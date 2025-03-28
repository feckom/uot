#!/usr/bin/env python
"""
Universal Offline Translator (UOT)
Author: Michal Fecko, 2025 (feckom@gmail.com)
https://github.com/feckom/uot.git
"""

import sys
import argparse
import argostranslate.package
import argostranslate.translate
import os
import time
import psutil
import requests
import json
from concurrent.futures import ThreadPoolExecutor
from textwrap import fill

# Constants
VERSION = "1.0"
AUTHOR = "Michal Fecko, 2025 (feckom@gmail.com), https://github.com/feckom/uot.git"
MODELS_DIR = os.getenv("UOT_MODELS_DIR", "models")
BASE_URL = "https://data.argosopentech.com/argospm/v1/"
INDEX_URL = "https://raw.githubusercontent.com/argosopentech/argospm-index/main/index.json"

# Global state
INSTALLED_LANGUAGES = None
VERBOSE = False

def print_help(available_languages):
    help_text = f"""
Universal Offline Translator (UOT)

Author:
  {AUTHOR}

Version:
  {VERSION}

Syntax:
  uot.py -il [input_language] -ol [output_language] text_to_translate [options]

Parameters:
  -il    input language (available: {format_languages(available_languages)})
  -ol    output language (available: {format_languages(available_languages)})

Optional:
  -i     interactive mode (show [INFO] logs)
  -v     show version info and exit
  -im    install models from Argos index

Examples:
  uot.py -il en -ol sk Hello world
  uot.py -il sk -ol en Ahoj svet

You can also use stdin:
  echo Hello world | uot.py -il en -ol sk -i
"""
    print(help_text)

def print_version():
    print(f"Universal Offline Translator (UOT)\nVersion: {VERSION}\nAuthor: {AUTHOR}")

def verbose_log(message):
    if VERBOSE:
        print(message, file=sys.stderr)

def format_languages(languages):
    if not languages:
        return "No languages available. Please install models."

    valid_languages = sorted(languages)
    if not valid_languages:
        return "No valid languages found in models."

    grouped = {}
    for lang in valid_languages:
        prefix = lang.split('-')[0] if '-' in lang else lang
        grouped.setdefault(prefix, []).append(lang)

    compact = []
    for prefix, codes in grouped.items():
        if len(codes) == 1:
            compact.append(codes[0])
        else:
            compact.append(f"{prefix}-*")

    return fill(", ".join(compact), width=80)

def load_installed_languages():
    global INSTALLED_LANGUAGES
    if INSTALLED_LANGUAGES is None:
        INSTALLED_LANGUAGES = argostranslate.translate.get_installed_languages()
    return INSTALLED_LANGUAGES

def detect_available_languages():
    if not os.path.exists(MODELS_DIR):
        print(f"[ERROR] Models directory '{MODELS_DIR}' not found.", file=sys.stderr)
        sys.exit(1)

    model_files = [f for f in os.listdir(MODELS_DIR) if f.endswith(".argosmodel")]
    if not model_files:
        print(f"[ERROR] No model files found in '{MODELS_DIR}'.", file=sys.stderr)
        sys.exit(1)

    available_languages = set()
    for model_file in model_files:
        name = os.path.splitext(model_file)[0]
        if name.startswith("translate-"):
            parts = name.split("_")
            if len(parts) >= 2:
                input_lang = parts[0].replace("translate-", "")
                output_lang = parts[1].split('-')[0]
                available_languages.add(input_lang)
                available_languages.add(output_lang)

    verbose_log(f"[DEBUG] Detected available languages: {available_languages}")
    return available_languages

def install_model(model_path, timeout=300):
    if not os.path.exists(model_path):
        verbose_log(f"[WARNING] Model file '{model_path}' not found. Skipping.")
        return False
    try:
        #with open(model_path, 'rb') as model_file:
        #    argostranslate.package.install_from_pipe(model_file, timeout=timeout)
        argostranslate.package.install_from_path(model_path)
        verbose_log(f"[INFO] Successfully installed model '{os.path.basename(model_path)}'")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to install model '{os.path.basename(model_path)}': {e}", file=sys.stderr)
        return False

def install_models_from_local_dir():
    model_files = [os.path.join(MODELS_DIR, f)
                   for f in os.listdir(MODELS_DIR)
                   if f.endswith(".argosmodel")]

    if not model_files:
        print(f"[ERROR] No models found in '{MODELS_DIR}' to install.", file=sys.stderr)
        sys.exit(1)

    verbose_log(f"[INFO] Installing {len(model_files)} model(s)...")

    with ThreadPoolExecutor() as executor:
        results = list(executor.map(install_model, model_files))

    if not any(results):
        print("[ERROR] Failed to install any models.", file=sys.stderr)
        sys.exit(1)

    global INSTALLED_LANGUAGES
    INSTALLED_LANGUAGES = None

def ensure_models_dir():
    if not os.path.exists(MODELS_DIR):
        os.makedirs(MODELS_DIR)
        verbose_log(f"[INFO] Created directory: {MODELS_DIR}")

def install_models_from_index():
    ensure_models_dir()

    print(f"Fetching model index from {INDEX_URL}...")

    try:
        response = requests.get(INDEX_URL, timeout=10)
        response.raise_for_status()
        index_data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to fetch index: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON in index: {e}", file=sys.stderr)
        sys.exit(1)

    verbose_log(f"[DEBUG] Loaded JSON index successfully.")
    verbose_log(f"[DEBUG] First 3 entries: {json.dumps(index_data[:3], indent=2)}")

    packages_found = 0
    packages_downloaded = 0
    skipped_entries = 0

    for idx, item in enumerate(index_data):
        if not item:
            verbose_log(f"[SKIP] Empty or invalid entry at index {idx}.")
            skipped_entries += 1
            continue

        if not all(k in item for k in ("code", "package_version")):
            verbose_log(f"[SKIP] Entry {idx} missing code or package_version.")
            skipped_entries += 1
            continue

        code = item["code"]
        package_version = item["package_version"]

        filename = generate_filename(code, package_version)
        file_url = f"{BASE_URL}{filename}"
        dest_path = os.path.join(MODELS_DIR, filename)

        verbose_log(f"[INFO] Processing {filename}")

        packages_found += 1

        if os.path.exists(dest_path):
            print(f"[SKIP] {filename} already exists.")
            continue

        if download_file(file_url, dest_path):
            packages_downloaded += 1

    print(f"\nFinished processing.\n")
    print(f"Total entries in index: {len(index_data)}")
    print(f"Packages found: {packages_found}")
    print(f"Packages downloaded: {packages_downloaded}")
    print(f"Skipped invalid entries: {skipped_entries}")
    print(f"Packages skipped (already exist): {packages_found - packages_downloaded}")

def generate_filename(code, package_version):
    return f"{code}-{normalize_version(package_version)}.argosmodel"

def normalize_version(version):
    return version.replace('.', '_')

def download_file(url, dest_path, retries=3):
    for attempt in range(retries):
        try:
            with requests.get(url, stream=True, timeout=10) as response:
                if response.status_code == 404:
                    print(f"[ERROR] File not found (404): {url}")
                    return False
                response.raise_for_status()

                total_size = int(response.headers.get('content-length', 0))
                block_size = 1024 * 1024
                downloaded_size = 0

                with open(dest_path, 'wb') as file:
                    for data in response.iter_content(block_size):
                        file.write(data)
                        downloaded_size += len(data)
                        if total_size:
                            done = int(50 * downloaded_size / total_size)
                            print(f"\rDownloading {os.path.basename(dest_path)} [{'#' * done}{'.' * (50 - done)}] {downloaded_size // (1024 * 1024)}MB/{total_size // (1024 * 1024)}MB", end='')

                print("\nDone.")
                return True
        except Exception as e:
            print(f"\n[ERROR] Attempt {attempt + 1} failed: {e}")
            if os.path.exists(dest_path):
                os.remove(dest_path)
            if attempt < retries - 1:
                time.sleep(2)
    return False

def measure_memory_usage_mb():
    process = psutil.Process(os.getpid())
    mem_bytes = process.memory_info().rss
    mem_mb = mem_bytes / (1024 * 1024)
    return round(mem_mb, 1)

def validate_language_code(code, available_languages):
    if code not in available_languages:
        print(f"[ERROR] Invalid language code: {code}. Available languages: {format_languages(available_languages)}", file=sys.stderr)
        sys.exit(1)

def main():
    global VERBOSE

    if len(sys.argv) == 1:
        available_languages = detect_available_languages()
        print_help(available_languages)
        sys.exit(0)

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-il', type=str, help="Input language code")
    parser.add_argument('-ol', type=str, help="Output language code")
    parser.add_argument('-i', action='store_true', help="Interactive mode (show [INFO] logs)")
    parser.add_argument('-v', action='store_true', help="Show version info and exit")
    parser.add_argument('-im', action='store_true', help="Install models from Argos OpenTech index")
    parser.add_argument('text', nargs=argparse.REMAINDER, help="Text to translate")

    try:
        args = parser.parse_args()
    except Exception as e:
        print(f"[ERROR] Argument parsing failed: {e}", file=sys.stderr)
        available_languages = detect_available_languages()
        print_help(available_languages)
        sys.exit(1)

    VERBOSE = args.i

    if args.v:
        print_version()
        sys.exit(0)

    if args.im:
        install_models_from_index()
        sys.exit(0)

    available_languages = detect_available_languages()

    if not args.il or not args.ol:
        print_help(available_languages)
        sys.exit(1)

    validate_language_code(args.il, available_languages)
    validate_language_code(args.ol, available_languages)

    if not args.text:
        verbose_log("[INFO] Waiting for input from stdin... (Ctrl+D to end)")
        args.text = [sys.stdin.read().strip()]
        if not args.text[0]:
            print("[ERROR] No input provided.", file=sys.stderr)
            print_help(available_languages)
            sys.exit(1)

    input_text = " ".join(args.text).strip()

    if not load_installed_languages():
        verbose_log("[INFO] No installed languages found. Installing local models...")
        install_models_from_local_dir()

    verbose_log(f"[INFO] Looking for translation path: {args.il} -> {args.ol}")
    translation = find_translation(args.il, args.ol)

    verbose_log(f"[INFO] Translating: '{input_text}'")

    start_time = time.perf_counter()

    try:
        output_text = translation.translate(input_text)
    except Exception as e:
        print(f"[ERROR] Translation failed: {e}", file=sys.stderr)
        sys.exit(1)

    elapsed_time = time.perf_counter() - start_time
    memory_usage_mb = measure_memory_usage_mb()

    print(output_text)
    verbose_log(f"[INFO] Translation took {elapsed_time:.2f} seconds, uses {memory_usage_mb} MB RAM")

def find_translation(from_code, to_code):
    installed_languages = load_installed_languages()

    from_lang = next((lang for lang in installed_languages if lang.code == from_code), None)
    to_lang = next((lang for lang in installed_languages if lang.code == to_code), None)

    if not from_lang or not to_lang:
        print(f"[ERROR] Language not found. Installed languages: {[lang.code for lang in installed_languages]}")
        sys.exit(1)

    translation = from_lang.get_translation(to_lang)
    if not translation:
        print(f"[ERROR] No translation path from '{from_code}' to '{to_code}'.")
        sys.exit(1)

    return translation

if __name__ == "__main__":
    main()

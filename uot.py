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
from concurrent.futures import ThreadPoolExecutor, as_completed
from textwrap import fill
from functools import lru_cache
from pathlib import Path
from typing import Set, List, Dict, Tuple, Optional, Any, Union

# Constants
VERSION = "1.16"
AUTHOR = "Michal Fecko, 2025 (feckom@gmail.com), https://github.com/uot.git"
MODELS_DIR = os.getenv("UOT_MODELS_DIR", "models")
BASE_URL = "https://data.argosopentech.com/argospm/v1/"
INDEX_URL = "https://raw.githubusercontent.com/argosopentech/argospm-index/main/index.json"
MAX_DOWNLOAD_THREADS = 3
DOWNLOAD_RETRY_DELAY = 2
DOWNLOAD_TIMEOUT = 20
MODEL_INSTALL_TIMEOUT = 300

# Global state
LANGUAGE_CACHE = {}  # Cache for language objects

class TranslatorError(Exception):
    """Custom exception for translator errors"""
    pass

def print_help(available_languages: Set[Tuple[str, str]]) -> None:
    """Print help text with available languages."""
    input_languages = {il for il, ol in available_languages}
    output_languages = {ol for il, ol in available_languages}

    il_str = format_languages(input_languages)
    ol_str = format_languages(output_languages)
    
    help_text = f"""
Universal Offline Translator (UOT)
Author:
  {AUTHOR}
Version:
  {VERSION}
Syntax:
  uot.py -il [input_language] -ol [output_language] text_to_translate [options]
Parameters:
  -il    input language (available: {il_str})
  -ol    output language (available: {ol_str})
Optional:
  -i     interactive mode (show info logs)
  -v     show version info and exit
  -im    install models from Argos index
  -c     clean model cache
  -l     list available languages and exit
  -p     show available pairs of languages and exit
Examples:
  uot.py -il en -ol sk Hello world
  uot.py -il sk -ol en Ahoj svet
You can also use stdin:
  echo Hello world | uot.py -il en -ol sk -i
"""
    print(help_text)

def print_version() -> None:
    """Print version information."""
    print(f"Universal Offline Translator (UOT)\nVersion: {VERSION}\nAuthor: {AUTHOR}")

def verbose_log(message: str, verbose: bool = False) -> None:
    """Log message if verbose mode is enabled."""
    if verbose:
        print(message, file=sys.stderr)

def format_languages(languages: Set[str]) -> str:
    """Format language list in a compact form."""
    if not languages:
        return "No languages available. Please install models."
    
    valid_languages = sorted(languages)
    if not valid_languages:
        return "No valid languages found in models."
        
    # Group languages by prefix
    grouped = {}
    for lang in valid_languages:
        prefix = lang.split('-')[0] if '-' in lang else lang
        grouped.setdefault(prefix, []).append(lang)
    
    # Create compact representation
    compact = []
    for prefix, codes in grouped.items():
        if len(codes) == 1:
            compact.append(codes[0])
        else:
            compact.append(f"{prefix}-*")
    
    return fill(", ".join(compact), width=80)

def format_language_pairs(language_pairs: Set[Tuple[str, str]]) -> str:
    """Format language pairs in a compact combination form."""
    if not language_pairs:
        return "No language pairs available. Please install models."

    # Group by input language
    grouped = {}
    for il, ol in language_pairs:
        grouped.setdefault(il, []).append(ol)

    compact = []
    for il, ols in grouped.items():
        ols_str = ", ".join(sorted(ols))  # Ensure output languages are sorted
        compact.append(f"{il}→({ols_str})")  # Combination notation

    return fill(", ".join(compact), width=80)

@lru_cache(maxsize=1)
def get_installed_languages():
    """Get installed languages with caching."""
    return argostranslate.translate.get_installed_languages()

def detect_available_languages() -> Set[Tuple[str, str]]:
    """Detect available languages from model files and only return compatible pairs."""
    models_dir = Path(MODELS_DIR)
    if not models_dir.exists():
        print(f"[ERROR] Models directory '{MODELS_DIR}' not found.", file=sys.stderr)
        sys.exit(1)
    
    model_files = list(models_dir.glob("*.argosmodel"))
    if not model_files:
        print(f"[ERROR] No model files found in '{MODELS_DIR}'.", file=sys.stderr)
        sys.exit(1)
    
    available_language_pairs: Set[Tuple[str, str]] = set()
    for model_file in model_files:
        name = model_file.stem
        if name.startswith("translate-"):
            parts = name.split("_")
            if len(parts) >= 2:
                try:
                    output_lang = parts[0].replace("translate-", "")
                    input_lang = parts[1].split('-')[0]
                    available_language_pairs.add((input_lang, output_lang))  # Store the pair
                except IndexError:
                    print(f"[WARNING] Could not parse language codes from model name: {name}", file=sys.stderr)

    return available_language_pairs

def install_model(model_path: str, verbose: bool = False, timeout: int = MODEL_INSTALL_TIMEOUT) -> bool:
    """Install a translation model."""
    if not os.path.exists(model_path):
        verbose_log(f"[WARNING] Model file '{model_path}' not found. Skipping.", verbose)
        return False
    
    try:
        argostranslate.package.install_from_path(model_path)
        verbose_log(f"[INFO] Successfully installed model '{os.path.basename(model_path)}'", verbose)
        # Reset the cache after installing new models
        get_installed_languages.cache_clear()
        return True
    except Exception as e:
        print(f"[ERROR] Failed to install model '{os.path.basename(model_path)}': {e}", file=sys.stderr)
        return False

def install_models_from_local_dir(verbose: bool = False) -> None:
    """Install all models from the local models directory."""
    models_dir = Path(MODELS_DIR)
    if not models_dir.exists():
        print(f"[ERROR] Models directory '{MODELS_DIR}' not found.", file=sys.stderr)
        sys.exit(1)
    
    model_files = list(models_dir.glob("*.argosmodel"))
    if not model_files:
        print(f"[ERROR] No models found in '{MODELS_DIR}' to install.", file=sys.stderr)
        sys.exit(1)
    
    verbose_log(f"[INFO] Installing {len(model_files)} model(s)...", verbose)
    
    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(install_model, str(model_path), verbose): model_path for model_path in model_files}
        
        installed = 0
        for future in as_completed(futures):
            model_path = futures[future]
            try:
                if future.result():
                    installed += 1
            except Exception as e:
                print(f"[ERROR] Failed to install '{model_path.name}': {e}", file=sys.stderr)
    
    if installed == 0:
        print("[ERROR] Failed to install any models.", file=sys.stderr)
        sys.exit(1)
    
    verbose_log(f"[INFO] Successfully installed {installed} of {len(model_files)} models.", verbose)

def ensure_models_dir() -> None:
    """Ensure models directory exists."""
    Path(MODELS_DIR).mkdir(exist_ok=True)

def clean_model_cache(verbose: bool = False) -> None:
    """Clean the model cache."""
    try:
        argostranslate.package.update_package_index()
        verbose_log("[INFO] Package index updated successfully.", verbose)
        
        cache_dir = argostranslate.package.get_package_data_dir()
        if os.path.exists(cache_dir):
            for file in os.listdir(cache_dir):
                file_path = os.path.join(cache_dir, file)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        import shutil
                        shutil.rmtree(file_path)
                except Exception as e:
                    print(f"[ERROR] Failed to remove {file_path}: {e}", file=sys.stderr)
        
        print(f"[INFO] Cache cleaned successfully.")
        # Reset the cache after cleaning
        get_installed_languages.cache_clear()
    except Exception as e:
        print(f"[ERROR] Failed to clean cache: {e}", file=sys.stderr)
        sys.exit(1)

def download_file(url: str, dest_path: str, verbose: bool = False, retries: int = 3) -> bool:
    """Download a file with progress tracking and retries."""
    for attempt in range(retries):
        try:
            with requests.get(url, stream=True, timeout=DOWNLOAD_TIMEOUT) as response:
                if response.status_code == 404:
                    print(f"[ERROR] File not found (404): {url}")
                    return False
                
                response.raise_for_status()
                total_size = int(response.headers.get('content-length', 0))
                block_size = 1024 * 1024  # 1MB
                downloaded_size = 0
                
                with open(dest_path, 'wb') as file:
                    for data in response.iter_content(block_size):
                        file.write(data)
                        downloaded_size += len(data)
                        
                        if total_size:
                            done = int(50 * downloaded_size / total_size)
                            progress = f"[{'#' * done}{'.' * (50 - done)}]"
                            mb_done = downloaded_size // (1024 * 1024)
                            mb_total = total_size // (1024 * 1024)
                            print(f"\rDownloading {os.path.basename(dest_path)} {progress} {mb_done}MB/{mb_total}MB", end='')
                
                print("\nDone.")
                return True
                
        except Exception as e:
            print(f"\n[ERROR] Attempt {attempt + 1} failed: {e}")
            if os.path.exists(dest_path):
                os.remove(dest_path)
            
            if attempt < retries - 1:
                time.sleep(DOWNLOAD_RETRY_DELAY)
    
    return False

def generate_filename(code: str, package_version: str) -> str:
    """Generate standard filename for a model package."""
    return f"{code}-{normalize_version(package_version)}.argosmodel"

def normalize_version(version: str) -> str:
    """Normalize version string for filenames."""
    return version.replace('.', '_')

def download_model(item: Dict[str, Any], verbose: bool = False) -> bool:
    """Download a single model from the index."""
    try:
        if not all(k in item for k in ("code", "package_version")):
            verbose_log(f"[SKIP] Entry missing required fields: {item}", verbose)
            return False
        
        code = item["code"]
        package_version = item["package_version"]
        filename = generate_filename(code, package_version)
        file_url = f"{BASE_URL}{filename}"
        dest_path = os.path.join(MODELS_DIR, filename)
        
        if os.path.exists(dest_path):
            print(f"[SKIP] {filename} already exists.")
            return False
        
        return download_file(file_url, dest_path, verbose)
    except Exception as e:
        print(f"[ERROR] Failed to download model: {e}", file=sys.stderr)
        return False

def install_models_from_index(verbose: bool = False) -> None:
    """Install models from the Argos OpenTech index."""
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
    
    verbose_log(f"[DEBUG] Loaded JSON index successfully.", verbose)
    
    valid_entries = [item for item in index_data if item and all(k in item for k in ("code", "package_version"))]
    packages_found = len(valid_entries)
    
    print(f"Found {packages_found} packages in index.")
    
    # Download and install packages using ThreadPoolExecutor
    packages_downloaded = 0
    
    with ThreadPoolExecutor(max_workers=MAX_DOWNLOAD_THREADS) as executor:
        futures = {executor.submit(download_model, item, verbose): item for item in valid_entries}
        
        for future in as_completed(futures):
            item = futures[future]
            try:
                if future.result():
                    packages_downloaded += 1
            except Exception as e:
                print(f"[ERROR] Download failed: {e}", file=sys.stderr)
    
    print(f"\nFinished processing.\n")
    print(f"Total entries in index: {len(index_data)}")
    print(f"Valid packages found: {packages_found}")
    print(f"Packages downloaded: {packages_downloaded}")
    print(f"Packages skipped (already exist): {packages_found - packages_downloaded}")
    
    if packages_downloaded > 0:
        print(f"\nInstalling downloaded models...")
        install_models_from_local_dir(verbose)

def measure_memory_usage_mb() -> float:
    """Measure current memory usage in MB."""
    process = psutil.Process(os.getpid())
    mem_bytes = process.memory_info().rss
    mem_mb = mem_bytes / (1024 * 1024)
    return round(mem_mb, 1)

def validate_language_code(input_lang: str, output_lang: str, available_languages: Set[Tuple[str, str]]) -> bool:
    """Validate that the language pair is available."""
    if (input_lang, output_lang) not in available_languages:
        print(f"[ERROR] Invalid language pair: {input_lang}-{output_lang}. ", file=sys.stderr, end="")
        print(f"Available pairs: {format_language_pairs(available_languages)}")
        return False
    return True

def find_translation(from_code: str, to_code: str) -> Any:
    """Find a translation path between two languages."""
    # Create a cache key for this language pair
    cache_key = f"{from_code}_{to_code}"
    
    # Check if we have this translation in cache
    if cache_key in LANGUAGE_CACHE:
        return LANGUAGE_CACHE[cache_key]
    
    installed_languages = get_installed_languages()
    
    from_lang = next((lang for lang in installed_languages if lang.code == from_code), None)
    to_lang = next((lang for lang in installed_languages if lang.code == to_code), None)
    
    if not from_lang:
        installed_codes = [lang.code for lang in installed_languages]
        raise TranslatorError(f"Input language '{from_code}' not installed. Installed languages: {', '.join(installed_codes)}")
    
    if not to_lang:
        installed_codes = [lang.code for lang in installed_languages]
        raise TranslatorError(f"Output language '{to_code}' not installed. Installed languages: {', '.join(installed_codes)}")
    
    translation = from_lang.get_translation(to_lang)
    if not translation:
        raise TranslatorError(f"No translation path from '{from_code}' to '{to_code}'.")
    
    # Cache this translation for future use
    LANGUAGE_CACHE[cache_key] = translation
    return translation

def list_languages(language_pairs: Set[Tuple[str, str]], verbose: bool = False) -> None:
    """List all available languages."""
    available_languages = detect_available_languages()
    
    print("Available languages:")
    for il, ol in sorted(available_languages):
        print(f"  {il} -> {ol}")
    
    if verbose:
        # Show additional information about installed languages
        installed = get_installed_languages()
        print("\nInstalled language models:")
        for lang in installed:
            translations = [t.to_lang.code for t in lang.translations]
            if translations:
                print(f"  {lang.code} → {', '.join(translations)}")
            else:
                print(f"  {lang.code} (no translations)")

def show_language_pairs(language_pairs: Set[Tuple[str, str]]) -> None:
    """Show available pairs of languages in compact combination form and exit."""
    print(format_language_pairs(language_pairs))

def main() -> None:
    """Main function."""
    if len(sys.argv) == 1:
        language_pairs = detect_available_languages()
        print_help(language_pairs)
        sys.exit(0)
    
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-il', type=str, help="Input language code")
    parser.add_argument('-ol', type=str, help="Output language code")
    parser.add_argument('-i', action='store_true', help="Interactive mode (show info logs)")
    parser.add_argument('-v', action='store_true', help="Show version info and exit")
    parser.add_argument('-im', action='store_true', help="Install models from Argos OpenTech index")
    parser.add_argument('-c', action='store_true', help="Clean model cache")
    parser.add_argument('-l', action='store_true', help="List available languages and exit")
    parser.add_argument('-p', action='store_true', help="Show available pairs of languages and exit")
    parser.add_argument('text', nargs=argparse.REMAINDER, help="Text to translate")
    
    try:
        args = parser.parse_args()
    except Exception as e:
        print(f"[ERROR] Argument parsing failed: {e}", file=sys.stderr)
        language_pairs = detect_available_languages()
        print_help(language_pairs)
        sys.exit(1)
    
    verbose = args.i
    
    if args.v:
        print_version()
        sys.exit(0)
    
    if args.c:
        clean_model_cache(verbose)
        sys.exit(0)
    
    if args.im:
        install_models_from_index(verbose)
        sys.exit(0)
    
    # Detect language pairs from model files
    language_pairs = detect_available_languages()
    
    if args.l:
        list_languages(language_pairs, verbose)
        sys.exit(0)

    if args.p:
        show_language_pairs(language_pairs)
        sys.exit(0)
    
    if not args.il or not args.ol:
        print_help(language_pairs)
        sys.exit(1)
    
    # First check if the specified language pair is valid
    available_languages = detect_available_languages()
    if not validate_language_code(args.il, args.ol, available_languages):
        # Suggest installing models if the language pair is invalid
        print(f"[TIP] You may need to run 'uot.py -im' to download and install language models.", file=sys.stderr)
        sys.exit(1)
    
    if not args.text:
        verbose_log("[INFO] Waiting for input from stdin... (Ctrl+D to end)", verbose)
        args.text = [sys.stdin.read().strip()]
        if not args.text[0]:
            print("[ERROR] No input provided.", file=sys.stderr)
            print_help(language_pairs)
            sys.exit(1)
    
    input_text = " ".join(args.text).strip()
    
    # Make sure we have models installed
    if not get_installed_languages():
        verbose_log("[INFO] No installed languages found. Installing local models...", verbose)
        install_models_from_local_dir(verbose)
    
    # Now check if the required languages are actually installed (not just available)
    installed_languages = get_installed_languages()
    installed_codes = [lang.code for lang in installed_languages]
    
    missing_languages = []
    if args.il not in installed_codes:
        missing_languages.append(args.il)
    if args.ol not in installed_codes:
        missing_languages.append(args.ol)

    try:
        verbose_log(f"[INFO] Looking for translation path: {args.il} → {args.ol}", verbose)
        translation = find_translation(args.il, args.ol)
        
        verbose_log(f"[INFO] Translating: '{input_text}'", verbose)
        start_time = time.perf_counter()
        
        output_text = translation.translate(input_text)
        
        elapsed_time = time.perf_counter() - start_time
        memory_usage_mb = measure_memory_usage_mb()
        
        print(output_text)
        verbose_log(f"[INFO] Translation took {elapsed_time:.2f} seconds, uses {memory_usage_mb} MB RAM", verbose)
        
    except TranslatorError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        # If we have both languages installed but no translation path, suggest downloading models
        available_languages = detect_available_languages()
        if (args.il, args.ol) in available_languages:
            print(f"[TIP] You may need to download a specific model for {args.il}-{args.ol} with 'uot.py -im'", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Translation failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

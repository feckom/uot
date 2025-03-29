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
VERSION = "1.17"
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

def print_help(available_language_pairs: Set[Tuple[str, str]]) -> None:
    """Print help text with available languages."""
    installed_languages = get_installed_languages()
    installed_codes = {lang.code for lang in installed_languages}

    # Filter to only show installed and available pairs
    valid_pairs = {(il, ol) for il, ol in available_language_pairs if il in installed_codes and ol in installed_codes}

    # Extract unique input and output languages from valid pairs
    input_languages = {il for il, ol in valid_pairs}
    output_languages = {ol for il, ol in valid_pairs}

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
  -il    input language (based on translation models in '{MODELS_DIR}': {il_str})
  -ol    output language (based on translation models in '{MODELS_DIR}': {ol_str})
Optional:
  -i     interactive mode (show info logs)
  -v     show version info and exit
  -im    install models from Argos index. Installs all available models.
  -c     clean model cache
  -l     list available languages and exit
  -p     show available pairs of languages and exit
Examples:
  uot.py -il en -ol sk Hello world
  uot.py -il sk -ol en Ahoj svet
You can also use stdin:
  echo Hello world | uot.py -il en -ol sk -i

Note:
  Only language pairs with available models are supported.
  Use -p to see available translation directions.
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
    """
    Detect available language pairs from model files in the models directory.
    Each model file has a name like "translate-en_sk-1_9.argosmodel".
    Returns a set of tuples (source_lang, target_lang).
    """
    models_dir = Path(MODELS_DIR)
    if not models_dir.exists():
        print(f"[ERROR] Models directory '{MODELS_DIR}' not found.", file=sys.stderr)
        sys.exit(1)

    model_files = list(models_dir.glob("translate-*.argosmodel"))
    if not model_files:
        print(f"[ERROR] No model files found in '{MODELS_DIR}'.", file=sys.stderr)
        return set()

    available_language_pairs: Set[Tuple[str, str]] = set()

    for model_file in model_files:
        name = model_file.stem  # e.g. translate-en_sk-1_9
        if name.startswith("translate-"):
            try:
                parts = name[len("translate-"):].split("-")
                # Join everything except the version back together (in case language codes have dashes)
                lang_part = "-".join(parts[:-1])
                source_target = lang_part.split("_")
                if len(source_target) == 2:
                    tgt, src = source_target #Fixed language detection
                    available_language_pairs.add((src, tgt)) #Fixed language detection
            except Exception as e:
                print(f"[WARNING] Could not parse language pair from '{name}': {e}", file=sys.stderr)

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
    """Clean the model cache by uninstalling all installed packages."""
    try:
        installed_packages = argostranslate.package.get_installed_packages()
        if not installed_packages:
            print("[INFO] No installed packages found.")
            return

        for package in installed_packages:
            argostranslate.package.uninstall(package)
            verbose_log(f"[INFO] Uninstalled: {package}", verbose)

        get_installed_languages.cache_clear()
        print("[INFO] All installed translation models have been uninstalled.")
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

if not get_installed_languages():
    verbose_log("[INFO] No installed languages found. Installing local models...", verbose=False) #Set default value False
    install_models_from_local_dir(verbose=False) #Set default value False


def validate_language_code(input_lang: str, output_lang: str, available_language_pairs: Set[Tuple[str, str]]) -> bool:
    """
    Validate that the language pair is available and installed.
    
    Args:
        input_lang: Source language code
        output_lang: Target language code
        available_language_pairs: Set of available language pairs
        
    Returns:
        bool: True if the language pair is valid, False otherwise
    """
    # Check if languages are installed
    installed_languages = get_installed_languages()
    installed_codes = {lang.code for lang in installed_languages}
    
    if input_lang not in installed_codes:
        print(f"[ERROR] Input language '{input_lang}' is not installed.", file=sys.stderr)
        return False
        
    if output_lang not in installed_codes:
        print(f"[ERROR] Output language '{output_lang}' is not installed.", file=sys.stderr)
        return False
    
    # Check if there's a direct translation path
    if (input_lang, output_lang) not in available_language_pairs:
        print(f"[ERROR] No translation path from '{input_lang}' to '{output_lang}'.", file=sys.stderr)
        print(f"[TIP] You may need to install a model for this language pair using 'uot.py -im'", file=sys.stderr)
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
        # Limit the number of displayed codes to avoid overly long error messages
        installed_codes = [lang.code for lang in installed_languages][:10]
        if len(installed_languages) > 10:
            installed_codes.append("...")
        raise TranslatorError(f"Input language '{from_code}' not installed. Some installed languages: {', '.join(installed_codes)}")
    
    if not to_lang:
        # Limit the number of displayed codes to avoid overly long error messages
        installed_codes = [lang.code for lang in installed_languages][:10]
        if len(installed_languages) > 10:
            installed_codes.append("...")
        raise TranslatorError(f"Output language '{to_code}' not installed. Some installed languages: {', '.join(installed_codes)}")
    
    translation = from_lang.get_translation(to_lang)
    if not translation:
        raise TranslatorError(f"No translation path from '{from_code}' to '{to_code}'.")
    
    # Cache this translation for future use
    LANGUAGE_CACHE[cache_key] = translation
    return translation

def list_languages(available_language_pairs: Set[Tuple[str, str]], verbose: bool = False) -> None:
    """
    List all available languages with their translation capabilities.
    
    Args:
        available_language_pairs: Set of available language pairs
        verbose: Whether to show detailed info
    """
    installed_languages = get_installed_languages()
    installed_codes = {lang.code for lang in installed_languages}
    
    # Group by source language for better readability
    source_to_targets = {}
    for source, target in available_language_pairs:
        if source in installed_codes and target in installed_codes:
            source_to_targets.setdefault(source, set()).add(target)
    
    if source_to_targets:
        print("Available language pairs (installed models):")
        for source in sorted(source_to_targets.keys()):
            targets = sorted(source_to_targets[source])
            print(f"  {source} → {', '.join(targets)}")
    else:
        print("No language pairs available with installed models.")
        print("[TIP] Run 'uot.py -im' to download and install language models.")
    
    if verbose:
        # Show additional information about language codes
        print("\nLanguage code reference:")
        # Map common language codes to full names
        lang_names = {
            'ar': 'Arabic', 'az': 'Azerbaijani', 'bg': 'Bulgarian', 'bn': 'Bengali', 
            'ca': 'Catalan', 'cs': 'Czech', 'da': 'Danish', 'de': 'German', 
            'el': 'Greek', 'en': 'English', 'eo': 'Esperanto', 'es': 'Spanish', 
            'et': 'Estonian', 'eu': 'Basque', 'fa': 'Persian', 'fi': 'Finnish', 
            'fr': 'French', 'ga': 'Irish', 'gl': 'Galician', 'he': 'Hebrew', 
            'hi': 'Hindi', 'hu': 'Hungarian', 'id': 'Indonesian', 'it': 'Italian', 
            'ja': 'Japanese', 'ko': 'Korean', 'lt': 'Lithuanian', 'lv': 'Latvian', 
            'ms': 'Malay', 'nb': 'Norwegian', 'nl': 'Dutch', 'pl': 'Polish', 
            'pt': 'Portuguese', 'ro': 'Romanian', 'ru': 'Russian', 'sk': 'Slovak', 
            'sl': 'Slovenian', 'sq': 'Albanian', 'sv': 'Swedish', 'th': 'Thai', 
            'tl': 'Tagalog', 'tr': 'Turkish', 'uk': 'Ukrainian', 'zh': 'Chinese (Simplified)', 
            'zt': 'Chinese (Traditional)'
        }
        for code in sorted(set(lang_code for pair in available_language_pairs for lang_code in pair)):
            if code in installed_codes:
                name = lang_names.get(code, f"Unknown ({code})")
                print(f"  {code}: {name}")

def show_language_pairs(available_language_pairs: Set[Tuple[str, str]]) -> None:
    """
    Show available language pairs in a user-friendly format.

    Args:
        available_language_pairs: Set of available language pairs
    """
    installed_languages = get_installed_languages()
    installed_codes = {lang.code for lang in installed_languages}

    # Filter pairs to only include installed languages
    valid_pairs = {(src, tgt) for src, tgt in available_language_pairs 
                   if src in installed_codes and tgt in installed_codes}

    if not valid_pairs:
        print("No language pairs available with installed models.")
        print("[TIP] Run 'uot.py -im' to download and install language models.")
        return

    # Group by source language
    source_to_targets = {}
    for source, target in valid_pairs:
        source_to_targets.setdefault(source, set()).add(target)

    print(f"Available translation pairs (based on .argosmodel files in '{MODELS_DIR}'):")
    for source in sorted(source_to_targets.keys()):
        targets = sorted(source_to_targets[source])
        targets_str = ', '.join(targets)
        print(f"  {source} → ({targets_str})")

def main() -> None:
    """Main function."""
    available_language_pairs = detect_available_languages()  # Get all available pairs
    
    # Show only installed languages pairs on main usage.
    installed_languages = get_installed_languages()
    installed_codes = {lang.code for lang in installed_languages}
    available_language_pairs = {(il, ol) for il, ol in available_language_pairs if il in installed_codes and ol in installed_codes}
    
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
        verbose = args.i
    except Exception as e:
        print(f"[ERROR] Argument parsing failed: {e}", file=sys.stderr)
        print_help(available_language_pairs)
        sys.exit(1)
    
    if len(sys.argv) == 1:
        print_help(available_language_pairs)
        sys.exit(0)

    if args.v:
        print_version()
        sys.exit(0)

    if args.c:
        clean_model_cache(verbose)
        sys.exit(0)

    if args.im:
        install_models_from_index(verbose)
        sys.exit(0)

    if args.l:
        list_languages(available_language_pairs, verbose)
        sys.exit(0)

    if args.p:
        # Ensure models are installed before showing pairs
        if not get_installed_languages():
            verbose_log("[INFO] No installed languages found. Installing local models...", verbose)
            install_models_from_local_dir(verbose)
        show_language_pairs(available_language_pairs)
        sys.exit(0)

    if not args.il or not args.ol:
        print_help(available_language_pairs)
        sys.exit(1)

    if not validate_language_code(args.il, args.ol, available_language_pairs):
        print(f"[TIP] You may need to run 'uot.py -im' to download and install language models.", file=sys.stderr)
        sys.exit(1)

    if not args.text:
        verbose_log("[INFO] Waiting for input from stdin... (Ctrl+D to end)", verbose)
        args.text = [sys.stdin.read().strip()]
        if not args.text[0]:
            print("[ERROR] No input provided.", file=sys.stderr)
            print_help(available_language_pairs)
            sys.exit(1)

    input_text = " ".join(args.text).strip()

    if not get_installed_languages():
        verbose_log("[INFO] No installed languages found. Installing local models...", verbose)
        install_models_from_local_dir(verbose)

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
        available_languages = detect_available_languages()
        installed_languages = get_installed_languages()
        installed_codes = [lang.code for lang in installed_languages]
        if (args.il in installed_codes) and (args.ol in installed_codes):
            print(f"[TIP] You may need to run 'uot.py -im' to download a specific model for {args.il}-{args.ol}.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Translation failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

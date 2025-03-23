
Universal Offline Translator
Version 1.0
Author: Michal Fecko, 2025 (feckom@gmail.com)

=======================================================================
📚 Table of Contents
=======================================================================

- English
  - Introduction
  - Features
  - Installation
  - Requirements
  - Usage
  - Environment Variables
  - Examples
  - License
- Čeština
  - Úvod
  - Vlastnosti
  - Instalace
  - Požadavky
  - Použití
  - Proměnné prostředí
  - Příklady
  - Licence
- Slovenčina
  - Úvod
  - Funkcie
  - Inštalácia
  - Požiadavky
  - Použitie
  - Premenné prostredia
  - Príklady
  - Licencia

=======================================================================
🇬🇧 ENGLISH
=======================================================================

INTRODUCTION
Universal Offline Translator (UOT) is a command-line tool for translating text between languages without an internet connection, powered by Argos Translate.
With OT, you can:
- Translate text instantly, fully offline.
- Download and manage translation models.
- Run it on Windows, Linux, and macOS.

FEATURES
- Fully offline translations (no internet after model installation)
- Download translation models directly from Argos OpenTech index (-im)
- Easy-to-use command-line interface
- Supports text input from arguments or stdin
- Performance and memory usage info with -i flag
- Custom models directory with UOT_MODELS_DIR env variable

INSTALLATION

Windows
-----------------------------------
git clone https://github.com/yourusername/uuot.git
cd uot
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt

Linux / macOS
-----------------------------------
git clone https://github.com/yourusername/uuot.git
cd uot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

REQUIREMENTS
- Python 3.8+
- Dependencies:
  - argostranslate
  - requests
  - psutil

USAGE
python uot.py [options] [text]

OPTIONS
- -il    Input language code (e.g., en, sk)
- -ol    Output language code (e.g., sk, en)
- -i     Interactive mode (show [INFO] debug messages)
- -v     Show version and author information
- -im    Install models from the Argos OpenTech index

ENVIRONMENT VARIABLES
- UOT_MODELS_DIR    Custom path to store downloaded model files

EXAMPLES
Basic translation:
  python uot.py -il en -ol sk Hello world

Verbose translation with info logs:
  python uot.py -il en -ol sk Hello world -i

Translate from stdin:
  echo "Hello world" | python uot.py -il en -ol sk

Install models from Argos OpenTech index:
  python uot.py -im -i

Show version info:
  python uot.py -v

LICENSE
MIT License

=======================================================================
🇨🇿 ČEŠTINA
=======================================================================

ÚVOD
Universal Offline Translator (UOT) je nástroj příkazového řádku pro překlad textů mezi jazyky bez připojení k internetu, využívající Argos Translate.

VLASTNOSTI
- Offline překlady (internet pouze pro stažení modelů)
- Stažení a instalace modelů přímo z Argos OpenTech indexu (-im)
- Jednoduché CLI rozhraní
- Podpora vstupu z argumentů i stdin
- Výpis výkonu a paměťového využití s parametrem -i
- Možnost nastavit vlastní adresář pro modely pomocí UOT_MODELS_DIR

INSTALACE

Windows
-----------------------------------
git clone https://github.com/yourusername/uuot.git
cd uot
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt

Linux / macOS
-----------------------------------
git clone https://github.com/yourusername/uuot.git
cd uot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

POŽADAVKY
- Python 3.8+
- Závislosti:
  - argostranslate
  - requests
  - psutil

POUŽITÍ
python uot.py [parametry] [text]

PARAMETRY
- -il    Vstupní jazyk (např. en, sk)
- -ol    Výstupní jazyk (např. sk, en)
- -i     Interaktivní režim (zobrazuje [INFO] logy)
- -v     Zobrazí verzi a informace o autorovi
- -im    Instalace modelů z Argos OpenTech indexu

PROMĚNNÉ PROSTŘEDÍ
- UOT_MODELS_DIR    Vlastní cesta pro ukládání modelových souborů

PŘÍKLADY
Základní překlad:
  python uot.py -il en -ol sk Hello world

Překlad s výpisem informací:
  python uot.py -il en -ol sk Hello world -i

Překlad ze stdin:
  echo "Hello world" | python uot.py -il en -ol sk

Instalace modelů z Argos indexu:
  python uot.py -im -i

Zobrazení verze:
  python uot.py -v

LICENCE
MIT Licence

=======================================================================
🇸🇰 SLOVENČINA
=======================================================================

ÚVOD
Universal Offline Translator (UOT) je nástroj príkazového riadku na preklad textov medzi jazykmi bez pripojenia na internet, založený na Argos Translate.

FUNKCIE
- Offline preklad (internet len na stiahnutie modelov)
- Sťahovanie modelov priamo z Argos OpenTech indexu (-im)
- Prehľadné CLI rozhranie
- Podpora vstupu cez argumenty aj stdin
- Zobrazenie výkonu a využitia pamäte pomocou -i
- Vlastný adresár pre modely cez UOT_MODELS_DIR

INŠTALÁCIA

Windows
-----------------------------------
git clone https://github.com/yourusername/uuot.git
cd uot
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt

Linux / macOS
-----------------------------------
git clone https://github.com/yourusername/uuot.git
cd uot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

POŽIADAVKY
- Python 3.8+
- Závislosti:
  - argostranslate
  - requests
  - psutil

POUŽITIE
python uot.py [parametre] [text]

PARAMETRE
- -il    Vstupný jazyk (napr. en, sk)
- -ol    Výstupný jazyk (napr. sk, en)
- -i     Interaktívny režim (zobrazuje [INFO] logy)
- -v     Zobrazí verziu a informácie o autorovi
- -im    Inštalácia modelov z Argos OpenTech indexu

PREMENNÉ PROSTREDIA
- UOT_MODELS_DIR    Vlastný adresár pre modely

PRÍKLADY
Základný preklad:
  python uot.py -il en -ol sk Hello world

Preklad s výpisom informácií:
  python uot.py -il en -ol sk Hello world -i

Preklad zo stdin:
  echo "Hello world" | python uot.py -il en -ol sk

Inštalácia modelov z Argos indexu:
  python uot.py -im -i

Zobrazenie verzie:
  python uot.py -v


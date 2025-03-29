
# Universal Offline Translator (UOT)

**Version**: 1.17
**Author**: Michal Fecko, 2025 (feckom@gmail.com)

---

## 📚 Table of Contents

- [🇬🇧 English](#english)
  - [Introduction](#introduction)
  - [Features](#features)
  - [Installation](#installation)
  - [Requirements](#requirements)
  - [Usage](#usage)
  - [Environment Variables](#environment-variables)
  - [Examples](#examples)
  - [License](#license)
- [🇨🇿 Čeština](#čeština)
  - [Úvod](#úvod)
  - [Vlastnosti](#vlastnosti)
  - [Instalace](#instalace)
  - [Požadavky](#požadavky)
  - [Použití](#použití)
  - [Proměnné prostředí](#proměnné-prostředí)
  - [Příklady](#příklady)
  - [Licence](#licence)
- [🇸🇰 Slovenčina](#slovenčina)
  - [Úvod](#úvod-1)
  - [Funkcie](#funkcie)
  - [Inštalácia](#inštalácia)
  - [Požiadavky](#požiadavky)
  - [Použitie](#použitie)
  - [Premenné prostredia](#premenné-prostredia)
  - [Príklady](#príklady-1)
  - [Licencia](#licencia)

---

# 🇬🇧 English

## Introduction

**Universal Offline Translator (UOT)** is a command-line tool for translating text between languages **without an internet connection**, powered by **Argos Translate**.

### With UOT, you can:
- Translate text instantly, fully offline.
- Download and manage translation models.
- Run it on Windows, Linux, and macOS.

## Features

- Fully offline translations (no internet after model installation).
- Download translation models directly from Argos OpenTech index (`-im`).
- Easy-to-use command-line interface.
- Supports text input from arguments or stdin.
- Performance and memory usage info with `-i` flag.
- Custom models directory via `UOT_MODELS_DIR` environment variable.

## Installation

### Windows

```bash
git clone https://github.com/feckom/uot.git
cd uot
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
```

### Linux / macOS

```bash
git clone https://github.com/feckom/uot.git
cd uot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Requirements

- Python 3.8+
- Dependencies:
  - `argostranslate`
  - `requests`
  - `psutil`

## Usage

```bash
python uot.py [options] [text]
```

### Options

| Option | Description                                                  |
|--------|--------------------------------------------------------------|
| `-il`  | Input language code (e.g., `en`, `sk`)                      |
| `-ol`  | Output language code (e.g., `sk`, `en`)                     |
| `-i`   | Interactive mode (show `[INFO]` debug messages)             |
| `-v`   | Show version and author information                         |
| `-im`  | Install models from the Argos OpenTech index                |
| '-p'   | Showing available language pairs                            |

## Environment Variables

| Variable         | Description                                         |
|------------------|-----------------------------------------------------|
| `UOT_MODELS_DIR` | Custom path to store downloaded model files         |

## Examples

### Basic translation
```bash
python uot.py -il en -ol sk Hello world
```

### Verbose translation with info logs
```bash
python uot.py -il en -ol sk Hello world -i
```

### Translate from stdin
```bash
echo "Hello world" | python uot.py -il en -ol sk
```

### Install models from Argos OpenTech index
```bash
python uot.py -im -i
```

### Show version info
```bash
python uot.py -v
```

## License

MIT License

---

# 🇨🇿 Čeština

## Úvod

**Universal Offline Translator (UOT)** je nástroj příkazového řádku pro překlad textů mezi jazyky **bez připojení k internetu**, využívající **Argos Translate**.

## Vlastnosti

- Offline překlady (internet pouze pro stažení modelů).
- Stažení a instalace modelů přímo z Argos OpenTech indexu (`-im`).
- Jednoduché CLI rozhraní.
- Podpora vstupu z argumentů i stdin.
- Výpis výkonu a paměťového využití s parametrem `-i`.
- Možnost nastavit vlastní adresář pro modely pomocí `UOT_MODELS_DIR`.

## Instalace

### Windows

```bash
git clone https://github.com/feckom/uot.git
cd uot
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
```

### Linux / macOS

```bash
git clone https://github.com/feckom/uot.git
cd uot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Požadavky

- Python 3.8+
- Závislosti:
  - `argostranslate`
  - `requests`
  - `psutil`

## Použití

```bash
python uot.py [parametry] [text]
```

### Parametry

| Parametr | Popis                                           |
|----------|-------------------------------------------------|
| `-il`    | Vstupní jazyk (např. `en`, `sk`)               |
| `-ol`    | Výstupní jazyk (např. `sk`, `en`)              |
| `-i`     | Interaktivní režim (zobrazení `[INFO]` logů)   |
| `-v`     | Zobrazení verze a informací o autorovi         |
| `-im`    | Instalace modelů z Argos OpenTech indexu       |
| '-p'     | Ukazuje dostupné páry jazykú                   |

## Proměnné prostředí

| Proměnná         | Popis                                        |
|------------------|----------------------------------------------|
| `UOT_MODELS_DIR` | Vlastní cesta pro ukládání modelových souborů |

## Příklady

### Základní překlad
```bash
python uot.py -il en -ol sk Hello world
```

### Překlad s výpisem informací
```bash
python uot.py -il en -ol sk Hello world -i
```

### Překlad ze stdin
```bash
echo "Hello world" | python uot.py -il en -ol sk
```

### Instalace modelů z Argos indexu
```bash
python uot.py -im -i
```

### Zobrazení verze
```bash
python uot.py -v
```

## Licence

MIT Licence

---

# 🇸🇰 Slovenčina

## Úvod

**Universal Offline Translator (UOT)** je nástroj príkazového riadku na preklad textov medzi jazykmi **bez pripojenia na internet**, založený na **Argos Translate**.

## Funkcie

- Offline preklad (internet len na stiahnutie modelov).
- Sťahovanie modelov priamo z Argos OpenTech indexu (`-im`).
- Prehľadné CLI rozhranie.
- Podpora vstupu cez argumenty aj stdin.
- Zobrazenie výkonu a využitia pamäte pomocou `-i`.
- Vlastný adresár pre modely cez `UOT_MODELS_DIR`.

## Inštalácia

### Windows

```bash
git clone https://github.com/feckom/uot.git
cd uot
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
```

### Linux / macOS

```bash
git clone https://github.com/feckom/uot.git
cd uot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Požiadavky

- Python 3.8+
- Závislosti:
  - `argostranslate`
  - `requests`
  - `psutil`

## Použitie

```bash
python uot.py [parametre] [text]
```

### Parametre

| Parameter | Popis                                               |
|-----------|-----------------------------------------------------|
| `-il`     | Vstupný jazyk (napr. `en`, `sk`)                   |
| `-ol`     | Výstupný jazyk (napr. `sk`, `en`)                  |
| `-i`      | Interaktívny režim (zobrazuje `[INFO]` logy)       |
| `-v`      | Zobrazí verziu a informácie o autorovi             |
| `-im`     | Inštaluje modely z Argos OpenTech indexu           |
| '-p'      | Ukazuje dostupné páry jazykov                      |

## Premenné prostredia

| Premenná         | Popis                                    |
|------------------|------------------------------------------|
| `UOT_MODELS_DIR` | Vlastný adresár pre modely               |

## Príklady

### Základný preklad
```bash
python uot.py -il en -ol sk Hello world
```

### Preklad s výpisom informácií
```bash
python uot.py -il en -ol sk Hello world -i
```

### Preklad zo stdin
```bash
echo "Hello world" | python uot.py -il en -ol sk
```

### Inštalácia modelov z Argos indexu
```bash
python uot.py -im -i
```

### Zobrazenie verzie
```bash
python uot.py -v
```

## Licencia

MIT Licencia

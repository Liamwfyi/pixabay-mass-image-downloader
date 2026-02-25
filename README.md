# Pixabay Mass Image Downloader

Minimal Python CLI to download the first _N_ images from a Pixabay search query.

## Why `pip install -r requirements.txt` can fail

On newer Linux distributions, Python may be marked as an **externally managed environment** (PEP 668). In that case, installing packages globally with `pip` is blocked.

Use a virtual environment instead.

## Setup (recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Run

```bash
python pixabay_mass_downloader.py
```

Prompts:
1. Save location (press Enter to default to Desktop)
2. New folder name
3. Search query
4. Number of images (1-100)

The script then downloads the first matching images into your selected folder.

## VS Code quick start

1. Open this folder in VS Code.
2. Open Terminal in VS Code.
3. Run setup commands above.
4. Select `.venv` as interpreter (`Python: Select Interpreter`).
5. Run:

```bash
python pixabay_mass_downloader.py
```

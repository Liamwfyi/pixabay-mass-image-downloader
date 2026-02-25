# Pixabay Mass Image Downloader

Minimal Python CLI to download the first _N_ images from a Pixabay search query using the official Pixabay API.

## Prerequisite: Pixabay API key

1. Create/get your key from: https://pixabay.com/api/docs/
2. Use either:
   - environment variable: `PIXABAY_API_KEY`
   - or enter the key when prompted by the script

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

## Prompt flow

Basic prompts:
1. Save location (press Enter to default to Desktop)
2. New folder name
3. Search query
4. Number of images (1-100)
5. Pixabay API key (only if `PIXABAY_API_KEY` is not already set)

Advanced API prompts (matching Pixabay API options for image search):
- `lang`
- `image_type`
- `orientation`
- `category`
- `min_width`
- `min_height`
- `colors`
- `editors_choice`
- `safesearch`
- `order`
- `page`
- `per_page` (set automatically from your image count)
- `id` (comma-separated image IDs)

## Output files

The script saves:
- downloaded images (`image_001.jpg`, etc.)
- `image_details.html` (readable details page)
- `image_details.json` (raw details data)

The details files include fields like image ID, size, tags, downloads, likes, comments, views, favorites, user, and Pixabay page URL.

## Example with environment variable

```bash
export PIXABAY_API_KEY="your_key_here"
python pixabay_mass_downloader.py
```

## VS Code quick start

1. Open this folder in VS Code.
2. Open Terminal in VS Code.
3. Run setup commands above.
4. Select `.venv` as interpreter (`Python: Select Interpreter`).
5. Optionally set `PIXABAY_API_KEY` in terminal, then run:

```bash
python pixabay_mass_downloader.py
```

# Pixabay Mass Image Downloader

Python-based mass downloader for Pixabay images using the official API.

This project now supports both:
- **CLI mode** (interactive terminal)
- **GUI mode** built with **Tkinter** (Python standard library)

## How to run the script

1. Create and activate a virtual environment (recommended):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

2. (Optional) set API key in environment:

```bash
export PIXABAY_API_KEY="your_key_here"
```

3. Run in CLI mode:

```bash
python pixabay_mass_downloader.py
```

4. Run in GUI mode:

```bash
python pixabay_mass_downloader.py --gui
```

## GUI (Issue #7)

The GUI is implemented in **Tkinter** so the stack stays fully Python and easy to maintain.

GUI features:
- Save location picker
- Folder name, search query, image count, API key fields
- Debug mode toggle
- Advanced API filter fields (language, image type, orientation, order, safe search, editor's choice, page, category, color)
- Start button + status panel
- Reuses the same download/retry/export logic as CLI mode

## API explanations

Uses Pixabay Image API docs: https://pixabay.com/api/docs/

Available filter options:
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
- `per_page` (auto-set from image count)
- `id`

## Troubleshooting

- **`externally-managed-environment` during pip install**
  - Use a virtual environment as shown above.

- **`400` / `403` API request failed**
  - Verify your API key is valid and active.
  - Check filters are valid for Pixabay API.

- **Rate limit (`429`)**
  - The script automatically retries with backoff + jitter.
  - Individual images that keep failing are skipped so the batch can continue.

## How it works

1. Collect input (CLI prompts or GUI fields).
2. Build Pixabay API request params.
3. Query `https://pixabay.com/api/`.
4. Download images with retry/backoff handling.
5. Save metadata output files:
   - `image_details.json`
   - `image_details.html`

## Version history

```bash
git log --oneline
```

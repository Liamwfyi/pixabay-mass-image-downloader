# Pixabay Mass Image Downloader

Minimal Python CLI to download the first _N_ images from a Pixabay search query using the official Pixabay API.

## How to run the script

1. (Recommended) create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

2. Set your API key (optional if you prefer entering it interactively):

```bash
export PIXABAY_API_KEY="your_key_here"
```

3. Run:

```bash
python pixabay_mass_downloader.py
```

At startup, the script now asks whether you want **debug mode**.
- `y` = verbose logs for each major step and sanitized API responses.
- `n` (or Enter) = normal output.

## API explanations

The script uses Pixabay Image API docs: https://pixabay.com/api/docs/

Basic prompts:
1. Save location (defaults to Desktop)
2. Output folder name
3. Search query
4. Number of images (1-100)
5. API key (if `PIXABAY_API_KEY` is not set)

Advanced API options available in the CLI:
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
- `id` (comma-separated image IDs)

Debug mode behavior:
- Prints current actions (request params, status codes, file writes, skips).
- Prints sanitized API response payloads.
- Redacts URL fields in debug output so image links are not printed.
- If rate limit (`429`) is hit, automatically retries with backoff + jitter and shows wait messaging.

## Troubleshooting

- **`externally-managed-environment` during pip install**
  - Use a virtual environment as shown above.

- **`400` / `403` API request failed**
  - Verify your API key is valid and active.
  - Check filters are valid for Pixabay API.

- **Rate limit reached (`429`)**
  - Wait and retry (script prints suggested wait time).
  - Reduce request frequency and image count per run.

- **No images downloaded**
  - Try broader search keywords.
  - Remove restrictive filters (category/color/min size/id).

## How it works

1. Collects user inputs (and debug mode preference).
2. Builds Pixabay API request parameters.
3. Calls `https://pixabay.com/api/`.
4. Downloads matching images into your target folder with a small cooldown between files.
5. Retries API/image requests when `429` is returned (uses `Retry-After` when available, otherwise exponential backoff + jitter).
6. Saves metadata files:
   - `image_details.json`
   - `image_details.html`

The details files include fields like image ID, tags, dimensions, downloads, likes, comments, views, favorites, user info, and page URL.

## Version history

See Git history for changes:
- `git log --oneline`

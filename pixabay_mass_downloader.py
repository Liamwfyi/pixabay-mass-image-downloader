#!/usr/bin/env python3
"""Minimal Pixabay image mass downloader (API-based)."""

from __future__ import annotations

import html
import json
import os
import random
import time
from pathlib import Path
from typing import Any, Dict, List

import requests

MAX_IMAGES = 100
API_URL = "https://pixabay.com/api/"
DOWNLOAD_COOLDOWN_SECONDS = 0.35
MAX_RETRIES = 5
BACKOFF_BASE_SECONDS = 1.5
VALID_IMAGE_TYPES = ("all", "photo", "illustration", "vector")
VALID_ORIENTATIONS = ("all", "horizontal", "vertical")
VALID_ORDERS = ("popular", "latest")
VALID_BOOL = ("true", "false")
VALID_CATEGORIES = (
    "backgrounds",
    "fashion",
    "nature",
    "science",
    "education",
    "feelings",
    "health",
    "people",
    "religion",
    "places",
    "animals",
    "industry",
    "computer",
    "food",
    "sports",
    "transportation",
    "travel",
    "buildings",
    "business",
    "music",
)
VALID_COLORS = (
    "grayscale",
    "transparent",
    "red",
    "orange",
    "yellow",
    "green",
    "turquoise",
    "blue",
    "lilac",
    "pink",
    "white",
    "gray",
    "black",
    "brown",
)


def prompt_debug_mode() -> bool:
    while True:
        raw = input("Enable debug mode? [y/N]: ").strip().lower()
        if raw in ("", "n", "no"):
            return False
        if raw in ("y", "yes"):
            return True
        print("Please enter y or n.")


def debug_log(enabled: bool, message: str) -> None:
    if enabled:
        print(f"[DEBUG] {message}")


def sanitize_debug_data(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: Dict[str, Any] = {}
        for key, item in value.items():
            if "url" in key.lower():
                sanitized[key] = "<redacted>"
            else:
                sanitized[key] = sanitize_debug_data(item)
        return sanitized
    if isinstance(value, list):
        return [sanitize_debug_data(item) for item in value]
    return value


def prompt_parent_directory() -> Path:
    default_dir = Path.home() / "Desktop"
    raw = input(f"Save location (press Enter for {default_dir}): ").strip()
    return Path(raw).expanduser() if raw else default_dir


def prompt_folder_name() -> str:
    while True:
        name = input("What should the new folder be called? ").strip()
        if name:
            return name
        print("Folder name cannot be empty.")


def prompt_search_query() -> str:
    while True:
        query = input("Search query: ").strip()
        if query:
            return query
        print("Search query cannot be empty.")


def prompt_image_count() -> int:
    while True:
        raw = input(f"How many images would you like (1-{MAX_IMAGES})? ").strip()
        try:
            count = int(raw)
        except ValueError:
            print("Please enter a number.")
            continue

        if 1 <= count <= MAX_IMAGES:
            return count
        print(f"Please enter a value between 1 and {MAX_IMAGES}.")


def prompt_api_key() -> str:
    env_key = os.getenv("PIXABAY_API_KEY", "").strip()
    if env_key:
        return env_key

    while True:
        key = input("Pixabay API key (or set PIXABAY_API_KEY): ").strip()
        if key:
            return key
        print("API key cannot be empty.")


def prompt_choice(prompt_text: str, valid: tuple[str, ...], default: str) -> str:
    options = "/".join(valid)
    while True:
        raw = input(f"{prompt_text} [{options}] (default: {default}): ").strip().lower()
        if not raw:
            return default
        if raw in valid:
            return raw
        print(f"Please choose one of: {', '.join(valid)}")


def prompt_non_negative_int(prompt_text: str, default: int) -> int:
    while True:
        raw = input(f"{prompt_text} (default: {default}): ").strip()
        if not raw:
            return default
        try:
            value = int(raw)
        except ValueError:
            print("Please enter a whole number.")
            continue
        if value >= 0:
            return value
        print("Please enter a value greater than or equal to 0.")


def prompt_positive_int(prompt_text: str, default: int) -> int:
    while True:
        raw = input(f"{prompt_text} (default: {default}): ").strip()
        if not raw:
            return default
        try:
            value = int(raw)
        except ValueError:
            print("Please enter a whole number.")
            continue
        if value > 0:
            return value
        print("Please enter a value greater than 0.")


def prompt_optional_choice(prompt_text: str, valid: tuple[str, ...]) -> str:
    options = "/".join(valid)
    while True:
        raw = input(f"{prompt_text} [{options}] (press Enter to skip): ").strip().lower()
        if not raw:
            return ""
        if raw in valid:
            return raw
        print(f"Please choose one of: {', '.join(valid)}")


def prompt_advanced_options(requested_count: int) -> Dict[str, str]:
    print("\nOptional Pixabay API filters (press Enter to keep defaults):")
    options: Dict[str, str] = {
        "lang": input("Language code (default: en): ").strip() or "en",
        "image_type": prompt_choice("Image type", VALID_IMAGE_TYPES, "photo"),
        "orientation": prompt_choice("Orientation", VALID_ORIENTATIONS, "all"),
        "order": prompt_choice("Order", VALID_ORDERS, "popular"),
        "safesearch": prompt_choice("Safe search", VALID_BOOL, "true"),
        "editors_choice": prompt_choice("Editor's choice only", VALID_BOOL, "false"),
        "page": str(prompt_positive_int("Results page", 1)),
        "per_page": str(requested_count),
    }

    category = prompt_optional_choice("Category", VALID_CATEGORIES)
    color = prompt_optional_choice("Color filter", VALID_COLORS)
    min_width = prompt_non_negative_int("Minimum width in px", 0)
    min_height = prompt_non_negative_int("Minimum height in px", 0)
    image_ids = input("Specific image IDs (comma-separated, optional): ").strip()

    if category:
        options["category"] = category
    if color:
        options["colors"] = color
    if min_width:
        options["min_width"] = str(min_width)
    if min_height:
        options["min_height"] = str(min_height)
    if image_ids:
        cleaned = ",".join(part.strip() for part in image_ids.split(",") if part.strip())
        if cleaned:
            options["id"] = cleaned

    return options


def request_with_retry(
    method: str,
    url: str,
    *,
    debug: bool,
    request_label: str,
    redact_url_in_logs: bool,
    **kwargs: Any,
) -> requests.Response:
    for attempt in range(1, MAX_RETRIES + 1):
        debug_url = "<redacted>" if redact_url_in_logs else url
        debug_log(debug, f"{request_label}: attempt {attempt}/{MAX_RETRIES} -> {method.upper()} {debug_url}")

        response = requests.request(method, url, **kwargs)
        debug_log(debug, f"{request_label}: status {response.status_code}")

        if response.status_code != 429:
            return response

        retry_after_raw = response.headers.get("Retry-After", "")
        try:
            retry_after_seconds = max(1.0, float(retry_after_raw)) if retry_after_raw else 0.0
        except ValueError:
            retry_after_seconds = 0.0

        exponential_backoff = BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
        jitter = random.uniform(0.1, 0.6)
        sleep_for = retry_after_seconds or (exponential_backoff + jitter)

        print(
            f"{request_label}: Pixabay rate limit reached (429). "
            f"Waiting {sleep_for:.1f}s before retry {attempt}/{MAX_RETRIES}."
        )
        debug_log(debug, f"{request_label}: rate limit headers {dict(response.headers)}")

        if attempt >= MAX_RETRIES:
            return response

        time.sleep(sleep_for)

    raise RuntimeError("Unreachable retry loop state")


def fetch_hits(api_key: str, query: str, options: Dict[str, str], debug: bool) -> List[Dict[str, Any]]:
    params = {"key": api_key, "q": query, **options}
    debug_log(debug, f"Calling Pixabay API with params: {json.dumps(sanitize_debug_data(params), indent=2)}")

    response = request_with_retry(
        "get",
        API_URL,
        debug=debug,
        request_label="Pixabay API search",
        redact_url_in_logs=False,
        params=params,
        timeout=30,
    )
    response.raise_for_status()

    payload = response.json()
    sanitized_payload = sanitize_debug_data(payload)
    debug_log(debug, f"Pixabay API response body (sanitized): {json.dumps(sanitized_payload, indent=2)}")

    hits = payload.get("hits", [])
    if not isinstance(hits, list):
        return []
    filtered_hits = [hit for hit in hits if isinstance(hit, dict)]
    debug_log(debug, f"Valid hit count: {len(filtered_hits)}")
    return filtered_hits


def download_images(hits: List[Dict[str, Any]], destination: Path, debug: bool) -> List[Dict[str, Any]]:
    details: List[Dict[str, Any]] = []

    for idx, hit in enumerate(hits, start=1):
        url = hit.get("largeImageURL") or hit.get("webformatURL")
        if not isinstance(url, str) or not url:
            debug_log(debug, f"Skipping hit {idx}: no usable image URL.")
            continue

        debug_log(debug, f"Downloading image {idx}/{len(hits)}")
        response = request_with_retry(
            "get",
            url,
            debug=debug,
            request_label=f"Image download {idx}/{len(hits)}",
            redact_url_in_logs=True,
            timeout=60,
            stream=True,
        )
        response.raise_for_status()

        ext = Path(url.split("?")[0]).suffix or ".jpg"
        filename = destination / f"image_{idx:03d}{ext.lower()}"

        with filename.open("wb") as out_file:
            for chunk in response.iter_content(chunk_size=1024 * 64):
                if chunk:
                    out_file.write(chunk)

        record = {
            "file_name": filename.name,
            "id": hit.get("id"),
            "page_url": hit.get("pageURL", ""),
            "type": hit.get("type", ""),
            "tags": hit.get("tags", ""),
            "width": hit.get("imageWidth"),
            "height": hit.get("imageHeight"),
            "downloads": hit.get("downloads"),
            "likes": hit.get("likes"),
            "comments": hit.get("comments"),
            "views": hit.get("views"),
            "favorites": hit.get("favorites"),
            "user": hit.get("user", ""),
            "user_id": hit.get("user_id"),
            "download_url": url,
        }
        details.append(record)
        print(f"Downloaded {idx}/{len(hits)}: {filename.name}")
        time.sleep(DOWNLOAD_COOLDOWN_SECONDS + random.uniform(0.05, 0.25))

    return details


def save_details_files(details: List[Dict[str, Any]], destination: Path, debug: bool) -> None:
    json_path = destination / "image_details.json"
    json_path.write_text(json.dumps(details, indent=2), encoding="utf-8")
    debug_log(debug, f"Wrote metadata JSON: {json_path}")

    rows = []
    for item in details:
        page_url = html.escape(str(item.get("page_url", "")))
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('file_name', '')))}</td>"
            f"<td>{html.escape(str(item.get('id', '')))}</td>"
            f"<td><a href=\"{page_url}\">link</a></td>"
            f"<td>{html.escape(str(item.get('type', '')))}</td>"
            f"<td>{html.escape(str(item.get('tags', '')))}</td>"
            f"<td>{html.escape(str(item.get('width', '')))} x {html.escape(str(item.get('height', '')))}</td>"
            f"<td>{html.escape(str(item.get('downloads', '')))}</td>"
            f"<td>{html.escape(str(item.get('likes', '')))}</td>"
            f"<td>{html.escape(str(item.get('comments', '')))}</td>"
            f"<td>{html.escape(str(item.get('views', '')))}</td>"
            f"<td>{html.escape(str(item.get('favorites', '')))}</td>"
            f"<td>{html.escape(str(item.get('user', '')))} ({html.escape(str(item.get('user_id', '')))})</td>"
            "</tr>"
        )

    html_content = f"""<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <title>Pixabay Download Details</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 20px; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; vertical-align: top; }}
    th {{ background: #f3f3f3; }}
    tr:nth-child(even) {{ background: #fafafa; }}
  </style>
</head>
<body>
  <h1>Pixabay Download Details</h1>
  <p>Total images: {len(details)}</p>
  <table>
    <thead>
      <tr>
        <th>File</th><th>ID</th><th>Page</th><th>Type</th><th>Tags</th><th>Size</th>
        <th>Downloads</th><th>Likes</th><th>Comments</th><th>Views</th><th>Favorites</th><th>User</th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
</body>
</html>
"""
    html_path = destination / "image_details.html"
    html_path.write_text(html_content, encoding="utf-8")
    debug_log(debug, f"Wrote metadata HTML: {html_path}")


def main() -> None:
    print("Pixabay Mass Downloader")
    debug = prompt_debug_mode()
    parent_dir = prompt_parent_directory()
    folder_name = prompt_folder_name()
    query = prompt_search_query()
    requested_count = prompt_image_count()
    api_key = prompt_api_key()
    options = prompt_advanced_options(requested_count)

    target_dir = parent_dir / folder_name
    target_dir.mkdir(parents=True, exist_ok=True)
    debug_log(debug, f"Output directory: {target_dir}")

    print("\nSearching Pixabay via API...")

    try:
        hits = fetch_hits(api_key, query, options, debug)
    except requests.HTTPError as exc:
        print(f"Pixabay API request failed: {exc}")
        print("Verify your API key and filters, then try again.")
        return

    if not hits:
        print("No images found for that query.")
        return

    if len(hits) < requested_count:
        print(f"Only found {len(hits)} images. Downloading available images.")

    details = download_images(hits, target_dir, debug)
    save_details_files(details, target_dir, debug)
    print(f"Done! Saved {len(details)} images to: {target_dir}")
    print(f"Saved details pages: {target_dir / 'image_details.html'} and {target_dir / 'image_details.json'}")


if __name__ == "__main__":
    main()

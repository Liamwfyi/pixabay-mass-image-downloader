#!/usr/bin/env python3
"""Minimal Pixabay image mass downloader (API-based)."""

from __future__ import annotations

import html
import json
import os
from pathlib import Path
from typing import Any, Dict, List

import requests

MAX_IMAGES = 100
API_URL = "https://pixabay.com/api/"
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
    min_width = prompt_positive_int("Minimum width in px", 0)
    min_height = prompt_positive_int("Minimum height in px", 0)
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


def fetch_hits(api_key: str, query: str, options: Dict[str, str]) -> List[Dict[str, Any]]:
    params = {"key": api_key, "q": query, **options}
    response = requests.get(API_URL, params=params, timeout=30)
    response.raise_for_status()

    payload = response.json()
    hits = payload.get("hits", [])
    if not isinstance(hits, list):
        return []
    return [hit for hit in hits if isinstance(hit, dict)]


def download_images(hits: List[Dict[str, Any]], destination: Path) -> List[Dict[str, Any]]:
    details: List[Dict[str, Any]] = []

    for idx, hit in enumerate(hits, start=1):
        url = hit.get("largeImageURL") or hit.get("webformatURL")
        if not isinstance(url, str) or not url:
            continue

        response = requests.get(url, timeout=60, stream=True)
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

    return details


def save_details_files(details: List[Dict[str, Any]], destination: Path) -> None:
    json_path = destination / "image_details.json"
    json_path.write_text(json.dumps(details, indent=2), encoding="utf-8")

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


def main() -> None:
    print("Pixabay Mass Downloader")
    parent_dir = prompt_parent_directory()
    folder_name = prompt_folder_name()
    query = prompt_search_query()
    requested_count = prompt_image_count()
    api_key = prompt_api_key()
    options = prompt_advanced_options(requested_count)

    target_dir = parent_dir / folder_name
    target_dir.mkdir(parents=True, exist_ok=True)

    print("\nSearching Pixabay via API...")

    try:
        hits = fetch_hits(api_key, query, options)
    except requests.HTTPError as exc:
        print(f"Pixabay API request failed: {exc}")
        print("Verify your API key and filters, then try again.")
        return

    if not hits:
        print("No images found for that query.")
        return

    if len(hits) < requested_count:
        print(f"Only found {len(hits)} images. Downloading available images.")

    details = download_images(hits, target_dir)
    save_details_files(details, target_dir)
    print(f"Done! Saved {len(details)} images to: {target_dir}")
    print(f"Saved details pages: {target_dir / 'image_details.html'} and {target_dir / 'image_details.json'}")


if __name__ == "__main__":
    main()

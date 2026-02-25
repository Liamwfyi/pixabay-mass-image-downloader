#!/usr/bin/env python3
"""Minimal Pixabay image mass downloader (API-based)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

import requests

MAX_IMAGES = 100
API_URL = "https://pixabay.com/api/"


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


def fetch_image_urls(api_key: str, query: str, limit: int) -> List[str]:
    params = {
        "key": api_key,
        "q": query,
        "image_type": "photo",
        "safesearch": "true",
        "per_page": str(limit),
        "page": "1",
    }

    response = requests.get(API_URL, params=params, timeout=30)
    response.raise_for_status()

    payload = response.json()
    hits = payload.get("hits", [])
    if not isinstance(hits, list):
        return []

    found: List[str] = []
    for hit in hits:
        if not isinstance(hit, dict):
            continue

        image_url = hit.get("largeImageURL") or hit.get("webformatURL")
        if not isinstance(image_url, str) or not image_url:
            continue

        found.append(image_url)
        if len(found) >= limit:
            break

    return found


def download_images(urls: List[str], destination: Path) -> None:
    for idx, url in enumerate(urls, start=1):
        response = requests.get(url, timeout=60, stream=True)
        response.raise_for_status()

        ext = Path(url.split("?")[0]).suffix or ".jpg"
        filename = destination / f"image_{idx:03d}{ext.lower()}"

        with filename.open("wb") as out_file:
            for chunk in response.iter_content(chunk_size=1024 * 64):
                if chunk:
                    out_file.write(chunk)

        print(f"Downloaded {idx}/{len(urls)}: {filename.name}")


def main() -> None:
    print("Pixabay Mass Downloader")
    parent_dir = prompt_parent_directory()
    folder_name = prompt_folder_name()
    query = prompt_search_query()
    requested_count = prompt_image_count()
    api_key = prompt_api_key()

    target_dir = parent_dir / folder_name
    target_dir.mkdir(parents=True, exist_ok=True)

    print("Searching Pixabay via API...")

    try:
        image_urls = fetch_image_urls(api_key, query, requested_count)
    except requests.HTTPError as exc:
        print(f"Pixabay API request failed: {exc}")
        print("Verify your API key and try again.")
        return

    if not image_urls:
        print("No images found for that query.")
        return

    if len(image_urls) < requested_count:
        print(f"Only found {len(image_urls)} images. Downloading available images.")

    download_images(image_urls, target_dir)
    print(f"Done! Saved {len(image_urls)} images to: {target_dir}")


if __name__ == "__main__":
    main()

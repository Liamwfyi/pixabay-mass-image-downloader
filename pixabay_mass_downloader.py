#!/usr/bin/env python3
"""Minimal Pixabay image mass downloader."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List
from urllib.parse import quote

import cloudscraper
from bs4 import BeautifulSoup

MAX_IMAGES = 100


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


def build_search_url(query: str) -> str:
    return f"https://pixabay.com/photos/search/{quote(query)}/?content_type=authentic"


def fetch_image_urls(query: str, limit: int) -> List[str]:
    search_url = build_search_url(query)
    scraper = cloudscraper.create_scraper(browser="chrome")
    response = scraper.get(search_url, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    found: List[str] = []
    seen = set()

    for script in soup.find_all("script", type="application/ld+json"):
        content = script.string or script.get_text()
        if not content.strip():
            continue
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            continue

        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("@type") != "ImageObject":
                continue

            url = item.get("contentUrl")
            if not isinstance(url, str):
                continue
            if not re.match(r"^https://cdn\.pixabay\.com/photo/.*\.(jpg|jpeg|png)$", url, re.IGNORECASE):
                continue
            if url in seen:
                continue

            seen.add(url)
            found.append(url)
            if len(found) >= limit:
                return found

    return found


def download_images(urls: List[str], destination: Path) -> None:
    scraper = cloudscraper.create_scraper(browser="chrome")

    for idx, url in enumerate(urls, start=1):
        response = scraper.get(url, timeout=60, stream=True)
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

    target_dir = parent_dir / folder_name
    target_dir.mkdir(parents=True, exist_ok=True)

    print("Searching Pixabay...")
    image_urls = fetch_image_urls(query, requested_count)
    if not image_urls:
        print("No images found for that query.")
        return

    if len(image_urls) < requested_count:
        print(f"Only found {len(image_urls)} images. Downloading available images.")

    download_images(image_urls, target_dir)
    print(f"Done! Saved {len(image_urls)} images to: {target_dir}")


if __name__ == "__main__":
    main()

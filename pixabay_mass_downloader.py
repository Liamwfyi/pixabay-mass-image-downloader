#!/usr/bin/env python3
"""Pixabay mass downloader with CLI and Tkinter GUI modes."""

from __future__ import annotations

import argparse
import html
import json
import os
import random
import threading
import time
from pathlib import Path
from tkinter import END, StringVar, Tk, filedialog, messagebox, ttk
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


def prompt_debug_mode() -> bool:
    while True:
        raw = input("Enable debug mode? [y/N]: ").strip().lower()
        if raw in ("", "n", "no"):
            return False
        if raw in ("y", "yes"):
            return True
        print("Please enter y or n.")


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
    debug_log(debug, f"Pixabay API response body (sanitized): {json.dumps(sanitize_debug_data(payload), indent=2)}")
    hits = payload.get("hits", [])
    if not isinstance(hits, list):
        return []
    return [hit for hit in hits if isinstance(hit, dict)]


def download_images(hits: List[Dict[str, Any]], destination: Path, debug: bool) -> tuple[List[Dict[str, Any]], int]:
    details: List[Dict[str, Any]] = []
    failed_downloads = 0

    for idx, hit in enumerate(hits, start=1):
        url = hit.get("largeImageURL") or hit.get("webformatURL")
        if not isinstance(url, str) or not url:
            debug_log(debug, f"Skipping hit {idx}: no usable image URL.")
            continue

        try:
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
        except requests.HTTPError as exc:
            failed_downloads += 1
            print(f"Skipping image {idx}/{len(hits)} after retries failed: {exc}")
            continue

        ext = Path(url.split("?")[0]).suffix or ".jpg"
        filename = destination / f"image_{idx:03d}{ext.lower()}"
        with filename.open("wb") as out_file:
            for chunk in response.iter_content(chunk_size=1024 * 64):
                if chunk:
                    out_file.write(chunk)

        details.append(
            {
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
        )
        print(f"Downloaded {idx}/{len(hits)}: {filename.name}")
        time.sleep(DOWNLOAD_COOLDOWN_SECONDS + random.uniform(0.05, 0.25))

    return details, failed_downloads


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
<html><head><meta charset=\"utf-8\" /><title>Pixabay Download Details</title>
<style>body {{ font-family: Arial, sans-serif; margin: 20px; }} table {{ border-collapse: collapse; width: 100%; }} th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; vertical-align: top; }} th {{ background: #f3f3f3; }} tr:nth-child(even) {{ background: #fafafa; }}</style>
</head><body><h1>Pixabay Download Details</h1><p>Total images: {len(details)}</p>
<table><thead><tr><th>File</th><th>ID</th><th>Page</th><th>Type</th><th>Tags</th><th>Size</th><th>Downloads</th><th>Likes</th><th>Comments</th><th>Views</th><th>Favorites</th><th>User</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
</body></html>"""
    html_path = destination / "image_details.html"
    html_path.write_text(html_content, encoding="utf-8")
    debug_log(debug, f"Wrote metadata HTML: {html_path}")


def run_download_job(
    *,
    parent_dir: Path,
    folder_name: str,
    query: str,
    requested_count: int,
    api_key: str,
    options: Dict[str, str],
    debug: bool,
) -> tuple[Path, int, int]:
    target_dir = parent_dir / folder_name
    target_dir.mkdir(parents=True, exist_ok=True)
    print("\nSearching Pixabay via API...")

    hits = fetch_hits(api_key, query, options, debug)
    if not hits:
        raise ValueError("No images found for that query.")

    details, failed_downloads = download_images(hits, target_dir, debug)
    save_details_files(details, target_dir, debug)
    return target_dir, len(details), failed_downloads


def run_cli() -> None:
    print("Pixabay Mass Downloader")
    debug = prompt_debug_mode()
    parent_dir = prompt_parent_directory()
    folder_name = prompt_folder_name()
    query = prompt_search_query()
    requested_count = prompt_image_count()
    api_key = prompt_api_key()
    options = prompt_advanced_options(requested_count)

    try:
        target_dir, saved_count, failed_downloads = run_download_job(
            parent_dir=parent_dir,
            folder_name=folder_name,
            query=query,
            requested_count=requested_count,
            api_key=api_key,
            options=options,
            debug=debug,
        )
    except requests.HTTPError as exc:
        print(f"Pixabay API request failed: {exc}")
        print("Verify your API key and filters, then try again.")
        return
    except ValueError as exc:
        print(str(exc))
        return

    print(f"Done! Saved {saved_count} images to: {target_dir}")
    if failed_downloads:
        print(f"Completed with {failed_downloads} skipped images due to repeated HTTP errors.")
    print(f"Saved details pages: {target_dir / 'image_details.html'} and {target_dir / 'image_details.json'}")


class DownloaderGUI:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title("Pixabay Mass Downloader")
        self.root.geometry("720x560")

        self.save_dir = StringVar(value=str(Path.home() / "Desktop"))
        self.folder_name = StringVar(value="pixabay-downloads")
        self.query = StringVar()
        self.count = StringVar(value="10")
        self.api_key = StringVar(value=os.getenv("PIXABAY_API_KEY", ""))
        self.debug = StringVar(value="0")

        self.lang = StringVar(value="en")
        self.image_type = StringVar(value="photo")
        self.orientation = StringVar(value="all")
        self.order = StringVar(value="popular")
        self.safesearch = StringVar(value="true")
        self.editors_choice = StringVar(value="false")
        self.page = StringVar(value="1")
        self.category = StringVar(value="")
        self.color = StringVar(value="")

        self._build()

    def _build(self) -> None:
        frm = ttk.Frame(self.root, padding=12)
        frm.pack(fill="both", expand=True)

        row = 0
        ttk.Label(frm, text="Save location").grid(row=row, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.save_dir, width=60).grid(row=row, column=1, sticky="we")
        ttk.Button(frm, text="Browse", command=self._browse).grid(row=row, column=2, padx=6)

        row += 1
        ttk.Label(frm, text="Folder name").grid(row=row, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.folder_name).grid(row=row, column=1, columnspan=2, sticky="we")

        row += 1
        ttk.Label(frm, text="Search query").grid(row=row, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.query).grid(row=row, column=1, columnspan=2, sticky="we")

        row += 1
        ttk.Label(frm, text="Image count (1-100)").grid(row=row, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.count).grid(row=row, column=1, columnspan=2, sticky="we")

        row += 1
        ttk.Label(frm, text="Pixabay API key").grid(row=row, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.api_key, show="*").grid(row=row, column=1, columnspan=2, sticky="we")

        row += 1
        ttk.Checkbutton(frm, text="Debug mode", variable=self.debug, onvalue="1", offvalue="0").grid(
            row=row, column=0, sticky="w"
        )

        row += 1
        ttk.Separator(frm).grid(row=row, column=0, columnspan=3, sticky="we", pady=8)

        row += 1
        ttk.Label(frm, text="Advanced filters").grid(row=row, column=0, sticky="w")

        row += 1
        ttk.Label(frm, text="Language").grid(row=row, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.lang).grid(row=row, column=1, sticky="we")
        ttk.Label(frm, text="Image type").grid(row=row, column=2, sticky="w")

        row += 1
        ttk.Combobox(frm, textvariable=self.image_type, values=VALID_IMAGE_TYPES, state="readonly").grid(row=row, column=2, sticky="we")
        ttk.Label(frm, text="Orientation").grid(row=row, column=0, sticky="w")
        ttk.Combobox(frm, textvariable=self.orientation, values=VALID_ORIENTATIONS, state="readonly").grid(row=row, column=1, sticky="we")

        row += 1
        ttk.Label(frm, text="Order").grid(row=row, column=0, sticky="w")
        ttk.Combobox(frm, textvariable=self.order, values=VALID_ORDERS, state="readonly").grid(row=row, column=1, sticky="we")
        ttk.Label(frm, text="Safe search").grid(row=row, column=2, sticky="w")

        row += 1
        ttk.Combobox(frm, textvariable=self.safesearch, values=VALID_BOOL, state="readonly").grid(row=row, column=2, sticky="we")
        ttk.Label(frm, text="Editor's choice").grid(row=row, column=0, sticky="w")
        ttk.Combobox(frm, textvariable=self.editors_choice, values=VALID_BOOL, state="readonly").grid(row=row, column=1, sticky="we")

        row += 1
        ttk.Label(frm, text="Page").grid(row=row, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.page).grid(row=row, column=1, sticky="we")
        ttk.Label(frm, text="Category (optional)").grid(row=row, column=2, sticky="w")

        row += 1
        ttk.Combobox(frm, textvariable=self.category, values=("", *VALID_CATEGORIES)).grid(row=row, column=2, sticky="we")
        ttk.Label(frm, text="Color (optional)").grid(row=row, column=0, sticky="w")
        ttk.Combobox(frm, textvariable=self.color, values=("", *VALID_COLORS)).grid(row=row, column=1, sticky="we")

        row += 1
        ttk.Button(frm, text="Start Download", command=self._start).grid(row=row, column=0, pady=10, sticky="w")

        row += 1
        self.log = ttk.Treeview(frm, columns=("msg",), show="headings", height=10)
        self.log.heading("msg", text="Status")
        self.log.grid(row=row, column=0, columnspan=3, sticky="nsew")

        frm.columnconfigure(1, weight=1)
        frm.columnconfigure(2, weight=1)
        frm.rowconfigure(row, weight=1)

    def _browse(self) -> None:
        chosen = filedialog.askdirectory(initialdir=self.save_dir.get())
        if chosen:
            self.save_dir.set(chosen)

    def _append_log(self, message: str) -> None:
        self.log.insert("", END, values=(message,))

    def _collect_options(self, requested_count: int) -> Dict[str, str]:
        options = {
            "lang": self.lang.get().strip() or "en",
            "image_type": self.image_type.get() or "photo",
            "orientation": self.orientation.get() or "all",
            "order": self.order.get() or "popular",
            "safesearch": self.safesearch.get() or "true",
            "editors_choice": self.editors_choice.get() or "false",
            "page": self.page.get().strip() or "1",
            "per_page": str(requested_count),
        }
        if self.category.get().strip():
            options["category"] = self.category.get().strip()
        if self.color.get().strip():
            options["colors"] = self.color.get().strip()
        return options

    def _start(self) -> None:
        try:
            count = int(self.count.get().strip())
            if not (1 <= count <= MAX_IMAGES):
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid count", f"Image count must be between 1 and {MAX_IMAGES}.")
            return

        if not self.query.get().strip() or not self.folder_name.get().strip() or not self.api_key.get().strip():
            messagebox.showerror("Missing fields", "Folder name, search query, and API key are required.")
            return

        self._append_log("Starting download...")

        def worker() -> None:
            try:
                target_dir, saved_count, failed_count = run_download_job(
                    parent_dir=Path(self.save_dir.get().strip()).expanduser(),
                    folder_name=self.folder_name.get().strip(),
                    query=self.query.get().strip(),
                    requested_count=count,
                    api_key=self.api_key.get().strip(),
                    options=self._collect_options(count),
                    debug=self.debug.get() == "1",
                )
                self.root.after(0, lambda: self._append_log(f"Done. Saved {saved_count} images to {target_dir}"))
                if failed_count:
                    self.root.after(0, lambda: self._append_log(f"Skipped {failed_count} images after retries."))
                self.root.after(0, lambda: self._append_log("Saved image_details.html and image_details.json"))
            except Exception as exc:  # noqa: BLE001
                self.root.after(0, lambda: self._append_log(f"Error: {exc}"))
                self.root.after(0, lambda: messagebox.showerror("Download error", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def run(self) -> None:
        self.root.mainloop()


def run_gui() -> None:
    DownloaderGUI().run()


def main() -> None:
    parser = argparse.ArgumentParser(description="Pixabay mass image downloader")
    parser.add_argument("--gui", action="store_true", help="Launch Tkinter GUI")
    args = parser.parse_args()

    if args.gui:
        run_gui()
        return

    run_cli()


if __name__ == "__main__":
    main()

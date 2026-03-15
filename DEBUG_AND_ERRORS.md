# Debug Mode and Error Codes

This document explains how debug mode works and describes every error code the downloader can produce.

---

## Debug Mode

### What it does

When debug mode is enabled, the downloader prints detailed diagnostic messages to the terminal prefixed with `[DEBUG]`. These messages let you trace exactly what the application is doing at each step without changing its normal behaviour.

### How to enable it

**CLI mode**

At startup you will be prompted:

```
Enable debug mode? [y/N]:
```

Type `y` or `yes` and press Enter to enable it. Press Enter (or type `n`) to leave it off.

**GUI mode**

Check the **Debug mode** checkbox before clicking **Start**.

### What gets logged

| Event | Example message |
|---|---|
| API search request (each attempt) | `[DEBUG] Pixabay API search: attempt 1/5 -> GET https://pixabay.com/api/` |
| API search response status | `[DEBUG] Pixabay API search: status 200` |
| Full API response body | `[DEBUG] Pixabay API response body (sanitized): { ... }` |
| Rate-limit response headers | `[DEBUG] Pixabay API search: rate limit headers { ... }` |
| Image download attempt (each attempt) | `[DEBUG] Image download 3/10: attempt 1/5 -> GET <redacted>` |
| Image download response status | `[DEBUG] Image download 3/10: status 200` |
| Skipped hit with no usable URL | `[DEBUG] Skipping hit 2: no usable image URL.` |
| Metadata JSON file written | `[DEBUG] Wrote metadata JSON: /path/to/image_details.json` |
| Metadata HTML file written | `[DEBUG] Wrote metadata HTML: /path/to/image_details.html` |

### URL redaction

Image download URLs are automatically replaced with `<redacted>` in debug output to avoid logging potentially sensitive direct-download links. For Pixabay search requests, the base URL (`https://pixabay.com/api/`) is logged as shown in the table above, and the request parameters (including your API key) are logged separately in a params debug line. Because the API key appears in that params debug output, you should treat all debug logs as sensitive.

Any dictionary key containing `"url"` (case-insensitive) in the sanitised API response body is also replaced with `<redacted>`.

---

## Error Codes and Messages

### HTTP status codes

| Code | Meaning | What the downloader does |
|---|---|---|
| **200** | OK | Continues normally. |
| **400** | Bad Request | Raises an HTTP error. Check that all filter values are valid for the Pixabay API. |
| **403** | Forbidden | Raises an HTTP error. Your API key may be missing, invalid, or revoked. |
| **429** | Too Many Requests (rate limited) | Automatically retries up to **5 times** using exponential back-off with jitter. If a `Retry-After` header is present its value is used as the wait time instead. If all retries are exhausted the last response is returned and the request fails. |
| **Other 4xx / 5xx** | Other HTTP error | The response is returned and `.raise_for_status()` turns it into an `HTTPError`. |

#### Retry timing for `429`

| Attempt | Approximate wait (no `Retry-After` header) |
|---|---|
| 1 | ~1.6 – 2.1 s |
| 2 | ~3.1 – 3.6 s |
| 3 | ~6.1 – 6.6 s |
| 4 | ~12.1 – 12.6 s |
| 5 | (last attempt, request returned immediately) |

### Application errors

#### `Pixabay API request failed: <details>`

**When:** The Pixabay search API returns a 4xx or 5xx response after all retries.  
**Cause:** Invalid API key, bad filter values, or a server-side problem.  
**Fix:** Verify your API key is active and that every filter option matches the values documented at [https://pixabay.com/api/docs/](https://pixabay.com/api/docs/).

---

#### `No images found for that query.`

**When:** The API responded successfully but returned zero results.  
**Cause:** The search query or combination of filters matched no images.  
**Fix:** Broaden your query, remove restrictive filters (e.g. `editors_choice`, `safesearch`, narrow `category`), or try a different search term.

---

#### `Skipping image <n>/<total> after retries failed: <details>`

**When:** A single image download fails with an HTTP error after all retry attempts.  
**Cause:** The image URL returned a persistent error (e.g. `404 Not Found`, `403 Forbidden`).  
**Behaviour:** The failed image is counted and skipped; the remaining images in the batch continue downloading.  
**Summary line:** At the end of a run with at least one failure you will see:

```
Completed with <n> skipped images due to repeated HTTP errors.
```

---

#### `Image count must be between 1 and 100.` *(GUI only)*

**When:** The **Image count** field contains a value outside the range 1–100, or is not a valid integer.  
**Fix:** Enter a whole number between 1 and 100.

---

#### `Folder name, search query, and API key are required.` *(GUI only)*

**When:** The **Folder name**, **Search query**, or **API key** field is blank when you click **Start**.  
**Fix:** Fill in all three required fields before starting a download.

---

#### `Download error: <details>` *(GUI only)*

**When:** An unexpected exception occurs inside the download worker thread.  
**Cause:** Any error not covered by the specific handlers above (e.g. a filesystem permission error, a network connectivity problem).  
**Fix:** Read the message shown in the error dialogue for specific details.

---

### Internal errors (should not occur in normal use)

#### `RuntimeError: Unreachable retry loop state`

**When:** The retry loop exits without returning a response — this should never happen.  
**Cause:** A logic error in `request_with_retry`. If you see this, please open a bug report.

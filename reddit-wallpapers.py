#!/usr/bin/env python3
"""Cycle Caelestia's wallpaper through image posts from a Reddit community."""

from __future__ import annotations

import base64
import getpass
import html
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

APP_NAME = "caelestia-reddit-wallpapers"
APP_VERSION = "1.0"
CONFIG_DIR = Path.home() / ".config" / "reddit-wallpaper"
CONFIG_FILE = CONFIG_DIR / "config.json"
CACHE_ROOT = Path.home() / ".cache" / "reddit-wallpaper"
MAX_IMAGE_BYTES = 40 * 1024 * 1024
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MIME_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def prompt_credentials() -> dict[str, str]:
    print("\nReddit read-only API setup")
    print("Create a Reddit app at https://www.reddit.com/prefs/apps")
    print("Choose the 'script' app type. No Reddit password is needed by this program.\n")
    client_id = input("Personal use script (client ID): ").strip()
    client_secret = getpass.getpass("Secret: ").strip()
    username = input("Your Reddit username (without u/): ").strip().removeprefix("u/").removeprefix("/")

    if not client_id or not client_secret or not username:
        raise SystemExit("Client ID, secret, and Reddit username are all required.")

    config = {"client_id": client_id, "client_secret": client_secret, "username": username}
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.chmod(0o700)
    CONFIG_FILE.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    CONFIG_FILE.chmod(0o600)
    print(f"Saved credentials securely in {CONFIG_FILE}\n")
    return config


def load_credentials() -> dict[str, str]:
    if not CONFIG_FILE.exists():
        return prompt_credentials()
    try:
        config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        for key in ("client_id", "client_secret", "username"):
            if not isinstance(config.get(key), str) or not config[key].strip():
                raise ValueError(f"Missing {key}")
        return config
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise SystemExit(f"Cannot read {CONFIG_FILE}: {exc}\nRemove or repair that file and run again.")


def user_agent(username: str) -> str:
    return f"linux:{APP_NAME}:v{APP_VERSION} (by /u/{username})"


def request_json(url: str, headers: dict[str, str], data: bytes | None = None) -> dict[str, Any]:
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=35) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read(2000).decode("utf-8", errors="replace")
        raise RuntimeError(f"Reddit returned HTTP {exc.code}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error contacting Reddit: {exc.reason}") from exc
    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Reddit returned a response that was not valid JSON.") from exc
    if not isinstance(result, dict):
        raise RuntimeError("Reddit returned an unexpected response.")
    return result


def get_access_token(config: dict[str, str]) -> str:
    basic = base64.b64encode(
        f"{config['client_id']}:{config['client_secret']}".encode("utf-8")
    ).decode("ascii")
    body = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode("ascii")
    result = request_json(
        "https://www.reddit.com/api/v1/access_token",
        {
            "Authorization": f"Basic {basic}",
            "User-Agent": user_agent(config["username"]),
            "Content-Type": "application/x-www-form-urlencoded",
        },
        body,
    )
    token = result.get("access_token")
    if not isinstance(token, str) or not token:
        raise RuntimeError(f"Reddit did not return an access token: {result}")
    return token


def extension_for(url: str, mime: str | None = None) -> str | None:
    path = urllib.parse.urlparse(url).path.lower()
    suffix = Path(path).suffix
    if suffix in ALLOWED_EXTENSIONS:
        return suffix
    if mime:
        guessed = MIME_EXTENSIONS.get(mime.lower().split(";", 1)[0].strip())
        if guessed:
            return guessed
    return None


def collect_post_images(post: dict[str, Any]) -> list[tuple[str, str]]:
    """Return (URL, extension) pairs in the order Reddit presents them."""
    if post.get("over_18"):
        return []

    images: list[tuple[str, str]] = []
    gallery = post.get("gallery_data") or {}
    metadata = post.get("media_metadata") or {}

    if isinstance(gallery, dict) and isinstance(metadata, dict):
        for item in gallery.get("items", []):
            media_id = item.get("media_id")
            media = metadata.get(media_id, {})
            source = media.get("s", {}) if isinstance(media, dict) else {}
            url = source.get("u") if isinstance(source, dict) else None
            mime = media.get("m") if isinstance(media, dict) else None
            if isinstance(url, str):
                url = html.unescape(url)
                ext = extension_for(url, mime)
                if ext:
                    images.append((url, ext))
        if images:
            return images

    candidates: list[tuple[str, str | None]] = []
    direct_url = post.get("url_overridden_by_dest") or post.get("url")
    if isinstance(direct_url, str):
        candidates.append((direct_url, None))

    # Reddit's preview source is normally the highest-resolution image exposed
    # in the post JSON. Use it when the direct URL did not identify an image.
    if not candidates or not extension_for(candidates[0][0]):
        try:
            source = post["preview"]["images"][0]["source"]
            if isinstance(source.get("url"), str):
                candidates.append((source["url"], source.get("mime")))
        except (KeyError, IndexError, TypeError):
            pass

    for url, mime in candidates:
        url = html.unescape(url)
        ext = extension_for(url, mime)
        if ext:
            images.append((url, ext))
            break
    return images


def fetch_wallpapers(
    subreddit: str, sort: str, time_filter: str, max_posts: int, config: dict[str, str]
) -> list[dict[str, str]]:
    token = get_access_token(config)
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": user_agent(config["username"]),
    }
    collected: list[dict[str, str]] = []
    after: str | None = None
    pages = (max_posts + 99) // 100
    scanned = 0

    for page in range(pages):
        params = {"limit": "100", "raw_json": "1"}
        if sort == "top":
            params["t"] = time_filter
        if after:
            params["after"] = after
        url = f"https://oauth.reddit.com/r/{subreddit}/{sort}?{urllib.parse.urlencode(params)}"
        result = request_json(url, headers)
        listing = result.get("data", {})
        children = listing.get("children", [])
        for child in children:
            if scanned >= max_posts:
                break
            scanned += 1
            post = child.get("data", {})
            post_id = str(post.get("id") or "")
            title = str(post.get("title") or "Untitled")
            for image_index, (image_url, ext) in enumerate(collect_post_images(post), start=1):
                collected.append({
                    "post_id": post_id or f"item{len(collected)}",
                    "title": title,
                    "url": image_url,
                    "extension": ext,
                    "image_index": str(image_index),
                })
        after = listing.get("after")
        if not after or not children or scanned >= max_posts:
            break
        print(f"Scanned {scanned} Reddit posts; found {len(collected)} images...", flush=True)

    # De-duplicate image URLs while preserving Reddit's order.
    unique: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in collected:
        if item["url"] not in seen:
            seen.add(item["url"])
            unique.append(item)
    return unique


def download_image(item: dict[str, str], target_dir: Path, username: str) -> Path:
    safe_id = re.sub(r"[^A-Za-z0-9_-]", "_", item["post_id"])
    filename = f"{safe_id}_{item['image_index']}{item['extension']}"
    target = target_dir / filename
    if target.exists() and target.stat().st_size > 0:
        return target

    req = urllib.request.Request(
        item["url"],
        headers={"User-Agent": user_agent(username), "Accept": "image/avif,image/webp,image/*,*/*;q=0.8"},
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            content_type = response.headers.get("Content-Type", "").lower()
            payload = response.read(MAX_IMAGE_BYTES + 1)
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        raise RuntimeError(f"Could not download image: {exc}") from exc

    if len(payload) > MAX_IMAGE_BYTES:
        raise RuntimeError("Image is larger than 40 MiB; skipping it.")
    if content_type and not content_type.startswith("image/"):
        raise RuntimeError(f"The image URL returned {content_type}, not an image.")
    if not payload:
        raise RuntimeError("The downloaded image was empty.")

    target_dir.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".part")
    temporary.write_bytes(payload)
    temporary.replace(target)
    return target


def set_wallpaper(path: Path) -> None:
    subprocess.run(["caelestia", "wallpaper", "-f", str(path)], check=True)


def main() -> int:
    if not shutil_which("caelestia"):
        print("Cannot find the 'caelestia' command. Check that caelestia-cli is installed and in PATH.", file=sys.stderr)
        return 1

    print("Caelestia Reddit Wallpaper Rotator")
    subreddit = input("Enter Reddit community [r/wallpaper]: ").strip() or "r/wallpaper"
    subreddit = subreddit.removeprefix("https://www.reddit.com/").removeprefix("https://reddit.com/")
    subreddit = subreddit.strip("/")
    if subreddit.lower().startswith("r/"):
        subreddit = subreddit[2:]
    if not re.fullmatch(r"[A-Za-z0-9_]{2,21}", subreddit):
        print("Enter a community name such as r/wallpaper (letters, numbers, underscores only).", file=sys.stderr)
        return 2

    sort = input("Feed order [hot/new/top] (hot): ").strip().lower() or "hot"
    if sort not in {"hot", "new", "top"}:
        print("Feed order must be hot, new, or top.", file=sys.stderr)
        return 2
    time_filter = "all"
    if sort == "top":
        time_filter = input("Top posts timeframe [all/day/week/month/year] (all): ").strip().lower() or "all"
        if time_filter not in {"all", "day", "week", "month", "year"}:
            print("Timeframe must be all, day, week, month, or year.", file=sys.stderr)
            return 2

    try:
        interval = int(input("Seconds between wallpapers [60]: ").strip() or "60")
        max_posts = int(input("How many Reddit posts to scan [300, maximum 1000]: ").strip() or "300")
    except ValueError:
        print("Interval and post count must be whole numbers.", file=sys.stderr)
        return 2
    if interval < 10:
        print("Use an interval of at least 10 seconds.", file=sys.stderr)
        return 2
    if not 100 <= max_posts <= 1000:
        print("Post count must be between 100 and 1000.", file=sys.stderr)
        return 2

    config = load_credentials()
    target_dir = CACHE_ROOT / subreddit.lower()
    print(f"\nReading r/{subreddit} ({sort}, up to {max_posts} posts)...", flush=True)

    while True:
        try:
            items = fetch_wallpapers(subreddit, sort, time_filter, max_posts, config)
        except Exception as exc:  # Keep the loop alive on transient network/API errors.
            print(f"Reddit feed error: {exc}", file=sys.stderr, flush=True)
            print("Retrying in 60 seconds...", flush=True)
            time.sleep(60)
            continue

        if not items:
            print("No supported image posts found in this listing. Try another sort order or community.", file=sys.stderr)
            return 3

        # Keep only the images in the current listing and expire cached media
        # after 24 hours. This avoids turning the cache into a permanent archive.
        target_dir.mkdir(parents=True, exist_ok=True)
        expected_files = {
            re.sub(r"[^A-Za-z0-9_-]", "_", item["post_id"])
            + "_" + item["image_index"] + item["extension"]
            for item in items
        }
        now = time.time()
        for cached in target_dir.iterdir():
            if not cached.is_file():
                continue
            try:
                too_old = now - cached.stat().st_mtime > 24 * 60 * 60
                if too_old or cached.name not in expected_files:
                    cached.unlink(missing_ok=True)
            except OSError:
                pass

        print(f"Found {len(items)} images. Changing wallpaper every {interval} seconds. Press Ctrl+C to stop.\n", flush=True)
        for index, item in enumerate(items, start=1):
            try:
                image_path = download_image(item, target_dir, config["username"])
                set_wallpaper(image_path)
                title = " ".join(item["title"].split())
                if len(title) > 90:
                    title = title[:87] + "..."
                print(f"[{index}/{len(items)}] {title}\n    {image_path}", flush=True)
            except Exception as exc:
                print(f"[{index}/{len(items)}] Skipping image: {exc}", file=sys.stderr, flush=True)
            time.sleep(interval)

        print("\nReached the end of this Reddit listing; refreshing it...\n", flush=True)


def shutil_which(command: str) -> str | None:
    import shutil
    return shutil.which(command)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nWallpaper rotation stopped.")
        raise SystemExit(0)

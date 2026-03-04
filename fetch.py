"""Fetch top App Store apps for given keywords, save metadata + screenshots locally."""

import asyncio
import json
import os
import re
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("APPTWEAK_API_KEY", "")
BASE = "https://public-api.apptweak.com/api/public"
HEADERS = {"x-apptweak-key": API_KEY}
TOP_N = 5


async def api_get(client: httpx.AsyncClient, path: str, params: dict) -> dict:
    resp = await client.get(f"{BASE}{path}", params=params, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


def pick_screenshot_urls(meta: dict) -> list[str]:
    screenshots = meta.get("screenshots", {})
    if not isinstance(screenshots, dict):
        return []
    for key in ("iphone_6_5", "iphone_5_8", "iphone6plus", "iphone6", "iphone5", "iphone"):
        ss_list = screenshots.get(key, [])
        urls = [s["url"] if isinstance(s, dict) else s for s in ss_list if (isinstance(s, dict) and s.get("url")) or isinstance(s, str)]
        if urls:
            return urls
    return []


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


async def download_image(client: httpx.AsyncClient, url: str, path: Path) -> bool:
    try:
        resp = await client.get(url)
        resp.raise_for_status()
        path.write_bytes(resp.content)
        return True
    except Exception as e:
        print(f"  WARN: failed to download {url}: {e}", file=sys.stderr)
        return False


async def run(keywords: list[str], out_dir: Path = Path("output"), top_n: int = TOP_N):
    if not API_KEY:
        print("ERROR: set APPTWEAK_API_KEY in .env", file=sys.stderr)
        sys.exit(1)

    out_dir.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient(timeout=30) as client:
        # 1. Search each keyword, collect apps
        all_apps: dict[str, dict] = {}
        for kw in keywords:
            print(f"Searching: {kw}", file=sys.stderr)
            data = await api_get(client, "/store/keywords/search-results/current", {
                "keyword": kw, "country": "us", "device": "iphone",
            })
            for app in data.get("result", {}).get("apps", [])[:20]:
                aid = str(app.get("id", ""))
                if aid in all_apps:
                    all_apps[aid]["keyword_hits"] += 1
                    all_apps[aid]["best_position"] = min(all_apps[aid]["best_position"], app.get("position", 999))
                else:
                    all_apps[aid] = {
                        "title": app.get("title", ""),
                        "keyword_hits": 1,
                        "best_position": app.get("position", 999),
                    }

        # 2. Rank and pick top N
        ranked = sorted(all_apps.items(), key=lambda x: (-x[1]["keyword_hits"], x[1]["best_position"]))
        top_ids = [aid for aid, _ in ranked[:top_n]]

        if not top_ids:
            print("No apps found.", file=sys.stderr)
            sys.exit(1)

        print(f"Top {len(top_ids)} apps: {top_ids}", file=sys.stderr)

        # 3. Fetch metadata
        data = await api_get(client, "/store/apps/metadata.json", {
            "apps": ",".join(top_ids), "country": "us", "device": "iphone",
        })

        result = data.get("result", {})
        apps_out = []

        for app_id in top_ids:
            info = result.get(app_id, {})
            meta = info.get("metadata", {})
            title = meta.get("title", app_id)
            slug = slugify(title)
            app_dir = out_dir / slug
            app_dir.mkdir(exist_ok=True)

            print(f"Downloading screenshots: {title}", file=sys.stderr)

            # Download screenshots
            urls = pick_screenshot_urls(meta)
            local_paths = []
            for i, url in enumerate(urls, 1):
                ext = "jpg" if "jpg" in url or "jpeg" in url else "png"
                img_path = app_dir / f"screenshot_{i}.{ext}"
                ok = await download_image(client, url, img_path)
                if ok:
                    local_paths.append(str(img_path))

            # Replace screenshot URLs with local paths in metadata
            meta["screenshots_local"] = local_paths
            meta["_app_id"] = app_id
            apps_out.append(meta)

        # 4. Save JSON
        out_file = out_dir / "apps.json"
        out_file.write_text(json.dumps(apps_out, indent=2, ensure_ascii=False))
        print(f"\nDone! Saved to {out_file}", file=sys.stderr)
        print(str(out_file))


def main():
    if len(sys.argv) < 2:
        print("Usage: fetch.py <keywords> [output_dir] [top_n]", file=sys.stderr)
        sys.exit(1)
    keywords = [k.strip() for k in sys.argv[1].split(",") if k.strip()]
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("output")
    top_n = int(sys.argv[3]) if len(sys.argv) > 3 else TOP_N
    asyncio.run(run(keywords, out_dir, top_n))


if __name__ == "__main__":
    main()

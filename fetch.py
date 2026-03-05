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
            result = data.get("result", {})
            # API returns either {apps: [...]} or {value: [...]} (list of IDs)
            apps_list = result.get("apps", [])
            if not apps_list:
                # value is a flat list of app IDs
                ids = result.get("value", [])
                apps_list = [{"id": aid, "title": "", "position": pos + 1} for pos, aid in enumerate(ids)]
            for app in apps_list[:20]:
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

        # 3. Fetch metadata one-by-one (some search-result apps may not exist in the US store)
        result = {}
        for aid in top_ids:
            try:
                data = await api_get(client, "/store/apps/metadata.json", {
                    "apps": aid, "country": "us", "device": "iphone",
                })
                result.update(data.get("result", {}))
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 422:
                    print(f"  WARN: app {aid} not available in US store, skipping", file=sys.stderr)
                    continue
                raise

        apps_out = []
        top_ids = [aid for aid in top_ids if aid in result]

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

            # Build slim output — drop bloat fields to reduce token usage
            versions = meta.get("versions", [])
            app_out = {
                "_app_id": app_id,
                "title": meta.get("title", ""),
                "subtitle": meta.get("subtitle", ""),
                "description": meta.get("description", ""),
                "id": meta.get("id"),
                "categories": meta.get("categories", []),
                "icon": meta.get("icon", ""),
                "rating": meta.get("rating"),
                "developer": meta.get("developer"),
                "price": meta.get("price", ""),
                "size": meta.get("size"),
                "release_date": meta.get("release_date", ""),
                "latest_version": versions[0] if versions else None,
                "dna": meta.get("dna"),
                "features": meta.get("features"),
                "screenshots_local": local_paths,
            }
            apps_out.append(app_out)

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

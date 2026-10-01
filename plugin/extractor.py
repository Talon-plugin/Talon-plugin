#!/usr/bin/env python3
import sys
import os
import json
import subprocess
import re


# ---------------------------------------------------------------------------
# Filename sanitization
# ---------------------------------------------------------------------------

def sanitize_filename(title: str, ext: str) -> str:
    clean = re.sub(r'[/\\?%*:|"<>!]', '-', title).strip()
    clean = re.sub(r'\s+', ' ', clean)
    if not clean:
        clean = "download"
    clean_ext = ext.lstrip('.').lower()
    if clean.lower().endswith(f".{clean_ext}"):
        return clean
    return f"{clean}.{clean_ext}"


# ---------------------------------------------------------------------------
# Format selection
# ---------------------------------------------------------------------------

def process_single_media(data, resolution: str):
    title = data.get("title", "Video")
    thumbnail = data.get("thumbnail", "")
    raw_formats = data.get("formats", [])

    if not raw_formats:
        direct_url = data.get("url")
        if direct_url:
            ext = data.get("ext", "mp4")
            return direct_url, None, ext, title, thumbnail
        return None, None, None, None, None

    direct_formats = []
    for f in raw_formats:
        f_url = f.get("url", "")
        if not f_url:
            continue
        proto = str(f.get("protocol", "")).lower()
        if "m3u8" in proto or ".m3u8" in f_url or "manifest/hls" in f_url or ".mpd" in f_url:
            continue
        direct_formats.append(f)

    if not direct_formats:
        direct_formats = raw_formats

    is_audio_only = (resolution.strip().lower() == "audio only")
    chosen_format = None
    chosen_ext = "m4a" if is_audio_only else "mp4"

    if is_audio_only:
        audio_formats = []
        for f in direct_formats:
            acodec = str(f.get("acodec", "none")).lower()
            vcodec = str(f.get("vcodec", "none")).lower()
            if acodec not in ["none", ""] and vcodec in ["none", ""]:
                audio_formats.append(f)

        def audio_sort_key(f):
            ext = str(f.get("ext", "")).lower()
            apple_score = 1 if ext in ["m4a", "mp3", "aac"] else 0
            abr = float(f.get("abr") or f.get("tbr") or 0.0)
            return (apple_score, abr)

        audio_formats.sort(key=audio_sort_key, reverse=True)
        chosen_format = audio_formats[0] if audio_formats else None

        if not chosen_format:
            with_audio = [f for f in direct_formats if str(f.get("acodec", "none")).lower() not in ["none", ""]]
            chosen_format = with_audio[-1] if with_audio else direct_formats[0]

        ext = str(chosen_format.get("ext", "")).lower()
        if ext in ["mp4", "m4a"]:
            chosen_ext = "m4a"
        elif ext == "mp3":
            chosen_ext = "mp3"
        elif ext in ["webm", "opus"]:
            chosen_ext = "opus"
        else:
            chosen_ext = ext or "m4a"
    else:
        requested_height = None
        for h in [2160, 1440, 1080, 720, 480, 360, 240, 144]:
            if str(h) in resolution:
                requested_height = h
                break

        video_formats = []
        for f in direct_formats:
            vcodec = str(f.get("vcodec", "none")).lower()
            note = str(f.get("format_note", "")).lower()
            if vcodec not in ["none", ""] and "storyboard" not in note:
                video_formats.append(f)

        if not video_formats:
            video_formats = direct_formats

        def parse_height(f):
            try:
                return int(f.get("height") or 0)
            except (ValueError, TypeError):
                return 0

        def parse_bitrate(f):
            try:
                return float(f.get("tbr") or f.get("vbr") or 0.0)
            except (ValueError, TypeError):
                return 0.0

        if requested_height:
            under_or_equal = [f for f in video_formats if parse_height(f) <= requested_height]
            pool = under_or_equal if under_or_equal else video_formats

            def height_sort_key(f):
                h = parse_height(f)
                has_audio = 1 if str(f.get("acodec", "none")).lower() not in ["none", ""] else 0
                is_mp4 = 1 if str(f.get("ext", "")).lower() == "mp4" else 0
                bitrate = parse_bitrate(f)
                return (h, has_audio, is_mp4, bitrate)

            pool.sort(key=height_sort_key, reverse=True)
            chosen_format = pool[0]
        else:
            def best_sort_key(f):
                h = parse_height(f)
                is_mp4 = 1 if str(f.get("ext", "")).lower() == "mp4" else 0
                has_audio = 1 if str(f.get("acodec", "none")).lower() not in ["none", ""] else 0
                bitrate = parse_bitrate(f)
                return (h, is_mp4, has_audio, bitrate)

            video_formats.sort(key=best_sort_key, reverse=True)
            chosen_format = video_formats[0]

        ext = str(chosen_format.get("ext", "")).lower()
        chosen_ext = ext if ext else "mp4"

    media_url = chosen_format.get("url")
    audio_url = None

    if not is_audio_only:
        has_audio = str(chosen_format.get("acodec", "none")).lower() not in ["none", ""]
        if not has_audio:
            audio_formats = [f for f in direct_formats if str(f.get("acodec", "none")).lower() not in ["none", ""] and str(f.get("vcodec", "none")).lower() in ["none", ""]]
            if not audio_formats:
                audio_formats = [f for f in direct_formats if str(f.get("acodec", "none")).lower() not in ["none", ""]]
            if audio_formats:
                def audio_sort_key(f):
                    e = str(f.get("ext", "")).lower()
                    apple_score = 1 if e in ["m4a", "mp3", "aac"] else 0
                    abr = float(f.get("abr") or f.get("tbr") or 0.0)
                    return (apple_score, abr)
                audio_formats.sort(key=audio_sort_key, reverse=True)
                audio_url = audio_formats[0].get("url")

    return media_url, audio_url, chosen_ext, title, thumbnail


# ---------------------------------------------------------------------------
# Build yt-dlp command
# ---------------------------------------------------------------------------

# YouTube PoToken workaround: use the Android client which bypasses the
# Proof-of-Origin (PoToken) gate that blocks web/ios clients for unauthenticated
# users. Confirmed working with yt-dlp 2026.08.x on macOS without cookies.
_YOUTUBE_EXTRACTOR_ARGS = [
    "--extractor-args", "youtube:player_client=default,android",
]


def _build_cmd(url: str) -> list:
    """Return the base yt-dlp command list for fetching full JSON info.

    uv run (called from run.sh) installs yt-dlp into the venv declared in
    pyproject.toml and sets sys.executable to that venv's Python — so we
    simply invoke `sys.executable -m yt_dlp` here, no path detection needed.
    """
    base_flags = [
        "--no-warnings",
        "-q",
        "--dump-json",
        "--yes-playlist",
    ]

    # YouTube PoToken workaround: android client bypasses the sign-in gate
    yt_flags = []
    if re.search(r"(youtube\.com|youtu\.be)", url, re.I):
        yt_flags = _YOUTUBE_EXTRACTOR_ARGS

    return [sys.executable, "-m", "yt_dlp"] + base_flags + yt_flags + ["--", url]


def _build_flat_cmd(cmd: list) -> list:
    """Convert a full-JSON command into a flat-playlist / dump-single-json command."""
    flat_cmd = cmd.copy()

    # Remove --dump-json
    if "--dump-json" in flat_cmd:
        flat_cmd.remove("--dump-json")

    # Replace --yes-playlist with --flat-playlist
    if "--yes-playlist" in flat_cmd:
        idx = flat_cmd.index("--yes-playlist")
        flat_cmd[idx] = "--flat-playlist"

    # Insert --dump-single-json immediately before the "--" URL separator
    # Correct order: ... --flat-playlist --dump-single-json -- <url>
    if "--" in flat_cmd:
        sep_idx = flat_cmd.index("--")
        flat_cmd.insert(sep_idx, "--dump-single-json")
    else:
        flat_cmd.insert(-1, "--dump-single-json")

    return flat_cmd


# ---------------------------------------------------------------------------
# Main extraction logic
# ---------------------------------------------------------------------------

def extract_media(url: str, default_resolution: str = "Best Quality"):
    cmd = _build_cmd(url)
    flat_cmd = _build_flat_cmd(cmd)

    import concurrent.futures

    try:
        proc = subprocess.Popen(flat_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = proc.communicate(timeout=60)
    except subprocess.TimeoutExpired:
        proc.kill()
        return {"status": "error", "message": "yt-dlp timed out while fetching playlist info"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to execute yt-dlp: {str(e)}"}

    if not stdout or not stdout.strip():
        err_msg = stderr.strip() if stderr else "No output from yt-dlp"
        return {"status": "error", "message": err_msg}

    playlist_title = None
    urls_to_fetch = []

    for line in stdout.splitlines():
        line = line.strip()
        if not line or not line.startswith('{'):
            continue
        try:
            metadata = json.loads(line)

            if not playlist_title and metadata.get("playlist_title"):
                playlist_title = metadata.get("playlist_title")

            if metadata.get("_type") == "playlist":
                for entry in metadata.get("entries", []):
                    # Prefer webpage_url (proper watch URL) over raw CDN url
                    u = entry.get("webpage_url") or entry.get("url")
                    if u:
                        urls_to_fetch.append(u)
            else:
                # For single videos: webpage_url is the canonical watch URL.
                # metadata.get("url") may be a signed CDN stream URL that
                # yt-dlp cannot re-fetch info for.
                u = metadata.get("webpage_url") or metadata.get("url")
                if u:
                    urls_to_fetch.append(u)
        except Exception:
            pass

    if not urls_to_fetch:
        return {"status": "error", "message": "No playable URLs found in playlist"}

    urls_to_fetch = list(dict.fromkeys(urls_to_fetch))
    is_playlist_mode = len(urls_to_fetch) > 1

    if is_playlist_mode:
        final_title = playlist_title if playlist_title else "Playlist"
        print(json.dumps({"type": "header", "total": len(urls_to_fetch), "playlist_title": final_title}), flush=True)

    parsed_items = []
    resolutions_to_check = ["Best Quality", "4K", "1440p", "1080p", "720p", "480p", "360p", "240p", "144p", "Audio Only"]

    def fetch_single(vid_url):
        single_cmd = cmd.copy()
        if "--yes-playlist" in single_cmd:
            single_cmd[single_cmd.index("--yes-playlist")] = "--no-playlist"
        # Replace the URL (last element) with the individual video URL
        single_cmd[-1] = vid_url
        try:
            p = subprocess.Popen(single_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            out, err = p.communicate(timeout=60)
            if out and out.strip():
                # Find first valid JSON line (skip any warning/debug prefix lines)
                for ln in out.splitlines():
                    ln = ln.strip()
                    if ln.startswith('{'):
                        try:
                            return json.loads(ln)
                        except Exception:
                            continue
        except Exception:
            pass
        return None

    # Fetch concurrently — capped at 3 workers to avoid rate-limiting
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        results = executor.map(fetch_single, urls_to_fetch)
        for i, data in enumerate(results):
            if data:
                item_formats = {}
                best_url = None
                best_audio_url = None
                best_ext = "mp4"
                item_title = "Video"
                item_thumb = ""

                for res in resolutions_to_check:
                    media_url, audio_url, ext, title, thumb = process_single_media(data, res)
                    if media_url:
                        item_formats[res] = media_url
                        if res == default_resolution or (best_url is None):
                            best_url = media_url
                            best_audio_url = audio_url
                            best_ext = ext
                            item_title = title
                            item_thumb = thumb

                if best_url:
                    if is_playlist_mode:
                        chunk = {
                            "type": "item",
                            "index": i,
                            "title": item_title,
                            "url": best_url,
                            "ext": best_ext,
                            "formats": item_formats,
                            "thumbnail": item_thumb
                        }
                        if best_audio_url:
                            chunk["audioUrl"] = best_audio_url
                        print(json.dumps(chunk, ensure_ascii=False), flush=True)
                    else:
                        playlist_item = {
                            "title": item_title,
                            "url": best_url,
                            "ext": best_ext,
                            "formats": item_formats,
                            "thumbnail": item_thumb
                        }
                        if best_audio_url:
                            playlist_item["audioUrl"] = best_audio_url
                        parsed_items.append(playlist_item)

    if is_playlist_mode:
        sys.exit(0)

    if not parsed_items:
        return {"status": "error", "message": "Failed to resolve direct playable stream URLs"}

    return {
        "status": "success",
        "title": parsed_items[0]["title"],
        "playlist": parsed_items
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"status": "error", "message": "Usage: extractor.py <url> [resolution]"}))
        sys.exit(1)

    url = sys.argv[1]
    resolution = sys.argv[2] if len(sys.argv) > 2 else "Best Quality"

    result = extract_media(url, resolution)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()

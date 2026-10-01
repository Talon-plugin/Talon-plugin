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

def format_resolution_label(f):
    vcodec = str(f.get("vcodec", "none")).lower()
    if vcodec in ["none", ""]:
        return None
    note = str(f.get("format_note", "")).lower()
    if "storyboard" in note:
        return None

    h = 0
    try:
        h = int(f.get("height") or 0)
    except (ValueError, TypeError):
        h = 0

    w = 0
    try:
        w = int(f.get("width") or 0)
    except (ValueError, TypeError):
        w = 0

    if "2160" in note or "4k" in note or h >= 2160 or w >= 3840:
        return "4K"
    if "1440" in note or "2k" in note or h >= 1440 or w >= 2560:
        return "1440p"
    if "1080" in note or h >= 1080 or w >= 1920:
        return "1080p"
    if "720" in note or h >= 720 or w >= 1280:
        return "720p"
    if "480" in note or h >= 480 or w >= 854:
        return "480p"
    if "360" in note or h >= 360 or w >= 640:
        return "360p"
    if "240" in note or h >= 240 or w >= 426:
        return "240p"
    if "144" in note or (0 < h < 240) or (0 < w < 426):
        return "144p"
    return None


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
            chosen_format = with_audio[-1] if with_audio else None

        if not chosen_format:
            return None, None, None, None, None

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

        if resolution == "Best Quality":
            def best_sort_key(f):
                h = parse_height(f)
                is_mp4 = 1 if str(f.get("ext", "")).lower() == "mp4" else 0
                has_audio = 1 if str(f.get("acodec", "none")).lower() not in ["none", ""] else 0
                bitrate = parse_bitrate(f)
                return (h, is_mp4, has_audio, bitrate)

            video_formats.sort(key=best_sort_key, reverse=True)
            chosen_format = video_formats[0] if video_formats else None
        else:
            # Strictly match requested resolution tier
            matching_formats = [f for f in video_formats if format_resolution_label(f) == resolution]
            if not matching_formats:
                return None, None, None, None, None

            def tier_sort_key(f):
                h = parse_height(f)
                is_mp4 = 1 if str(f.get("ext", "")).lower() == "mp4" else 0
                has_audio = 1 if str(f.get("acodec", "none")).lower() not in ["none", ""] else 0
                bitrate = parse_bitrate(f)
                return (h, is_mp4, has_audio, bitrate)

            matching_formats.sort(key=tier_sort_key, reverse=True)
            chosen_format = matching_formats[0]

        if not chosen_format:
            return None, None, None, None, None

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

# Resilient YouTube player client strategy:
# Start with android and web client fallbacks.
# If PoToken or bot challenges occur, fallback strategy will switch client tiers.
_DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

_YOUTUBE_PRIMARY_EXTRACTOR_ARGS = [
    "--extractor-args", "youtube:player_client=default,web,ios",
]

_YOUTUBE_FALLBACK_EXTRACTOR_ARGS = [
    "--extractor-args", "youtube:player_client=tv,mweb",
]

def _is_youtube(url: str) -> bool:
    return bool(re.search(r"(youtube\.com|youtu\.be)", url, re.I))

def _build_cmd(url: str, fallback_client: bool = False, no_playlist: bool = False) -> list:
    """Return the base yt-dlp command list for fetching full JSON info.

    uv run (called from run.sh) installs yt-dlp into the venv declared in
    pyproject.toml and sets sys.executable to that venv's Python — so we
    simply invoke `sys.executable -m yt_dlp` here, no path detection needed.
    """
    base_flags = [
        "--no-warnings",
        "-q",
        "--dump-json",
        "--socket-timeout", "30",
        "--retries", "5",
        "--fragment-retries", "5",
        "--extractor-retries", "3",
        "--no-check-certificates",
        "--geo-bypass",
        "--user-agent", _DEFAULT_USER_AGENT,
    ]

    if no_playlist:
        base_flags.append("--no-playlist")
    else:
        base_flags.append("--yes-playlist")

    yt_flags = []
    if _is_youtube(url):
        yt_flags = _YOUTUBE_FALLBACK_EXTRACTOR_ARGS if fallback_client else _YOUTUBE_PRIMARY_EXTRACTOR_ARGS

    return [sys.executable, "-m", "yt_dlp"] + base_flags + yt_flags + ["--", url]


def _build_flat_cmd(cmd: list) -> list:
    """Convert a full-JSON command into a flat-playlist / dump-single-json command."""
    flat_cmd = cmd.copy()

    # Remove --dump-json
    if "--dump-json" in flat_cmd:
        flat_cmd.remove("--dump-json")

    # Replace --yes-playlist or --no-playlist with --flat-playlist
    if "--yes-playlist" in flat_cmd:
        idx = flat_cmd.index("--yes-playlist")
        flat_cmd[idx] = "--flat-playlist"
    elif "--no-playlist" in flat_cmd:
        idx = flat_cmd.index("--no-playlist")
        flat_cmd[idx] = "--flat-playlist"
    else:
        flat_cmd.append("--flat-playlist")

    # Insert --dump-single-json immediately before the "--" URL separator
    if "--" in flat_cmd:
        sep_idx = flat_cmd.index("--")
        flat_cmd.insert(sep_idx, "--dump-single-json")
    else:
        flat_cmd.insert(-1, "--dump-single-json")

    return flat_cmd


# ---------------------------------------------------------------------------
# Main extraction logic
# ---------------------------------------------------------------------------

def _run_proc(cmd_list, timeout=60):
    try:
        proc = subprocess.Popen(cmd_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = proc.communicate(timeout=timeout)
        return proc.returncode, stdout, stderr
    except subprocess.TimeoutExpired:
        proc.kill()
        return -1, "", "yt-dlp timed out"
    except Exception as e:
        return -1, "", str(e)


def extract_media(url: str, default_resolution: str = "Best Quality"):
    import concurrent.futures

    resolutions_to_check = ["4K", "1440p", "1080p", "720p", "480p", "360p", "240p", "144p", "Audio Only"]
    is_yt = _is_youtube(url)
    is_likely_playlist = bool(re.search(r"([&?]list=|\/playlist|\/channel\/|\/user\/|\/c\/|@.*\/videos)", url, re.I))

    # Fast path for single videos: avoid double-invocation of yt-dlp by querying directly
    if not is_likely_playlist:
        direct_cmd = _build_cmd(url, fallback_client=False, no_playlist=True)
        rc, stdout, stderr = _run_proc(direct_cmd, timeout=60)

        # Retry with fallback client if YouTube challenged the player client
        if rc != 0 and is_yt:
            fallback_cmd = _build_cmd(url, fallback_client=True, no_playlist=True)
            rc, stdout, stderr = _run_proc(fallback_cmd, timeout=60)

        if rc == 0 and stdout and stdout.strip():
            # Check if this returned a single video or if it's secretly a multi-entry playlist
            for line in stdout.splitlines():
                line = line.strip()
                if not line or not line.startswith('{'):
                    continue
                try:
                    data = json.loads(line)
                    if data.get("_type") != "playlist":
                        # Direct single video extraction succeeded!
                        item_formats = {}
                        audio_formats = {}
                        best_url = None
                        best_audio_url = None
                        best_ext = "mp4"
                        best_res = None
                        item_title = data.get("title", "Video")
                        item_thumb = data.get("thumbnail", "")
                        http_headers = data.get("http_headers") or {}

                        for res in resolutions_to_check:
                            media_url, audio_url, ext, title, thumb = process_single_media(data, res)
                            if media_url:
                                item_formats[res] = media_url
                                if audio_url:
                                    audio_formats[res] = audio_url
                                if res == default_resolution or (best_url is None and res != "Audio Only"):
                                    best_url = media_url
                                    best_audio_url = audio_url
                                    best_ext = ext
                                    best_res = res
                                    item_title = title
                                    item_thumb = thumb

                        if not best_url and "Audio Only" in item_formats:
                            best_url = item_formats["Audio Only"]
                            best_res = "Audio Only"
                            best_ext = "m4a"

                        if best_url:
                            playlist_item = {
                                "title": item_title,
                                "url": best_url,
                                "ext": best_ext,
                                "resolution": best_res,
                                "formats": item_formats,
                                "audioFormats": audio_formats,
                                "thumbnail": item_thumb,
                                "httpHeaders": http_headers
                            }
                            if best_audio_url:
                                playlist_item["audioUrl"] = best_audio_url

                            return {
                                "status": "success",
                                "title": playlist_item["title"],
                                "url": best_url,
                                "audioUrl": best_audio_url,
                                "ext": best_ext,
                                "resolution": best_res,
                                "formats": item_formats,
                                "audioFormats": audio_formats,
                                "thumbnail": item_thumb,
                                "httpHeaders": http_headers,
                                "playlist": [playlist_item]
                            }
                except Exception:
                    pass

    # Playlist or fallback path
    cmd = _build_cmd(url, fallback_client=False, no_playlist=False)
    flat_cmd = _build_flat_cmd(cmd)

    rc, stdout, stderr = _run_proc(flat_cmd, timeout=60)
    if rc != 0 and is_yt:
        cmd = _build_cmd(url, fallback_client=True, no_playlist=False)
        flat_cmd = _build_flat_cmd(cmd)
        rc, stdout, stderr = _run_proc(flat_cmd, timeout=60)

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
                    u = entry.get("webpage_url") or entry.get("url")
                    if u:
                        urls_to_fetch.append(u)
            else:
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

    def fetch_single(vid_url):
        single_cmd = cmd.copy()
        if "--yes-playlist" in single_cmd:
            single_cmd[single_cmd.index("--yes-playlist")] = "--no-playlist"
        single_cmd[-1] = vid_url
        rc, out, err = _run_proc(single_cmd, timeout=60)
        if rc != 0 and is_yt:
            fallback_single_cmd = _build_cmd(vid_url, fallback_client=True, no_playlist=True)
            rc, out, err = _run_proc(fallback_single_cmd, timeout=60)

        if out and out.strip():
            for ln in out.splitlines():
                ln = ln.strip()
                if ln.startswith('{'):
                    try:
                        return json.loads(ln)
                    except Exception:
                        continue
        return None

    # Fetch concurrently — capped at 3 workers to avoid rate-limiting
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        results = executor.map(fetch_single, urls_to_fetch)
        for i, data in enumerate(results):
            if data:
                item_formats = {}
                audio_formats = {}
                best_url = None
                best_audio_url = None
                best_ext = "mp4"
                best_res = None
                item_title = data.get("title", "Video")
                item_thumb = data.get("thumbnail", "")
                http_headers = data.get("http_headers") or {}

                for res in resolutions_to_check:
                    media_url, audio_url, ext, title, thumb = process_single_media(data, res)
                    if media_url:
                        item_formats[res] = media_url
                        if audio_url:
                            audio_formats[res] = audio_url
                        if res == default_resolution or (best_url is None and res != "Audio Only"):
                            best_url = media_url
                            best_audio_url = audio_url
                            best_ext = ext
                            best_res = res
                            item_title = title
                            item_thumb = thumb

                if not best_url and "Audio Only" in item_formats:
                    best_url = item_formats["Audio Only"]
                    best_res = "Audio Only"
                    best_ext = "m4a"

                if best_url:
                    if is_playlist_mode:
                        chunk = {
                            "type": "item",
                            "index": i,
                            "title": item_title,
                            "url": best_url,
                            "ext": best_ext,
                            "resolution": best_res,
                            "formats": item_formats,
                            "audioFormats": audio_formats,
                            "thumbnail": item_thumb,
                            "httpHeaders": http_headers
                        }
                        if best_audio_url:
                            chunk["audioUrl"] = best_audio_url
                        print(json.dumps(chunk, ensure_ascii=False), flush=True)
                    else:
                        playlist_item = {
                            "title": item_title,
                            "url": best_url,
                            "ext": best_ext,
                            "resolution": best_res,
                            "formats": item_formats,
                            "audioFormats": audio_formats,
                            "thumbnail": item_thumb,
                            "httpHeaders": http_headers
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
        "url": parsed_items[0]["url"],
        "audioUrl": parsed_items[0].get("audioUrl"),
        "ext": parsed_items[0]["ext"],
        "resolution": parsed_items[0]["resolution"],
        "formats": parsed_items[0]["formats"],
        "audioFormats": parsed_items[0].get("audioFormats", {}),
        "thumbnail": parsed_items[0]["thumbnail"],
        "httpHeaders": parsed_items[0].get("httpHeaders", {}),
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

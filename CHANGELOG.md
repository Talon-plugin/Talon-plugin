# Changelog

All notable changes to the **Talons** universal media extractor plugin are documented in this file.

## [1.0.2] - 2026-10-01

### Fixed
- **YouTube Multi-Resolution Stream Extraction**: Removed `player_skip=configs,webpage` and adopted `default,web,ios` client tiers. This allows `yt-dlp` to download player JavaScript configs and decipher `n`-token signatures, unlocking all adaptive high-definition video tiers (`1080p`, `720p`, `480p`, etc.) rather than collapsing exclusively to legacy 360p muxed video.
- **YouTube Extraction Resilience & Bot Gate Bypass**: Enhanced `yt-dlp` arguments with multi-client fallbacks (`default,web,ios` and `tv,mweb`) and automatic fallback execution retry to prevent PoToken and "Sign in to confirm you're not a bot" failures.
- **YouTube Download 403 Forbidden Prevention**: Extracted and emitted `httpHeaders` from yt-dlp stream metadata, enabling downstream download engines to send matching browser `User-Agent` and headers to `googlevideo.com`.
- **Audio Track Preservation Across Resolutions**: Emitted per-resolution `audioFormats` mapping so switching between video tiers (e.g., 720p to 1080p or 4K) dynamically preserves and attaches the required audio stream URL, preventing silent video downloads.
- **Single Video Fast Path**: Added direct single-video extraction path that avoids running yt-dlp twice, cutting YouTube extraction latency by ~50% and preventing YouTube rate limits.
- **Robust Ffmpeg Path & Container Merge**: Resolved `ffmpeg` executable lookup across standard macOS locations (`/opt/homebrew/bin`, `/usr/local/bin`) and added `-strict -2` support in `pincer-engine` with container preservation.

## [1.0.1] - 2026-10-01

### Fixed
- **Accurate Supported Resolution Detection**: Fixed an issue where queries for unsupported resolution tiers (such as 4K or 1440p on videos that only reach 1080p) fell back to the highest available stream and masqueraded as supported resolutions, creating duplicate stream URLs.
- **Resolution Selection in Grabbit UI**: Fixed resolution selection desynchronization where selecting a resolution from the dropdown failed to update the active item because multiple tiers pointed to the same URL and dictionary lookups returned arbitrary first-match keys.
- **Audio Stream Retention**: Ensured audio stream URLs are retained across resolution switches so that switching between audio-only and video tiers preserves muxing metadata.

### Added
- **`format_resolution_label` helper in `extractor.py`**: Standardized canonical resolution tier labeling (`4K`, `1440p`, `1080p`, `720p`, `480p`, `360p`, `240p`, `144p`) based on actual video stream height, width, and format notes.
- **Strict Format Matching**: `process_single_media` strictly matches requested resolution tiers and returns `None` for unsupported resolutions instead of falling back to lower tiers.
- **Resolution Output**: Added `resolution` to emitted JSON items and playlist entries for explicit UI selection tracking in Grabbit.

# Changelog

All notable changes to the **Talons** universal media extractor plugin are documented in this file.

## [1.0.1] - 2026-10-01

### Fixed
- **Accurate Supported Resolution Detection**: Fixed an issue where queries for unsupported resolution tiers (such as 4K or 1440p on videos that only reach 1080p) fell back to the highest available stream and masqueraded as supported resolutions, creating duplicate stream URLs.
- **Resolution Selection in Grabbit UI**: Fixed resolution selection desynchronization where selecting a resolution from the dropdown failed to update the active item because multiple tiers pointed to the same URL and dictionary lookups returned arbitrary first-match keys.
- **Audio Stream Retention**: Ensured audio stream URLs are retained across resolution switches so that switching between audio-only and video tiers preserves muxing metadata.

### Added
- **`format_resolution_label` helper in `extractor.py`**: Standardized canonical resolution tier labeling (`4K`, `1440p`, `1080p`, `720p`, `480p`, `360p`, `240p`, `144p`) based on actual video stream height, width, and format notes.
- **Strict Format Matching**: `process_single_media` strictly matches requested resolution tiers and returns `None` for unsupported resolutions instead of falling back to lower tiers.
- **Resolution Output**: Added `resolution` to emitted JSON items and playlist entries for explicit UI selection tracking in Grabbit.

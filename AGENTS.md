# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Project Overview

This is a Spotify playlist automation tool designed to run as an AWS Lambda function. The main script (`newStashMaintainer.py`) performs two key functions:
1. Maintains a master playlist by aggregating tracks from all user playlists and liked songs
2. Merges a Punjabi classics playlist into a main Punjabi playlist

## Running the Script

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run the script locally
python newStashMaintainer.py
```

The script detects local execution (absence of `AWS_EXECUTION_ENV`) and automatically loads environment variables from `.env`.

### AWS Lambda Deployment
The script is designed to run as a Lambda handler via the `lambda_handler()` function. The `package/` directory contains pre-packaged dependencies for Lambda deployment, which is referenced in `.gitignore` and commit history mentions `my-deployment-package.zip`.

## Environment Variables

Required environment variables (stored in `.env` for local development, or Lambda environment variables for production):

- `SPOTIFY_CLIENT_ID` - Spotify API client ID
- `SPOTIFY_CLIENT_SECRET` - Spotify API client secret
- `SPOTIFY_REDIRECT_URI` - OAuth redirect URI
- `SPOTIFY_MASTER_PLAYLIST_ID` - ID of the master aggregation playlist
- `SPOTIFY_PUNJABI_ID` - ID of the main Punjabi playlist
- `SPOTIFY_PUNJABI_CLASSICS_ID` - ID of the Punjabi classics playlist to merge
- `SPOTIFY_INCLUDE_LIKED_SONGS` - (optional, defaults to 'true') Whether to include liked songs in master playlist

## Architecture

### Authentication & Caching
- Uses SpotifyOAuth with a `.spotify_cache` file for token persistence
- Requires scope: `playlist-read-private playlist-modify-private playlist-modify-public user-library-read`

### Core Functions

**`authenticate_spotify()`** - Handles Spotify OAuth authentication and returns authenticated client + user ID

**`get_all_items(spotify, fetch_method)`** - Generic paginated fetcher that handles Spotify's pagination with rate limiting (0.2s between requests)

**`filter_and_normalize(tracks)`** - Deduplicates tracks based on normalized (name, artists, album) tuples. Filters out local files and non-track items.

**`collect_tracks(spotify, playlists, master_playlist_id)`** - Aggregates all tracks from user playlists (excluding master playlist itself) and optionally liked songs

**`update_master_playlist(spotify, track_list, master_playlist_id)`** - Syncs master playlist by:
  - Calculating diff between desired tracks and existing tracks
  - Removing tracks no longer in source playlists (batches of 100)
  - Adding new tracks (batches of 100)

**`merge_punjabi_playlists(spotify)`** - One-way merge that adds tracks from classics playlist to main Punjabi playlist (doesn't remove tracks)

**`lambda_handler(event, context)`** - Entry point for Lambda execution and local testing

### Rate Limiting
All Spotify API calls that iterate or batch are separated by `RATE_LIMIT_SLEEP = 0.2` seconds to avoid rate limits.

### Batch Operations
Playlist modifications (add/remove) are performed in batches of 100 tracks to comply with Spotify API limits.

## Key Behaviors

- **Deduplication strategy**: Tracks are deduplicated by case-insensitive comparison of (track name, sorted artist names, album name)
- **Master playlist exclusion**: The master playlist itself is excluded from track collection to avoid circular references
- **User playlist filtering**: Only playlists owned by the authenticated user are processed
- **Punjabi playlist merge**: Additive only - adds classics tracks not already in main playlist, but doesn't remove any tracks

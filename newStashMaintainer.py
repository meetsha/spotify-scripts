import json
import os
import shutil
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import logging
from dotenv import load_dotenv

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Load environment variables from .env when running locally
if os.environ.get("AWS_EXECUTION_ENV") is None:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)

    "Getting env"
    load_dotenv()

# Configuration from environment variables
CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI')
MASTER_PLAYLIST_ID = os.getenv('SPOTIFY_MASTER_PLAYLIST_ID')
PUNJABI_PLAYLIST_ID = os.getenv('SPOTIFY_PUNJABI_ID')
PUNJABI_CLASSICS_PLAYLIST_ID = os.getenv('SPOTIFY_PUNJABI_CLASSICS_ID')


_REQUIRED_ENV_VARS = {
    'SPOTIFY_CLIENT_ID': CLIENT_ID,
    'SPOTIFY_CLIENT_SECRET': CLIENT_SECRET,
    'SPOTIFY_REDIRECT_URI': REDIRECT_URI,
    'SPOTIFY_MASTER_PLAYLIST_ID': MASTER_PLAYLIST_ID,
    'SPOTIFY_PUNJABI_ID': PUNJABI_PLAYLIST_ID,
    'SPOTIFY_PUNJABI_CLASSICS_ID': PUNJABI_CLASSICS_PLAYLIST_ID,
}
missing = [k for k, v in _REQUIRED_ENV_VARS.items() if not v]
if missing:
    raise SystemExit(f"Missing required environment variables: {', '.join(missing)}")

SCOPE = 'playlist-read-private playlist-modify-private playlist-modify-public user-library-read'
PAGE_LIMIT = 50


def get_spotify_cache_path():
    if os.environ.get("AWS_EXECUTION_ENV") is None:
        return '.spotify_cache'

    package_cache_path = os.path.join(os.environ.get('LAMBDA_TASK_ROOT', ''), '.spotify_cache')
    writable_cache_path = '/tmp/.spotify_cache'

    if not os.path.exists(writable_cache_path) and os.path.exists(package_cache_path):
        shutil.copyfile(package_cache_path, writable_cache_path)

    return writable_cache_path


def authenticate_spotify():
    auth_manager = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        cache_path=get_spotify_cache_path()
    )
    spotify = spotipy.Spotify(auth_manager=auth_manager)
    user = spotify.current_user()
    logger.info(f"Connected to Spotify as: {user['display_name']}")
    return spotify, user['id']


def extract_item(item):
    return item.get('item') or item.get('track')


def get_all_items(spotify, fetch_method):
    all_items = []
    results = fetch_method(limit=PAGE_LIMIT)
    while results:
        all_items.extend(results['items'])
        if results['next']:
            results = spotify.next(results)
        else:
            results = None
    return all_items


def get_playlist_items(spotify, playlist_id):
    return get_all_items(
        spotify,
        lambda limit: spotify.playlist_items(
            playlist_id,
            limit=limit,
            additional_types=['track'],
        ),
    )


def extract_track_uris(items):
    return [
        track['uri'] for item in items
        for track in [extract_item(item)]
        if track and track.get('type') == 'track' and track.get('uri')
    ]


def filter_and_normalize(tracks):
    seen = {}
    for item in tracks:
        track = extract_item(item)
        if track and track.get('type') == 'track' and not track.get('is_local'):
            key = (track['name'].lower(),
                   tuple(sorted(artist['name'].lower() for artist in track['artists'])),
                   track['album']['name'].lower())
            if key not in seen:
                seen[key] = track['uri']
    return set(seen.values())


def collect_tracks(spotify, playlists, master_playlist_id):
    all_tracks = []
    for playlist in playlists:
        if playlist['id'] == master_playlist_id:
            continue
        logger.info(f"Processing playlist: {playlist['name']}")
        playlist_tracks = get_playlist_items(spotify, playlist['id'])
        all_tracks.extend(playlist_tracks)

    logger.info("Processing Liked Songs")
    liked_tracks = get_all_items(spotify, spotify.current_user_saved_tracks)
    all_tracks.extend(liked_tracks)

    unique_tracks = filter_and_normalize(all_tracks)
    logger.info(f"Collected {len(unique_tracks)} unique tracks")
    return list(unique_tracks)


def update_master_playlist(spotify, track_list, master_playlist_id):
    master_playlist = spotify.playlist(master_playlist_id)
    logger.info(f"Updating master playlist: {master_playlist['name']}")

    existing_tracks_raw = get_playlist_items(spotify, master_playlist_id)
    existing_tracks = extract_track_uris(existing_tracks_raw)

    desired_set = set(track_list)
    existing_set = set(existing_tracks)
    to_add = list(desired_set - existing_set)
    to_remove = list(existing_set - desired_set)

    logger.info(f"Tracks to add: {len(to_add)}")
    logger.info(f"Tracks to remove: {len(to_remove)}")

    for i in range(0, len(to_remove), 100):
        batch = to_remove[i:i+100]
        spotify.playlist_remove_all_occurrences_of_items(master_playlist_id, batch)
        logger.info(f"Removed batch of {len(batch)} tracks")

    for i in range(0, len(to_add), 100):
        batch = to_add[i:i+100]
        spotify.playlist_add_items(master_playlist_id, batch)
        logger.info(f"Added batch of {len(batch)} tracks")


def merge_punjabi_playlists(spotify):
    logger.info(f"Merging Punjabi playlists {PUNJABI_PLAYLIST_ID} and {PUNJABI_CLASSICS_PLAYLIST_ID}")
    
    # Get tracks from both playlists
    punjabi_tracks_raw = get_playlist_items(spotify, PUNJABI_PLAYLIST_ID)
    punjabi_classic_tracks_raw = get_playlist_items(spotify, PUNJABI_CLASSICS_PLAYLIST_ID)
    
    # Extract track URIs
    punjabi_tracks = extract_track_uris(punjabi_tracks_raw)
    punjabi_classic_tracks = extract_track_uris(punjabi_classic_tracks_raw)
    
    # Find tracks to add (classic tracks not in main playlist)
    to_add = list(set(punjabi_classic_tracks) - set(punjabi_tracks))
    
    logger.info(f"Adding {len(to_add)} classic tracks to main Punjabi playlist")
    
    # Add tracks in batches of 100 (Spotify API limit)
    for i in range(0, len(to_add), 100):
        batch = to_add[i:i+100]
        spotify.playlist_add_items(PUNJABI_PLAYLIST_ID, batch)
        logger.info(f"Added batch of {len(batch)} tracks")


def lambda_handler(event=None, context=None):
    try:
        spotify, user_id = authenticate_spotify()
        
        playlists = get_all_items(spotify, spotify.current_user_playlists)
        user_playlists = [p for p in playlists if p['owner']['id'] == user_id]
        track_list = collect_tracks(spotify, user_playlists, MASTER_PLAYLIST_ID)
        update_master_playlist(spotify, track_list, MASTER_PLAYLIST_ID)
        logger.info("Master playlist update complete")
        
        merge_punjabi_playlists(spotify)
        logger.info("Punjabi playlists merged")
        
        return {
            'statusCode': 200,
            'body': json.dumps('Playlists updated successfully!')
        }
    except Exception as e:
        logger.exception("Playlist update failed")
        return {
            'statusCode': 500,
            'body': json.dumps(f"Playlist update failed: {e}")
        }


if __name__ == "__main__":
    lambda_handler()

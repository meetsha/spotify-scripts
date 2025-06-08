import json
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
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
INCLUDE_LIKED_SONGS = os.getenv('SPOTIFY_INCLUDE_LIKED_SONGS', 'true').lower() == 'true'

SCOPE = 'playlist-read-private playlist-modify-private playlist-modify-public user-library-read'

RATE_LIMIT_SLEEP = 0.2

def authenticate_spotify():
    auth_manager = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        cache_path='.spotify_cache'
    )
    spotify = spotipy.Spotify(auth_manager=auth_manager)
    user = spotify.current_user()
    logger.info(f"Connected to Spotify as: {user['display_name']}")
    return spotify, user['id']

def get_all_items(spotify, fetch_method):
    all_items = []
    results = fetch_method(limit=50)
    while results:
        all_items.extend(results['items'])
        if results['next']:
            results = spotify.next(results)
        else:
            results = None
        time.sleep(RATE_LIMIT_SLEEP)
    return all_items

def filter_and_normalize(tracks):
    seen = {}
    for item in tracks:
        track = item['track'] if 'track' in item else item.get('track')
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
        playlist_tracks = get_all_items(spotify, lambda limit: spotify.playlist_tracks(playlist['id'], limit=limit))
        all_tracks.extend(playlist_tracks)

    if INCLUDE_LIKED_SONGS:
        logger.info("Processing Liked Songs")
        liked_tracks = get_all_items(spotify, spotify.current_user_saved_tracks)
        all_tracks.extend(liked_tracks)

    unique_tracks = filter_and_normalize(all_tracks)
    logger.info(f"Collected {len(unique_tracks)} unique tracks")
    return list(unique_tracks)

def update_master_playlist(spotify, track_list, master_playlist_id):
    master_playlist = spotify.playlist(master_playlist_id)
    logger.info(f"Updating master playlist: {master_playlist['name']}")

    existing_tracks_raw = get_all_items(spotify, lambda limit: spotify.playlist_tracks(master_playlist_id, limit=limit))
    existing_tracks = [item['track']['uri'] for item in existing_tracks_raw if item.get('track')]

    to_add = list(set(track_list) - set(existing_tracks))
    to_remove = list(set(existing_tracks) - set(track_list))

    logger.info(f"Tracks to add: {len(to_add)}")
    logger.info(f"Tracks to remove: {len(to_remove)}")

    for i in range(0, len(to_remove), 100):
        batch = to_remove[i:i+100]
        spotify.playlist_remove_all_occurrences_of_items(master_playlist_id, batch)
        logger.info(f"Removed batch of {len(batch)} tracks")
        time.sleep(RATE_LIMIT_SLEEP)

    for i in range(0, len(to_add), 100):
        batch = to_add[i:i+100]
        spotify.playlist_add_items(master_playlist_id, batch)
        logger.info(f"Added batch of {len(batch)} tracks")
        time.sleep(RATE_LIMIT_SLEEP)

def merge_punjabi_playlists(spotify):
    logger.info(f"Merging Punjabi playlists {PUNJABI_PLAYLIST_ID} and {PUNJABI_CLASSICS_PLAYLIST_ID}")
    
    # Get tracks from both playlists
    punjabi_tracks_raw = get_all_items(
        spotify, lambda limit: spotify.playlist_tracks(PUNJABI_PLAYLIST_ID, limit=limit))
    punjabi_classic_tracks_raw = get_all_items(
        spotify, lambda limit: spotify.playlist_tracks(PUNJABI_CLASSICS_PLAYLIST_ID, limit=limit))
    
    # Extract track URIs
    punjabi_tracks = [item['track']['uri'] for item in punjabi_tracks_raw if item.get('track')]
    punjabi_classic_tracks = [item['track']['uri'] for item in punjabi_classic_tracks_raw if item.get('track')]
    
    # Find tracks to add (classic tracks not in main playlist)
    to_add = list(set(punjabi_classic_tracks) - set(punjabi_tracks))
    
    logger.info(f"Adding {len(to_add)} classic tracks to main Punjabi playlist")
    
    # Add tracks in batches of 100 to respect rate limits
    for i in range(0, len(to_add), 100):
        batch = to_add[i:i+100]
        spotify.playlist_add_items(PUNJABI_PLAYLIST_ID, batch)
        logger.info(f"Added batch of {len(batch)} tracks")
        time.sleep(RATE_LIMIT_SLEEP)
    
    
def lambda_handler(event=None, context=None):
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

if __name__ == "__main__":
    lambda_handler()
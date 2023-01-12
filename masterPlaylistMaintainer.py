import spotipy
from spotipy import util
from spotipy.oauth2 import SpotifyOAuth
from pprint import pprint
import os
from dotenv import load_dotenv
import time

load_dotenv()

masterPlaylistId = os.getenv('MASTER_PLAYLIST_ID')
print

def getSpotifyClient():
    token = util.prompt_for_user_token(username=os.getenv('AUTH_USERNAME'),
                                       scope=['playlist-read-private',
                                              'playlist-read-collaborative',
                                              'user-library-read',
                                              'playlist-modify-private'],
                                       client_id=os.getenv('CLIENT_ID'),
                                       client_secret=os.getenv(
                                           'CLIENT_SECRET'),
                                       redirect_uri='http://localhost:8080/')

    sp = spotipy.Spotify(auth=token)
    return sp


def getPlaylists(sp: spotipy.Spotify):
    results = sp.user_playlists(os.getenv('USERNAME'), limit=50, offset=0)
    playlists = results['items']
    while results['next']:
        results = sp.next(results)
        playlists.extend(results['items'])

    print("Total Playlists: ", len(playlists))

    playlistIds = []
    for playlist in playlists:
        if playlist['owner']['id'] == os.getenv('USERNAME'):
            playlistIds.append(playlist['id'])

    return playlistIds


def getPlaylistTracks(sp: spotipy.Spotify, playlistId: str, override=False):
    if (not override) and (playlistId == masterPlaylistId):
        return []

    results = sp.playlist_tracks(playlistId)
    tracks = results['items']
    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])

    print(len(tracks))

    trackIds = []
    for track in tracks:
        try:
            trackIds.append(track['track']['id'])
        except:
            pass

    return trackIds


def getLikedTrackIds(sp: spotipy.Spotify):
    results = sp.current_user_saved_tracks()
    tracks = results['items']
    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])

    trackIds = []
    for track in tracks:
        try:
            trackIds.append(track['track']['id'])
        except:
            pass

    return trackIds


sp = getSpotifyClient()

playlistIds = getPlaylists(sp)
pprint(playlistIds)

likedTrackIds = getLikedTrackIds(sp)
trackIds = set()

totalLength = 0
totalLength += len(likedTrackIds)

for playlistId in playlistIds:
    playlistTrackIds = getPlaylistTracks(sp, playlistId)
    totalLength += len(playlistTrackIds)
    for trackId in playlistTrackIds:
        trackIds.add(trackId)
    time.sleep(0.1)

print("Total length: ", totalLength)

trackIdsList = list(trackIds)
print("Compressed length: ", len(trackIdsList))


def addTracksToPlaylist(sp: spotipy.Spotify, playlistId: str, trackIds: list):
    existingTrackIds = getPlaylistTracks(sp, playlistId, True)
    for i in range(0, len(trackIds), 100):
        chunk = trackIds[i:i+100]
        trackIdsToAdd = list(set(chunk).difference(existingTrackIds))
        print("Length of tracks to add: ", len(trackIdsToAdd))
        if len(trackIdsToAdd) != 0:
            sp.playlist_add_items(playlistId, trackIdsToAdd)

addTracksToPlaylist(sp, masterPlaylistId, trackIdsList)

"""
pip3 install --target ./package spotipy
zip -r ../my-deployment-package.zip .
zip my-deployment-package.zip lambda_function.py
zip my-deployment-package.zip .cache-meetsha
"""

import spotipy
from spotipy import util
from pprint import pprint
import os
from dotenv import load_dotenv
import time
import random

# requesting in chunks of 100 as max len of ids in api can be 100

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

    userPlaylists = []
    for playlist in playlists:
        if playlist['owner']['id'] == os.getenv('USERNAME'):
            userPlaylists.append(playlist['id'])
            
    print("Total User Playlists: ", len(userPlaylists))
    return userPlaylists


def getPlaylistTracks(sp: spotipy.Spotify, playlistId: str):
    results = sp.playlist_tracks(playlistId)
    tracks = results['items']
    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])

    trackIds = []
    for track in tracks:
        try:
            trackIds.append(track['track'])
        except:
            pass

    return trackIds


def getLikedTracks(sp: spotipy.Spotify):
    results = sp.current_user_saved_tracks()
    tracks = results['items']
    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])

    trackIds = []
    for track in tracks:
        try:
            trackIds.append(track['track'])
        except:
            pass

    return trackIds

def filterTracksWithDupeHandling(tracks: list, returnDuplicates: bool = False) -> list: 
    result = []
    seenTracks = set()
    
    for track in tracks:
        if not track or track['type'] != "track":
            continue

        trackName = track['name']
        artistNames = ', '.join(artist['name'] for artist in track['artists'])
        
        trackIdentifier = (trackName.lower(), artistNames.lower())
        
        if (trackIdentifier in seenTracks) == returnDuplicates:
            result.append(track)

        seenTracks.add(trackIdentifier)
    
    return result

def removeTracksFromPlaylist(sp: spotipy.Spotify, playlistId: str, tracks: list, areIds: bool = False):
    for i in range(0, len(tracks), 100):
        chunkedTracks = tracks[i: i+100]

        if areIds:
            chunkedTrackIds = chunkedTracks
        else:
            chunkedTrackIds = [track['id'] for track in chunkedTracks if track]

        sp.playlist_remove_all_occurrences_of_items(playlistId, chunkedTrackIds)
        time.sleep(random.uniform(0.05, 0.2))

def replacePlaylistTracks(sp: spotipy.Spotify, playlistId: str, tracks: list):
    existingTracks = getPlaylistTracks(sp, playlistId)
    print("Existing tracks: ", len(existingTracks))

    dupeTracks = filterTracksWithDupeHandling(existingTracks, returnDuplicates=True)
    print("Duplicate tracks: ", len(dupeTracks))
    removeTracksFromPlaylist(sp, playlistId, dupeTracks)

    existingTrackIds = [track['id'] for track in existingTracks if track]
    trackIds = [track['id'] for track in tracks if track]

    removedTrackIds = list(set(existingTrackIds).difference(trackIds))
    print("Removed tracks: ", len(removedTrackIds))
    removeTracksFromPlaylist(sp, playlistId, removedTrackIds, areIds=True)

    for i in range(0, len(trackIds), 100):
        chunkedTrackIds = trackIds[i:i+100]
        trackIdsToAdd = list(set(chunkedTrackIds).difference(existingTrackIds))
        if len(trackIdsToAdd) != 0:
            print("Length of tracks to add: ", len(trackIdsToAdd))
            sp.playlist_add_items(playlistId, trackIdsToAdd)
            time.sleep(random.uniform(0.05, 0.2))

def mainFunction():
    load_dotenv()
    theStashPlaylistId = os.getenv('STASH_PLAYLIST_ID')
    sp = getSpotifyClient()

    playlistIds = getPlaylists(sp)

    likedTracks = getLikedTracks(sp)
    tracks = list()
    tracks.extend(likedTracks)

    for playlistId in playlistIds:
        if playlistId == theStashPlaylistId:
            continue
        playlistTracks = getPlaylistTracks(sp, playlistId)
        tracks.extend(playlistTracks)
        time.sleep(random.uniform(0.05, 0.2))

    print("Total length: ", len(tracks))

    dedupedTracks = filterTracksWithDupeHandling(tracks)
    print("Compressed length: ", len(dedupedTracks))

    replacePlaylistTracks(sp, theStashPlaylistId, dedupedTracks)

def lambda_handler(event, context):
    print("Starting lamba")
    mainFunction()

if __name__ == '__main__':
    mainFunction()

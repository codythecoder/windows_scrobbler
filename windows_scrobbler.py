import asyncio
import time
import re

from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as MediaManager

targets = {
    'groove music': 'Microsoft.ZuneMusic$',
    'spotify': '^Spotify.exe$',
    'firefox': '^firefox.exe$',
}

# play time in senconds to scrobble
play_time = 60

PLAYING_ID = 4


class PlayerNotFound(Exception):
    pass

class Song_info(dict):
    """Basically a dict with some equivalence checks"""
    def __eq__(self, other: 'Song_info'):
        if not isinstance(other, dict):
            # i mean I guess you should be able to compare it to a dict
            return False
        # if len(self.keys()) != len(other.keys()):
        #     return False

        for key in set([*self.keys(), *other.keys()]):
            # thumbnail changes each call so ignore it
            if key == 'thumbnail':
                continue
            if key == 'scrobbled':
                continue
            # otherwise just make sure it's the same
            if key not in self or key not in other:
                return False
            if self[key] != other[key]:
                return False

        return True

    def __ne__(self, other):
        return not self == other


async def get_media_info() -> Song_info:
    # from https://stackoverflow.com/questions/65011660/how-can-i-get-the-title-of-the-currently-playing-media-in-windows-10-with-python
    sessions = await MediaManager.request_async()

    # This source_app_user_model_id check and if statement is optional
    # Use it if you want to only get a certain player/program's media
    # (e.g. only chrome.exe's media not any other program's).

    # To get the ID, use a breakpoint() to run sessions.get_current_session()
    # while the media you want to get is playing.
    # Then set TARGET_ID to the string this call returns.

    current_session = sessions.get_current_session()
    # there needs to be a media session running
    if current_session and current_session.get_playback_info().playback_status == PLAYING_ID:
        info = await current_session.try_get_media_properties_async()

        # song_attr[0] != '_' ignores system attributes
        info_dict = {song_attr: info.__getattribute__(song_attr) for song_attr in dir(info) if song_attr[0] != '_'}

        # converts winrt vector to list
        info_dict['genres'] = list(info_dict['genres'])
        info_dict['player'] = current_session.source_app_user_model_id

        return Song_info(info_dict)

    print(current_session.get_playback_info().playback_status)
    print(current_session.source_app_user_model_id)

    # It could be possible to select a program from a list of current
    # available ones. I just haven't implemented this here for my use case.
    # See references for more information.
    raise PlayerNotFound('TARGET_PROGRAM is not the current media session')

def any_search(patterns, s) -> bool:
    return any(map(lambda x: re.search(x, s), patterns))


if __name__ == '__main__':
    current_media_info = None
    while True:
        try:
            # I don't know how expensive get_media_info is, so we'll play it conservative
            time.sleep(2)
            new_media_info = asyncio.run(get_media_info())
            if new_media_info is None:
                continue
            if not any_search(targets.values(), new_media_info['player']):
                continue

            if current_media_info != new_media_info:
                start_time = time.time()
                current_media_info = new_media_info
                current_media_info['scrobbled'] = False
                print('scrobbling', current_media_info['title'], 'by', current_media_info['artist'])
            else:
                # if we're still playing the same song
                if time.time() > start_time + play_time:
                    if not current_media_info['scrobbled']:
                        print('scobbled')
                        current_media_info['scrobbled'] = True

        except PlayerNotFound:
            pass
            # print('player not found (maybe not playing or other service playing simultaniously)')
            

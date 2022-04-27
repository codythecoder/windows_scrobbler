import asyncio
import time

from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as MediaManager

TARGET_ID = 'Microsoft.ZuneMusic'
# Spotify.exe

# play time in senconds to scrobble
play_time = 60 

PLAYING_ID = 4


class PlayerNotFound(Exception):
    pass

class Song_info(dict):
    """Basically a dict with some equivalence checks"""
    def __eq__(self, other: 'Song_info'):
        if len(self.keys()) != len(other.keys()):
            return False
        for key in self:
            if key == 'thumbnail':
                # thumbnail changes each time so ignore it
                continue
            if key not in other:
                # print('not equal', key)
                return False
            if self[key] != other[key]:
                # print('not equal', key)
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
        if current_session.source_app_user_model_id.startswith(TARGET_ID):
            info = await current_session.try_get_media_properties_async()

            # song_attr[0] != '_' ignores system attributes
            info_dict = {song_attr: info.__getattribute__(song_attr) for song_attr in dir(info) if song_attr[0] != '_'}

            # converts winrt vector to list
            info_dict['genres'] = list(info_dict['genres'])

            return Song_info(info_dict)

    print(current_session.get_playback_info().playback_status)
    print(current_session.source_app_user_model_id)

    # It could be possible to select a program from a list of current
    # available ones. I just haven't implemented this here for my use case.
    # See references for more information.
    raise PlayerNotFound('TARGET_PROGRAM is not the current media session')


if __name__ == '__main__':
    current_media_info = None
    while True:
        try:
            new_media_info = asyncio.run(get_media_info())

            start_time = time.time()
            current_media_info = new_media_info
            print('scrobbling', current_media_info['title'], 'by', current_media_info['artist'])
            # check that we're still playing the same song
            for i in range(play_time//2):
                # I don't know how expensive get_media_info is, so we'll play it conservative
                time.sleep(2)
                new_media_info = asyncio.run(get_media_info())
                if new_media_info != current_media_info:
                    print('scrobble cancelled')
                    # for key in new_media_info:
                    #     if new_media_info[key] != current_media_info[key]:
                    #         print(f'{repr(key)}:{repr(new_media_info[key])}')
                    #         print(f'{repr(key)}:{repr(current_media_info[key])}')
                    #         print()
                    break
            else:
                print('scobbled')
                # if we listened to it for the full time then wait until it's the next song
                while new_media_info == current_media_info:
                    time.sleep(2)
                    new_media_info = asyncio.run(get_media_info())
        except PlayerNotFound:
            print('player not found (maybe not playing or other service playing simultaniously)')
            time.sleep(2)
            

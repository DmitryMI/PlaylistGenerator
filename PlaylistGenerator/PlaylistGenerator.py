
__author__ = "Dmitriy Monakhov"
__version__ = "0.1.0"
__license__ = "MIT"

import argparse
from genericpath import isdir, isfile
import os
import os.path
import logging
import subprocess


LOG_FORMAT = "%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s"
MEDIA_EXTENSIONS = ["mp3", "flac", "webm", "mp4", "mkv", "ogg", "mod", "m4a"]

logger = logging.getLogger("main")

media_info_cache = {}

def get_media_duration(path):
    # ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 input.mp4
    if path in media_info_cache:
        return media_info_cache[path]

    result = subprocess.run(
        [
            'ffprobe', '-v', "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", path
        ],
        stdout=subprocess.PIPE
        )
    
    duration_str = result.stdout
    duration = float(duration_str)
    media_info_cache[path] = duration
    return duration

def generate_m3u8(path_dir, playlist_name, files):
    lines = ["#EXTM3U"]
    for file_abs in files:
        duration = int(get_media_duration(file_abs))
        title = os.path.basename(file_abs)
        lines.append(f"#EXTINF:{duration},{title}")

        file_relative = os.path.relpath(file_abs, path_dir)        

        lines.append(file_relative)
    
    text = "\n".join(lines)
    playlist_path = os.path.join(path_dir, playlist_name)
        
    with open(playlist_path, "w", encoding="utf-8") as fout:
        fout.write(text)
    
    logger.info(f"Playlist generated: {playlist_path}")

def generate_playlists(path_dir, recurse, multilevel_playlists_enabled):
    logger.debug(f"Entering directory: {path_dir}")    

    playlist_name_local = os.path.basename(path_dir) + ".m3u8"

    media_local = []
    playlists = [playlist_name_local]

    local_entries = os.listdir(path_dir)
    for entry in local_entries:
        entry_abs = os.path.join(path_dir, entry)
        if os.path.isfile(entry_abs):
            ext = os.path.splitext(entry_abs)[1][1:]
            if ext not in MEDIA_EXTENSIONS:  
                logger.debug(f"File ignored due to extension not in the list: {entry_abs}")
            else:
                logger.debug(f"Found media: {entry_abs}")
                media_local.append(entry_abs)
        elif os.path.isdir(entry_abs):
            if not recurse:
                logger.debug(f"Directory {entry_abs} ignored because recursion is disabled")
            else:
                logger.debug(f"Found directory: {entry_abs}")
                playlists_subdir, media_subdirs = generate_playlists(entry_abs, recurse, multilevel_playlists_enabled)
                if multilevel_playlists_enabled:
                    media_local += media_subdirs
                playlists += playlists_subdir
        else:
            logger.debug(f"Entry ignored: {entry_abs}")
      
            
    generate_m3u8(path_dir, playlist_name_local, media_local)
    
    return playlists, media_local

def main(args):
    target_paths = args.paths

    if not target_paths:
        path = input("Directory: ")
        target_paths = [path]
        pass

    for path in target_paths:
        if not os.path.exists(path):
            logger.critical(f"Directory {path} does not exist!")
            return
    
        if not os.path.isdir(path):
            logger.critical(f"{path} is not a directory!")
            return
    
        generate_playlists(path, not args.no_recurse, not args.no_multilevel_playlists)


if __name__ == "__main__":
    logging.basicConfig(format=LOG_FORMAT)    

    parser = argparse.ArgumentParser()

    parser.add_argument("paths", nargs="*", help="Top directory with media", type=str)
    parser.add_argument("-v", "--verbosity", type=str, default="INFO")
    parser.add_argument("--no-multilevel-playlists", action="store_true")
    parser.add_argument("--no-recurse", action="store_true")

    args = parser.parse_args()
    logger.setLevel(args.verbosity)
    main(args)
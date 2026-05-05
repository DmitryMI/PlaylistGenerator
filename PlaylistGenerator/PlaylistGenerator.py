
__author__ = "Dmitriy Monakhov"
__version__ = "0.2.0"
__license__ = "MIT"

import argparse
import os
import os.path
from pathlib import Path
import logging
import subprocess
from urllib.parse import quote

LOG_FORMAT = "%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s"
MEDIA_EXTENSIONS = ["mp3", "flac", "webm", "mp4", "mkv", "ogg", "mod", "m4a", "mpg"]

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
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:
        logger.error(f"Failed to get media duration for {path}: {result.stderr.strip()}")
        quit()

    duration_str = result.stdout.strip()
    try:
        duration = float(duration_str)
    except ValueError:
        logger.error(f"Failed to get media duration for {path}: {duration_str} is not convertible to float")
        quit()
        
    media_info_cache[path] = duration
    return duration

def encode_playlist_path(file_abs, playlist_dir, library_root_dir, absolute_path_prefix=None):
    file_abs_path = Path(file_abs)

    if absolute_path_prefix:
        file_relative = file_abs_path.relative_to(library_root_dir)
        base_path = absolute_path_prefix.rstrip("/")
        playlist_path = f"{base_path}/{file_relative.as_posix()}"
    else:
        file_relative = file_abs_path.relative_to(playlist_dir)
        playlist_path = file_relative.as_posix()

    return quote(playlist_path, safe="/:")

def generate_m3u8(path_dir, playlist_name, files, library_root_dir=None, absolute_path_prefix=None):
    if not files:
        logger.info(f"No media found in {path_dir}")
        return

    if library_root_dir is None:
        library_root_dir = path_dir
        
    lines = ["#EXTM3U"]
    for file_abs in files:
        
        duration = int(get_media_duration(file_abs))
        title = os.path.basename(file_abs)
        lines.append(f"#EXTINF:{duration},{title}")
        
        lines.append(
            encode_playlist_path(
                file_abs,
                playlist_dir=path_dir,
                library_root_dir=library_root_dir,
                absolute_path_prefix=absolute_path_prefix,
            )
        )
    
    text = "\n".join(lines)
    playlist_path = os.path.join(path_dir, playlist_name)
        
    with open(playlist_path, "w", encoding="utf-8", newline="\n") as fout:
        fout.write(text)
    
    logger.info(f"Playlist generated: {playlist_path}")

def is_media_file(entry_abs):
    ext = os.path.splitext(entry_abs)[1][1:].lower()
    if ext not in MEDIA_EXTENSIONS:
        logger.debug(f"File ignored due to extension not in the list: {entry_abs}")
        return False

    return True

def generate_playlists(path_dir, recurse, multilevel_playlists_enabled, library_root_dir=None, absolute_path_prefix=None):
    logger.debug(f"Entering directory: {path_dir}")    

    if library_root_dir is None:
        library_root_dir = path_dir

    playlist_name_local = os.path.basename(path_dir) + ".m3u8"

    media_local = []
    playlists = [playlist_name_local]

    local_entries = sorted(os.listdir(path_dir))
    for entry in local_entries:
        entry_abs = os.path.join(path_dir, entry)
        if os.path.isfile(entry_abs):
            if is_media_file(entry_abs):
                logger.debug(f"Found media: {entry_abs}")
                media_local.append(entry_abs)
        elif os.path.isdir(entry_abs):
            if not recurse:
                logger.debug(f"Directory {entry_abs} ignored because recursion is disabled")
            else:
                logger.debug(f"Found directory: {entry_abs}")
                playlists_subdir, media_subdirs = generate_playlists(
                    entry_abs,
                    recurse,
                    multilevel_playlists_enabled,
                    library_root_dir=library_root_dir,
                    absolute_path_prefix=absolute_path_prefix,
                )
                if multilevel_playlists_enabled:
                    media_local += media_subdirs
                playlists += playlists_subdir
        else:
            logger.debug(f"Entry ignored: {entry_abs}")
      
            
    generate_m3u8(
        path_dir,
        playlist_name_local,
        media_local,
        library_root_dir=library_root_dir,
        absolute_path_prefix=absolute_path_prefix,
    )
    
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
    
        generate_playlists(
            path,
            not args.no_recurse,
            args.multilevel_playlists,
            library_root_dir=path,
            absolute_path_prefix=args.absolute_path_prefix,
        )


if __name__ == "__main__":
    logging.basicConfig(format=LOG_FORMAT)    

    parser = argparse.ArgumentParser(
        description=(
            "Generate UTF-8 M3U playlists for local media folders. "
            "By default playlist entries stay relative for portability."
        )
    )

    parser.add_argument("paths", nargs="*", help="Top directory with media", type=str)
    parser.add_argument("-v", "--verbosity", type=str, default="INFO")
    parser.add_argument(
        "--multilevel-playlists",
        action="store_true",
        help=(
            "Also add media from subdirectories to parent playlists. "
            "This is the default behavior. Pair it with --absolute-path-prefix for Android VLC."
        ),
    )
    parser.add_argument(
        "--no-multilevel-playlists",
        dest="multilevel_playlists",
        action="store_false",
        help=argparse.SUPPRESS,
    )
    parser.set_defaults(multilevel_playlists=True)
    parser.add_argument("--no-recurse", action="store_true")
    parser.add_argument(
        "--absolute-path-prefix",
        type=str,
        help=(
            "Write playlist entries as absolute POSIX paths rooted at this prefix, "
            "for example /storage/emulated/0/Music for Android VLC."
        ),
    )

    args = parser.parse_args()
    logger.setLevel(args.verbosity)
    main(args)

import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "PlaylistGenerator" / "PlaylistGenerator.py"
MODULE_SPEC = importlib.util.spec_from_file_location("playlist_generator", MODULE_PATH)
playlist_generator = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(playlist_generator)


class PlaylistGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.original_get_media_duration = playlist_generator.get_media_duration
        playlist_generator.get_media_duration = lambda _: 123.4

    def tearDown(self):
        playlist_generator.get_media_duration = self.original_get_media_duration

    def test_encode_playlist_path_uses_android_friendly_relative_paths(self):
        root = Path("C:/Music")
        media = root / "Sub Dir" / "Track 01 [live].mp3"

        encoded = playlist_generator.encode_playlist_path(
            media,
            playlist_dir=root,
            library_root_dir=root,
        )

        self.assertEqual(encoded, "Sub%20Dir/Track%2001%20%5Blive%5D.mp3")

    def test_encode_playlist_path_supports_android_absolute_prefix(self):
        root = Path("C:/Music")
        media = root / "Sub Dir" / "Track 01 [live].mp3"

        encoded = playlist_generator.encode_playlist_path(
            media,
            playlist_dir=root,
            library_root_dir=root,
            absolute_path_prefix="/storage/emulated/0/Music",
        )

        self.assertEqual(
            encoded,
            "/storage/emulated/0/Music/Sub%20Dir/Track%2001%20%5Blive%5D.mp3",
        )

    def test_single_level_playlists_are_default(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            subdir = root / "Sub"
            subdir.mkdir()

            (root / "Root Song.mp3").write_text("", encoding="utf-8")
            (subdir / "Child Song.mp3").write_text("", encoding="utf-8")

            playlist_generator.generate_playlists(str(root), recurse=True, multilevel_playlists_enabled=False)

            root_playlist = (root / f"{root.name}.m3u8").read_text(encoding="utf-8")
            child_playlist = (subdir / "Sub.m3u8").read_text(encoding="utf-8")

            self.assertIn("Root%20Song.mp3", root_playlist)
            self.assertNotIn("Sub/Child%20Song.mp3", root_playlist)
            self.assertIn("Child%20Song.mp3", child_playlist)

    def test_multilevel_playlists_remain_available_by_flag(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            subdir = root / "Sub"
            subdir.mkdir()

            (root / "Root Song.mp3").write_text("", encoding="utf-8")
            (subdir / "Child Song.mp3").write_text("", encoding="utf-8")

            playlist_generator.generate_playlists(str(root), recurse=True, multilevel_playlists_enabled=True)

            root_playlist = (root / f"{root.name}.m3u8").read_text(encoding="utf-8")

            self.assertIn("Root%20Song.mp3", root_playlist)
            self.assertIn("Sub/Child%20Song.mp3", root_playlist)

    def test_multilevel_playlists_can_use_android_absolute_paths(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            subdir = root / "Sub"
            subdir.mkdir()

            (root / "Root Song.mp3").write_text("", encoding="utf-8")
            (subdir / "Child Song.mp3").write_text("", encoding="utf-8")

            playlist_generator.generate_playlists(
                str(root),
                recurse=True,
                multilevel_playlists_enabled=True,
                library_root_dir=str(root),
                absolute_path_prefix="/storage/emulated/0/Music",
            )

            root_playlist = (root / f"{root.name}.m3u8").read_text(encoding="utf-8")
            child_playlist = (subdir / "Sub.m3u8").read_text(encoding="utf-8")

            self.assertIn("/storage/emulated/0/Music/Root%20Song.mp3", root_playlist)
            self.assertIn("/storage/emulated/0/Music/Sub/Child%20Song.mp3", root_playlist)
            self.assertIn("/storage/emulated/0/Music/Sub/Child%20Song.mp3", child_playlist)


if __name__ == "__main__":
    unittest.main()

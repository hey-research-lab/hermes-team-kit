from pathlib import Path
import tempfile
import unittest
from kit_config import load

class ConfigTest(unittest.TestCase):
    def config(self, text):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / 'config.toml'
        path.write_text(text)
        return path

    def test_paths_resolve_against_config_not_working_directory(self):
        path = self.config('[paths]\ngate="var/gate"\n')
        self.assertEqual(load(path)['paths']['gate'], str(path.resolve().parent / 'var/gate'))

    def test_duplicate_profile_and_key_groups_are_rejected(self):
        for text in ('[seats.A]\nprofiles=["builder"]\n[seats.B]\nprofiles=["builder"]\n',
                     '[seats.A]\nprofiles=["builder"]\napi_key_env="KEY"\n[seats.B]\nprofiles=["tester"]\napi_key_env="KEY"\n'):
            with self.assertRaises(ValueError):
                load(self.config(text))

    def test_invalid_locale_and_profile_are_rejected(self):
        for text in ('[telegram]\nlocale="xx"\n', '[seats.A]\nprofiles=["missing"]\n'):
            with self.assertRaises(ValueError):
                load(self.config(text))

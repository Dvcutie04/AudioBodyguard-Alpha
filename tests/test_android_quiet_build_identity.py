import unittest

from tools.smoke_android_quiet_output import verify_installed_identity


CONFIG = '''
    versionCode = 46
    versionName = "0.43-simple-setup"
    versionNameSuffix = "-live-input"
'''


class QuietBuildIdentityTests(unittest.TestCase):
    def test_current_build_passes_and_previous_build_is_rejected(self):
        verify_installed_identity("0.43-simple-setup-live-input", "46", CONFIG)
        with self.assertRaisesRegex(AssertionError, "differs from source"):
            verify_installed_identity("0.41-voice-cleanup-live-input", "44", CONFIG)

    def test_source_version_bump_accepts_new_build_and_rejects_stale_install(self):
        bumped = CONFIG.replace('46', '47').replace('0.43-simple-setup', '0.44-next')
        verify_installed_identity("0.44-next-live-input", "47", bumped)
        for version, build in (("0.43-simple-setup-live-input", "46"),
                               ("0.44-next-live-input", "46"),
                               ("0.44-next", "47")):
            with self.subTest(version=version, build=build):
                with self.assertRaisesRegex(AssertionError, "differs from source"):
                    verify_installed_identity(version, build, bumped)

    def test_missing_ambiguous_or_computed_configuration_is_rejected(self):
        for config in ("", CONFIG + 'versionCode = 47\n',
                       CONFIG.replace('versionCode = 46', 'versionCode = nextBuild'),
                       CONFIG.replace('versionNameSuffix = "-live-input"', '')):
            with self.subTest(config=config):
                with self.assertRaisesRegex(AssertionError, "unambiguous"):
                    verify_installed_identity("0.43-simple-setup-live-input", "46", config)

import plistlib
import zipfile

import pytest

from tools.testflight_package import inspect_package


TEAM = 'ABCDEFGHIJ'
BUNDLE = 'com.aqss.bodyguard.prototype'


def package_fixture(tmp_path, *, platform='iphoneos', changes=None):
    info = {
        'CFBundleIdentifier': BUNDLE,
        'CFBundleShortVersionString': '0.1.0',
        'CFBundleVersion': '1.1',
        'CFBundleSupportedPlatforms': ['iPhoneOS' if platform == 'iphoneos' else 'iPhoneSimulator'],
        'DTPlatformName': platform,
    }
    info.update(changes or {})
    privacy = {
        'NSPrivacyAccessedAPITypes': [
            {'NSPrivacyAccessedAPIType': 'NSPrivacyAccessedAPICategoryUserDefaults', 'NSPrivacyAccessedAPITypeReasons': ['CA92.1']},
            {'NSPrivacyAccessedAPIType': 'NSPrivacyAccessedAPICategorySystemBootTime', 'NSPrivacyAccessedAPITypeReasons': ['35F9.1']},
        ],
    }
    path = tmp_path/'beta.ipa'
    with zipfile.ZipFile(path, 'w') as z:
        for name, content in {
            'Info.plist': plistlib.dumps(info),
            'PrivacyInfo.xcprivacy': plistlib.dumps(privacy),
            '_CodeSignature/CodeResources': b'synthetic, not a signature',
            'embedded.mobileprovision': b'synthetic, not signed CMS',
        }.items():
            z.writestr('Payload/AQSSReadOnly.app/'+name, content)
    return path


def profile_fixture():
    return {'TeamIdentifier': [TEAM], 'Entitlements': {
        'application-identifier': TEAM+'.'+BUNDLE,
        'com.apple.developer.team-identifier': TEAM,
        'get-task-allow': False,
    }}


def inspect(path, profile=None):
    return inspect_package(path, bundle_id=BUNDLE, version='0.1.0', build_number='1.1',
                           team_id=TEAM, provisioning_profile=profile or profile_fixture())


def test_simulator_package_is_rejected_before_upload(tmp_path):
    with pytest.raises(ValueError, match='physical iOS'):
        inspect(package_fixture(tmp_path, platform='iphonesimulator'))


def test_metadata_report_never_claims_signing_delivery_or_physical_qualification(tmp_path):
    report = inspect(package_fixture(tmp_path))
    assert report['evidence_scope'] == 'PACKAGE_METADATA_ONLY'
    assert report['delivery_status'] == 'NOT_UPLOADED'
    assert report['physical_protection_qualified'] is False
    assert len(report['submitted_ipa_sha256']) == 64


@pytest.mark.parametrize('changes', [
    {'CFBundleIdentifier': 'com.other.app'},
    {'CFBundleShortVersionString': '9.9'},
    {'CFBundleVersion': '0'},
    {'AQSSPreviewMode': 'CONNECTED_UI_DEMO'},
    {'CFBundleSupportedPlatforms': ['iPhoneOS', 'iPhoneSimulator']},
])
def test_identity_and_demo_mismatches_are_rejected(tmp_path, changes):
    with pytest.raises(ValueError):
        inspect(package_fixture(tmp_path, changes=changes))


@pytest.mark.parametrize('changes', [
    {'ProvisionedDevices': ['synthetic-device']},
    {'TeamIdentifier': ['DIFFERTEAM']},
    {'ProvisionsAllDevices': True},
])
def test_development_adhoc_enterprise_or_wrong_team_profile_is_rejected(tmp_path, changes):
    profile = profile_fixture(); profile.update(changes)
    with pytest.raises(ValueError):
        inspect(package_fixture(tmp_path), profile)


@pytest.mark.parametrize('missing', ['PrivacyInfo.xcprivacy', 'embedded.mobileprovision'])
def test_required_package_contents_cannot_be_assumed(tmp_path, missing):
    path = package_fixture(tmp_path)
    with zipfile.ZipFile(path) as z:
        contents = {name: z.read(name) for name in z.namelist() if not name.endswith('/'+missing)}
    with zipfile.ZipFile(path, 'w') as z:
        for name, data in contents.items(): z.writestr(name, data)
    with pytest.raises(ValueError):
        inspect(path)

import plistlib
import zipfile
import json
import hashlib
from pathlib import Path
import subprocess
import sys

import pytest

from tools.testflight_package import ORIENTATIONS, inspect_package, make_export_options


TEAM = 'ABCDEFGHIJ'
BUNDLE = 'com.aqss.bodyguard.prototype'


def package_fixture(tmp_path, *, platform='iphoneos', changes=None):
    info = {
        'CFBundleIdentifier': BUNDLE,
        'CFBundleShortVersionString': '0.1.0',
        'CFBundleVersion': '1.1',
        'CFBundleSupportedPlatforms': ['iPhoneOS' if platform == 'iphoneos' else 'iPhoneSimulator'],
        'DTPlatformName': platform,
        'UIDeviceFamily': [1, 2],
        'UISupportedInterfaceOrientations': sorted(ORIENTATIONS),
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


@pytest.mark.parametrize('changes', [
    {'UISupportedInterfaceOrientations': []},
    {'UISupportedInterfaceOrientations': 'UIInterfaceOrientationPortrait'},
    {'UISupportedInterfaceOrientations': ['UIInterfaceOrientationPortrait']},
    {'UISupportedInterfaceOrientations~ipad': []},
    {'UISupportedInterfaceOrientations~ipad': ['UIInterfaceOrientationPortrait']},
    {'UIDeviceFamily': []},
])
def test_missing_or_incomplete_orientations_are_rejected_before_apple(tmp_path, changes):
    with pytest.raises(ValueError):
        inspect(package_fixture(tmp_path, changes=changes))


def test_ipad_orientation_override_is_respected(tmp_path):
    inspect(package_fixture(tmp_path, changes={
        'UISupportedInterfaceOrientations': ['UIInterfaceOrientationPortrait'],
        'UISupportedInterfaceOrientations~ipad': sorted(ORIENTATIONS),
    }))


def test_metadata_report_never_claims_signing_delivery_or_physical_qualification(tmp_path):
    report = inspect(package_fixture(tmp_path))
    assert report['evidence_scope'] == 'PACKAGE_METADATA_ONLY'
    assert report['delivery_status'] == 'NOT_UPLOADED'
    assert report['physical_protection_qualified'] is False
    assert len(report['submitted_ipa_sha256']) == 64
    assert report['internal_only_export_configured'] is None
    assert report['external_review_status'] == 'NOT_SUBMITTED_BY_THIS_WORKFLOW'


def test_internal_eligibility_remains_the_default():
    assert make_export_options(TEAM)['testFlightInternalTestingOnly'] is True


@pytest.mark.parametrize('audience,internal_only', [('internal', True), ('external', False)])
def test_requested_eligibility_is_bound_to_actual_export_options(tmp_path, audience, internal_only):
    options = make_export_options(TEAM, audience)
    assert options['testFlightInternalTestingOnly'] is internal_only
    report = inspect_package(package_fixture(tmp_path), bundle_id=BUNDLE, version='0.1.0',
                             build_number='1.1', team_id=TEAM, provisioning_profile=profile_fixture(),
                             testing_audience=audience, export_options=options)
    assert report['testflight_audience_requested'] == audience
    assert report['internal_only_export_configured'] is internal_only
    assert report['delivery_status'] == 'NOT_UPLOADED'
    assert report['external_review_status'] == 'NOT_SUBMITTED_BY_THIS_WORKFLOW'
    assert report['tester_assignment_status'] == 'NOT_CHECKED'
    assert report['physical_protection_qualified'] is False


@pytest.mark.parametrize('audience', ['friends', 'INTERNAL', '', None])
def test_ambiguous_eligibility_is_rejected(audience):
    with pytest.raises(ValueError):
        make_export_options(TEAM, audience)


@pytest.mark.parametrize('changed', [
    {'testFlightInternalTestingOnly': True}, {'testFlightInternalTestingOnly': 0},
    {'teamID': 'DIFFERTEAM'}, {'destination': 'upload'}, {'manageAppVersionAndBuildNumber': True},
])
def test_export_mismatch_is_rejected_before_apple(tmp_path, changed):
    options = make_export_options(TEAM, 'external'); options.update(changed)
    with pytest.raises(ValueError, match='Export options'):
        inspect_package(package_fixture(tmp_path), bundle_id=BUNDLE, version='0.1.0', build_number='1.1',
                        team_id=TEAM, provisioning_profile=profile_fixture(), testing_audience='external',
                        export_options=options)


@pytest.mark.parametrize('configured,accepted', [('external', True), ('internal', False)])
def test_cli_binds_external_request_to_the_actual_export_plist(tmp_path, configured, accepted):
    package = package_fixture(tmp_path)
    profile = tmp_path/'profile.plist'; profile.write_bytes(plistlib.dumps(profile_fixture()))
    options = tmp_path/'export.plist'; options.write_bytes(plistlib.dumps(make_export_options(TEAM, configured)))
    output = tmp_path/'provenance.json'
    call = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1]/'tools/testflight_package.py'),
        '--ipa', str(package), '--profile', str(profile), '--export-options', str(options),
        '--testing-audience', 'external', '--bundle-id', BUNDLE, '--version', '0.1.0', '--build-number', '1.1',
        '--team-id', TEAM, '--revision', 'a'*40, '--tree-sha', 'b'*40, '--workflow-run-id', '123',
        '--workflow-attempt', '1', '--output', str(output)], capture_output=True, text=True)
    assert (call.returncode == 0) is accepted
    assert output.exists() is accepted
    if accepted:
        report = json.loads(output.read_text())
        assert report['export_options_sha256'] == hashlib.sha256(options.read_bytes()).hexdigest()
        assert report['internal_only_export_configured'] is False
        assert report['source_revision'] == 'a'*40
        assert report['delivery_status'] == 'NOT_UPLOADED'
        assert report['external_review_status'] == 'NOT_SUBMITTED_BY_THIS_WORKFLOW'


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

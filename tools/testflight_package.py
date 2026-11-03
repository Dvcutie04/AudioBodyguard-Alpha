"""Inspect exported package metadata; this cannot certify signing or delivery."""
import argparse
import hashlib
import json
import plistlib
import re
from pathlib import Path
import zipfile


ORIENTATIONS = {
    'UIInterfaceOrientationPortrait', 'UIInterfaceOrientationPortraitUpsideDown',
    'UIInterfaceOrientationLandscapeLeft', 'UIInterfaceOrientationLandscapeRight',
}


def make_export_options(team_id, testing_audience='internal'):
    if not isinstance(team_id, str) or not re.fullmatch(r'[A-Z0-9]{10}', team_id):
        raise ValueError('Invalid Apple team identifier')
    if testing_audience not in ('internal', 'external'):
        raise ValueError('Select internal or external TestFlight eligibility')
    return {'method': 'app-store-connect', 'destination': 'export',
            'signingStyle': 'automatic', 'teamID': team_id,
            'manageAppVersionAndBuildNumber': False,
            'testFlightInternalTestingOnly': testing_audience == 'internal'}


def validate_orientations(info):
    families = info.get('UIDeviceFamily')
    if not isinstance(families, list) or not families or not set(families) <= {1, 2}:
        raise ValueError('Expected iPhone/iPad device families')
    for family in families:
        suffix = '~ipad' if family == 2 else '~iphone'
        orientations = info.get('UISupportedInterfaceOrientations'+suffix,
                                info.get('UISupportedInterfaceOrientations'))
        if (not isinstance(orientations, list) or not orientations
                or not set(orientations) <= ORIENTATIONS):
            raise ValueError('Supported interface orientations are missing or invalid')
        if family == 2 and set(orientations) != ORIENTATIONS:
            raise ValueError('iPad multitasking requires all four interface orientations')


def inspect_package(path, *, bundle_id, version, build_number, team_id, provisioning_profile,
                    testing_audience='internal', export_options=None):
    if not re.fullmatch(r'[A-Z0-9]{10}', team_id):
        raise ValueError('Invalid Apple team identifier')
    if bundle_id.endswith('.demo'):
        raise ValueError('A demonstration bundle cannot be a beta package')
    expected_export = make_export_options(team_id, testing_audience)
    if export_options is not None:
        if not isinstance(export_options, dict) or any(
            type(export_options.get(key)) is not type(value) or export_options.get(key) != value
            for key, value in expected_export.items()
        ):
            raise ValueError('Export options do not match the selected TestFlight eligibility')
    with zipfile.ZipFile(path) as package:
        names = package.namelist()
        apps = [name for name in names if re.fullmatch(r'Payload/[^/]+\.app/Info\.plist', name)]
        if len(apps) != 1:
            raise ValueError('Expected one main iOS application')
        root = apps[0].removesuffix('Info.plist')
        info = plistlib.loads(package.read(apps[0]))
        if info.get('DTPlatformName') != 'iphoneos' or info.get('CFBundleSupportedPlatforms') != ['iPhoneOS']:
            raise ValueError('A physical iOS package is required; Simulator apps cannot be uploaded')
        if 'AQSSPreviewMode' in info:
            raise ValueError('A demonstration package cannot be uploaded')
        validate_orientations(info)
        for key, expected in [('CFBundleIdentifier', bundle_id), ('CFBundleShortVersionString', version), ('CFBundleVersion', build_number)]:
            if info.get(key) != expected:
                raise ValueError(f'Package {key} does not match the release identity')
        for required in ['PrivacyInfo.xcprivacy', 'embedded.mobileprovision', '_CodeSignature/CodeResources']:
            if names.count(root+required) != 1:
                raise ValueError(f'Package lacks a unique {required}')
        privacy_bytes = package.read(root+'PrivacyInfo.xcprivacy')
        privacy = plistlib.loads(privacy_bytes)
        reasons = {entry['NSPrivacyAccessedAPIType']: entry['NSPrivacyAccessedAPITypeReasons']
                   for entry in privacy.get('NSPrivacyAccessedAPITypes', [])}
        for category, reason in [('UserDefaults', 'CA92.1'), ('SystemBootTime', '35F9.1')]:
            declared = reasons.get('NSPrivacyAccessedAPICategory'+category, [])
            if not isinstance(declared, list) or reason not in declared:
                raise ValueError('Required privacy reasons are missing from the exported package')
    profile = provisioning_profile
    entitlements = profile.get('Entitlements', {})
    if profile.get('TeamIdentifier') != [team_id] or entitlements.get('com.apple.developer.team-identifier') != team_id:
        raise ValueError('Provisioning team does not match the release identity')
    if entitlements.get('application-identifier') != team_id+'.'+bundle_id:
        raise ValueError('Provisioning application does not match the release identity')
    if entitlements.get('get-task-allow') is not False or 'ProvisionedDevices' in profile or profile.get('ProvisionsAllDevices') is True:
        raise ValueError('An App Store distribution profile is required')
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            digest.update(chunk)
    return {
        'evidence_scope': 'PACKAGE_METADATA_ONLY',
        'delivery_status': 'NOT_UPLOADED',
        'physical_protection_qualified': False,
        'bundle_id': bundle_id, 'app_version': version, 'build_number': build_number,
        'submitted_ipa_sha256': digest.hexdigest(),
        'privacy_manifest_sha256': hashlib.sha256(privacy_bytes).hexdigest(),
        'testflight_audience_requested': testing_audience,
        'internal_only_export_configured': None if export_options is None else export_options['testFlightInternalTestingOnly'],
        'external_review_status': 'NOT_SUBMITTED_BY_THIS_WORKFLOW',
        'tester_assignment_status': 'NOT_CHECKED',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['ipa', 'profile', 'export-options', 'bundle-id', 'version', 'build-number', 'team-id', 'revision', 'tree-sha', 'workflow-run-id', 'workflow-attempt', 'output']:
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--testing-audience', choices=['internal', 'external'], default='internal')
    args = parser.parse_args()
    if not re.fullmatch(r'[0-9a-f]{40}', args.revision) or not re.fullmatch(r'[0-9a-f]{40}', args.tree_sha):
        raise SystemExit('An exact source commit and tree SHA are required')
    export_bytes = Path(args.export_options).read_bytes()
    report = inspect_package(args.ipa, bundle_id=args.bundle_id, version=args.version,
                             build_number=args.build_number, team_id=args.team_id,
                             provisioning_profile=plistlib.loads(Path(args.profile).read_bytes()),
                             testing_audience=args.testing_audience,
                             export_options=plistlib.loads(export_bytes))
    report.update(source_revision=args.revision, source_tree_sha=args.tree_sha,
                  workflow_run_id=args.workflow_run_id, workflow_attempt=args.workflow_attempt,
                  export_options_sha256=hashlib.sha256(export_bytes).hexdigest())
    Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()

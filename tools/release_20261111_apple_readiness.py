"""Read-only App Store Connect build-state observation; never distributes a build."""
from __future__ import annotations
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

class ObservationError(RuntimeError):
    pass

def require(value, reason):
    if not value:
        raise ObservationError(reason)

def b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode('ascii')

def raw_es256(der):
    # OpenSSL emits DER ECDSA; JWT requires exactly 32-byte r || 32-byte s.
    require(isinstance(der, bytes) and 8 <= len(der) <= 72, 'Invalid ECDSA signature length')
    require(der[0] == 0x30 and der[1] == len(der)-2, 'Invalid ECDSA sequence')
    offset, result = 2, bytearray()
    for _ in range(2):
        require(offset+2 <= len(der) and der[offset] == 2, 'Invalid ECDSA integer')
        length = der[offset+1]; offset += 2
        require(1 <= length <= 33 and offset+length <= len(der), 'Invalid ECDSA integer length')
        value = der[offset:offset+length]; offset += length
        require(value[0] < 128, 'Negative ECDSA integer')
        if len(value) > 1 and value[0] == 0:
            require(value[1] >= 128, 'Noncanonical ECDSA integer')
            value = value[1:]
        require(len(value) <= 32 and int.from_bytes(value, 'big') > 0, 'Invalid ECDSA value')
        result.extend(value.rjust(32, b'\0'))
    require(offset == len(der), 'Trailing ECDSA signature bytes')
    return bytes(result)

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ObservationError('Apple API redirected; credentials were not forwarded')

class AppleReadOnly:
    ALLOWED = {'/v1/apps', '/v1/builds', '/v1/betaGroups'}
    def __init__(self, key_path, key_id, issuer):
        require(re.fullmatch(r'[A-Z0-9]{10}', key_id) is not None, 'Invalid configured key ID')
        require(re.fullmatch(r'[0-9a-fA-F-]{36}', issuer) is not None, 'Invalid configured issuer')
        self.key_path, self.key_id, self.issuer = key_path, key_id, issuer
        self.opener = urllib.request.build_opener(NoRedirect)

    def __call__(self, path, params):
        require(path in self.ALLOWED, 'Endpoint is outside the read-only build observation')
        now = int(time.time())
        # A short-lived token authorizes this GET endpoint only, not writes.
        header = {'alg': 'ES256', 'kid': self.key_id, 'typ': 'JWT'}
        payload = {'iss': self.issuer, 'iat': now, 'exp': now+300,
                   'aud': 'appstoreconnect-v1', 'scope': ['GET '+path]}
        encoded = '.'.join(b64url(json.dumps(item, separators=(',', ':')).encode())
                           for item in (header, payload)).encode('ascii')
        try:
            signature = subprocess.run(['openssl', 'dgst', '-sha256', '-sign', str(self.key_path)],
                                       input=encoded, capture_output=True, timeout=10, check=True).stdout
        except (OSError, subprocess.SubprocessError):
            raise ObservationError('Could not sign the read-only Apple request') from None
        token = encoded.decode() + '.' + b64url(raw_es256(signature))
        request = urllib.request.Request('https://api.appstoreconnect.apple.com'+path+'?'+urllib.parse.urlencode(params),
            method='GET', headers={'Authorization': 'Bearer '+token, 'Accept': 'application/json',
                                   'User-Agent': 'AQSS-internal-beta-readiness-observation'})
        try:
            with self.opener.open(request, timeout=30) as response:
                require(response.status == 200, 'Unexpected Apple response status')
                raw = response.read(2_000_001)
        except urllib.error.HTTPError as error:
            raise ObservationError('Apple read-only API returned HTTP '+str(error.code)) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise ObservationError('Apple read-only API request failed') from None
        require(len(raw) <= 2_000_000, 'Apple response exceeds bound')
        return json.loads(raw)

def timestamp(text):
    require(isinstance(text, str), 'Missing build timestamp')
    try:
        value = datetime.fromisoformat(text.replace('Z', '+00:00'))
    except ValueError:
        raise ObservationError('Invalid build timestamp') from None
    require(value.tzinfo is not None, 'Build timestamp is not timezone-aware')
    return value.astimezone(timezone.utc)

def single_page(response):
    require(not response.get('links', {}).get('next'), 'Result is paginated; do not infer complete access')
    data = response.get('data')
    require(isinstance(data, list), 'Invalid Apple resource list')
    return data

def observe(api, *, bundle, build, marketing, not_before):
    require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]{2,200}', bundle) is not None, 'Invalid configured bundle')
    require(re.fullmatch(r'[0-9]+\.[0-9]+', build) is not None, 'Require the exact signed-run build number')
    require(re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', marketing) is not None, 'Invalid marketing version')
    earliest = timestamp(not_before)
    apps = single_page(api('/v1/apps', {'filter[bundleId]': bundle, 'fields[apps]': 'bundleId', 'limit': '2'}))
    require(len(apps) == 1 and apps[0].get('type') == 'apps'
            and apps[0].get('attributes', {}).get('bundleId') == bundle, 'Exact app was not resolved')
    app_id = apps[0]['id']
    response = api('/v1/builds', {'filter[app]': app_id, 'filter[version]': build,
        'filter[preReleaseVersion.version]': marketing, 'include': 'preReleaseVersion,buildBetaDetail', 'limit': '2'})
    builds = single_page(response)
    if not builds:
        return {'state': 'NEW_BUILD_NOT_VISIBLE_YET', 'version': marketing, 'build': build,
                'owner_installation_verified': False}
    require(len(builds) == 1 and builds[0].get('type') == 'builds', 'Exact build is ambiguous')
    item = builds[0]; attributes = item.get('attributes', {})
    require(attributes.get('version') == build, 'Apple returned a different build')
    require(timestamp(attributes.get('uploadedDate')) >= earliest, 'Build predates this release')
    relationships = item.get('relationships', {})
    included = response.get('included', [])
    require(isinstance(included, list), 'Invalid included resources')
    def related(name, kind):
        link = relationships.get(name, {}).get('data', {})
        require(isinstance(link, dict) and link.get('type') == kind and link.get('id'), 'Missing related '+name)
        matches = [v for v in included if v.get('id') == link['id'] and v.get('type') == kind]
        require(len(matches) == 1, 'Missing or ambiguous included '+name)
        return matches[0].get('attributes', {})
    version = related('preReleaseVersion', 'preReleaseVersions')
    require(version.get('version') == marketing and version.get('platform') == 'IOS', 'Version/platform mismatch')
    processing = attributes.get('processingState')
    require(processing in {'PROCESSING', 'FAILED', 'INVALID', 'VALID'}, 'Unknown processing state')
    receipt = {'state': 'APPLE_PROCESSING_NOT_READY', 'version': marketing, 'build': build,
               'processing_state': processing, 'owner_installation_verified': False}
    if processing in {'FAILED', 'INVALID'}:
        receipt['state'] = 'APPLE_PROCESSING_REJECTED'; return receipt
    if processing != 'VALID':
        return receipt
    require(type(attributes.get('expired')) is bool, 'Missing expired status')
    if attributes['expired']:
        receipt['state'] = 'BUILD_EXPIRED'; return receipt
    detail = related('buildBetaDetail', 'buildBetaDetails')
    state = detail.get('internalBuildState')
    require(isinstance(state, str), 'Missing internal beta state')
    receipt['internal_build_state'] = state
    if state != 'IN_BETA_TESTING':
        receipt['state'] = 'INTERNAL_TESTING_NOT_ACTIVE'; return receipt
    groups = single_page(api('/v1/betaGroups', {'filter[app]': app_id, 'filter[builds]': item['id'],
        'filter[isInternalGroup]': 'true', 'fields[betaGroups]': 'isInternalGroup', 'limit': '200'}))
    require(all(g.get('type') == 'betaGroups' and g.get('attributes', {}).get('isInternalGroup') is True for g in groups),
            'Unexpected tester-group response')
    receipt['internal_group_count'] = len(groups)
    receipt['state'] = 'INTERNAL_GROUP_ACCESS_OBSERVED' if groups else 'NO_INTERNAL_GROUP_ACCESS_OBSERVED'
    return receipt

def await_observation(api, *, bundle, build, marketing, not_before,
                      clock=time.monotonic, sleep=time.sleep, max_seconds=1200, interval=30):
    deadline = clock()+max_seconds
    transitional = {'NEW_BUILD_NOT_VISIBLE_YET', 'APPLE_PROCESSING_NOT_READY', 'INTERNAL_TESTING_NOT_ACTIVE'}
    previous = None
    while True:
        receipt = observe(api, bundle=bundle, build=build, marketing=marketing, not_before=not_before)
        state = receipt['state']
        if state != previous:
            print('APPLE_BUILD_STATE: '+state)
            previous = state
        if state not in transitional or clock() >= deadline:
            return receipt
        sleep(min(interval, max(0, deadline-clock())))


def main():
    try:
        bundle = os.environ.get('IOS_BUNDLE_ID', '')
        require(bundle == os.environ.get('EXPECTED_BUNDLE_ID') and bool(bundle), 'Configured app differs from the uploaded package')
        digest = os.environ.get('EXPECTED_IPA_SHA256', '')
        require(re.fullmatch(r'[0-9a-f]{64}', digest) is not None, 'Missing verified package digest')
        encoded = os.environ.get('ASC_PRIVATE_KEY_P8_BASE64', '')
        require(0 < len(encoded) <= 16384, 'Missing or oversized configured key')
        key = base64.b64decode(encoded, validate=True)
        require(key.startswith(b'-----BEGIN PRIVATE KEY-----') and b'-----END PRIVATE KEY-----' in key, 'Configured key is not PKCS8 PEM')
        with tempfile.TemporaryDirectory(prefix='aqss-readonly-apple-') as temporary:
            path = Path(temporary) / 'key.p8'; path.write_bytes(key); path.chmod(0o600)
            api = AppleReadOnly(path, os.environ.get('ASC_KEY_ID', ''), os.environ.get('ASC_ISSUER_ID', ''))
            receipt = await_observation(api, bundle=bundle, build='17.1', marketing='1.0.0',
                                        not_before='2026-11-12T02:09:54Z')
        receipt.update(release_run_id=43139474513,
                       source_revision='2a51c435491a0524f85f530a69e54c6869c2e014',
                       source_tree_sha='bdae3290b5e39555c2976293b4f8a333c2b85708',
                       submitted_ipa_sha256=digest,
                       observed_at=datetime.now(timezone.utc).isoformat())
        output = json.dumps(receipt, indent=2)
        print(output)
        Path(os.environ['READINESS_RECEIPT']).write_text(output+'\n', encoding='utf-8')
        summary = os.environ.get('GITHUB_STEP_SUMMARY')
        if summary:
            with Path(summary).open('a') as file:
                file.write('## Read-only Apple beta observation\n\n```json\n'+output+'\n```\n')
                file.write('No tester, group, compliance or distribution setting was changed. Owner installation is not established by a group count.\n')
        return 0 if receipt['state'] == 'INTERNAL_GROUP_ACCESS_OBSERVED' else 1
    except (ObservationError, KeyError, TypeError, ValueError, OSError):
        # Do not echo environment values, JWTs, key bytes or response bodies.
        print('APPLE_READINESS_OBSERVATION_FAILED: no availability claim is established')
        return 1

if __name__ == '__main__':
    raise SystemExit(main())

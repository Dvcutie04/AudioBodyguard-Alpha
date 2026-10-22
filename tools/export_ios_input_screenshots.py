#!/usr/bin/env python3
"""Export native XCTest PNG attachments for explicitly named result suites."""
import json, pathlib, subprocess, sys
temporary = pathlib.Path(sys.argv[1])
out = temporary / 'sound-check-screenshots'
out.mkdir(exist_ok=True)
for mode in sys.argv[2:]:
    result = temporary / ('sound-' + mode + '.xcresult')
    if not result.exists():
        continue
    seen, exported = set(), set()
    def get(identifier=None):
        args = ['xcrun', 'xcresulttool', 'get', '--path', str(result), '--format', 'json']
        if identifier:
            args += ['--id', identifier]
        call = subprocess.run(args, capture_output=True, text=True)
        if call.returncode:
            call = subprocess.run(args + ['--legacy'], capture_output=True, text=True)
        if call.returncode:
            raise RuntimeError(call.stderr)
        return json.loads(call.stdout)
    def walk(value):
        if isinstance(value, list):
            for child in value:
                walk(child)
        elif isinstance(value, dict):
            if 'payloadRef' in value and value.get('uniformTypeIdentifier', {}).get('_value') == 'public.png':
                identifier = value['payloadRef']['id']['_value']
                if identifier not in exported:
                    exported.add(identifier)
                    name = value.get('name', {}).get('_value', 'Screenshot')
                    safe = ''.join(c if c.isalnum() or c in '-_' else '-' for c in name)[:100]
                    path = out / (mode + '-' + str(len(exported)).zfill(3) + '-' + safe + '.png')
                    subprocess.run(['xcrun', 'xcresulttool', 'export', '--type', 'file', '--path', str(result), '--id', identifier, '--output-path', str(path)], check=True)
            for key, child in value.items():
                if key in ('testsRef', 'summaryRef') and isinstance(child, dict):
                    identifier = child.get('id', {}).get('_value')
                    if identifier and identifier not in seen:
                        seen.add(identifier)
                        walk(get(identifier))
                else:
                    walk(child)
    walk(get())
    print(mode, 'exported', len(exported), 'screenshots')

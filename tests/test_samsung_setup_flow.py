"""Samsung pairing choices belong at the request, after the shared phone steps."""
import json
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def catalog():
    data = json.loads((ROOT / 'contracts/setup_guides_v1.json').read_text())
    return data, {r['id']: r for r in data['routes']}


def test_samsung_starts_one_guide_without_predicting_tv_approval():
    data, routes = catalog()
    samsung = next(g for g in data['groups'] if g['id'] == 'samsung')
    assert samsung['primary_routes'] == ['samsung_ok']
    assert routes['samsung_ok']['title'] == 'Samsung — connect with SmartThings'
    assert routes['samsung_ok']['steps'][:14] == routes['samsung_pin']['steps'][:14]
    assert routes['samsung_ok']['steps'][14]['surface'] == 'tv'
    assert routes['samsung_pin']['steps'][14]['surface'] == 'tv'
    assert 'PIN' in routes['samsung_ok']['steps'][14]['instruction']


def test_samsung_phone_part_checks_existing_pairing_instead_of_repeating_it():
    data, routes = catalog()
    assert 'samsung_phone' in routes
    phone = routes['samsung_phone']
    assert len(phone['steps']) == 5
    assert all(s['surface'] == 'phone' for s in phone['steps'])
    assert 'SmartThings' in phone['steps'][0]['instruction']
    assert all(s['action'] != 'type' for s in phone['steps'])
    assert not any('Add device' in s['items'] for s in phone['steps'])
    assert 'samsung_phone' in next(g for g in data['groups'] if g['id'] == 'samsung')['routes']
    tutorial = json.loads((ROOT / 'contracts/tutorial_v1.json').read_text())
    assert 'samsung_phone' in tutorial['onboarding']['picture_continue_routes']


def test_samsung_tv_approval_pictures_are_tv_screens_and_keep_pin_private():
    from tools.export_picture_guide import svg
    _, routes = catalog()
    for name in ('samsung_ok', 'samsung_pin'):
        route = routes[name]
        image = ET.fromstring(svg(route['steps'][14], 15, route))
        labels = [t.text or '' for t in image.findall('.//text')]
        assert any('On your TV:' in text for text in labels)
    assert routes['samsung_pin']['steps'][14]['items'] == ['Your TV PIN']
    assert 'no code length' in routes['samsung_pin']['steps'][14]['note']
    assert routes['samsung_pin']['steps'][15]['surface'] == 'phone'

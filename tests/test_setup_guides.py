"""Illustrated setup is guidance, never a record of device authorization."""
import importlib
import json
from pathlib import Path


def test_default_setup_choices_are_bounded_and_extra_routes_are_preserved():
    root = Path(__file__).resolve().parents[1]
    data = json.loads((root / 'contracts/setup_guides_v1.json').read_text())
    groups = {group['id']: group for group in data['groups']}
    for group in groups.values():
        primary = group['primary_routes']
        assert 1 <= len(primary) <= 3
        assert len(primary) == len(set(primary))
        assert set(primary) <= set(group['routes'])
    assert groups['tcl_roku']['primary_routes'] == ['roku_network']
    assert {'roku_model', 'roku_alexa', 'google_roku', 'roku_phone'} <= set(groups['tcl_roku']['routes'])


def test_every_existing_tv_and_assistant_choice_has_an_illustrated_route():
    generator = importlib.import_module('tools.generate_setup_guides')
    root = Path(__file__).resolve().parents[1]
    data = generator.validate(json.loads((root / 'contracts/setup_guides_v1.json').read_text()))
    choices = json.loads((root / 'contracts/tutorial_v1.json').read_text())['choices']
    groups = {group['id']: group for group in data['groups']}
    for choice in choices['chooseTV'] + choices['chooseHome']:
        assert groups[choice['id']]['routes']
    assert groups['voice']['routes']
    routes = {route['id']: route for route in data['routes']}
    for group in groups.values():
        for route_id in group['routes']:
            assert route_id in routes
    for route in routes.values():
        assert route['applies_to'] and route['sources']
        assert len(route['steps']) >= 4
        for step in route['steps']:
            assert step['instruction'] and step['screen'] and step['action']
            assert 0 <= step['focus'] < len(step['items'])
    for path, content in generator.sources(data).items():
        assert path.read_text() == content


def test_generator_rejects_missing_unknown_duplicate_or_unbounded_primary_choices():
    generator = importlib.import_module('tools.generate_setup_guides')
    root = Path(__file__).resolve().parents[1]
    raw = (root / 'contracts/setup_guides_v1.json').read_text()
    for invalid in ([], ['invented'], ['roku_network', 'roku_network'], ['roku_network', 'roku_model', 'roku_alexa', 'google_roku']):
        data = json.loads(raw)
        group = next(group for group in data['groups'] if group['id'] == 'tcl_roku')
        group['primary_routes'] = invalid
        try:
            generator.validate(data)
        except ValueError:
            continue
        raise AssertionError(f'invalid primary choices accepted: {invalid}')


def test_roku_default_instructions_are_short_and_keep_context_in_optional_notes():
    routes = setup_routes()
    for identifier in ('roku_network', 'roku_model'):
        for step in routes[identifier]['steps']:
            assert len(step['instruction'].split()) <= 18
            assert step['note']
    assert 'IP address' in routes['roku_network']['steps'][-1]['instruction']
    assert 'Model' in routes['roku_model']['steps'][-1]['instruction']


def setup_routes():
    root = Path(__file__).resolve().parents[1]
    return {route['id']: route for route in json.loads((root / 'contracts/setup_guides_v1.json').read_text())['routes']}


def test_roku_tv_part_one_leads_to_official_phone_app_pictures():
    data = json.loads((Path(__file__).resolve().parents[1] / 'contracts/setup_guides_v1.json').read_text())
    routes = setup_routes()
    assert routes['roku_network']['steps'][-1]['surface'] == 'tv'
    assert 'phone' in routes['roku_network']['steps'][-1]['note'].lower()
    phone = routes['roku_phone']
    assert phone['title'].startswith('2. Connect to your phone')
    assert [step['surface'] for step in phone['steps']] == ['phone'] * 5
    assert 'same Wi-Fi' in phone['steps'][1]['instruction']
    assert phone['steps'][-1]['items'][phone['steps'][-1]['focus']] == 'Remote'
    assert all('roku_phone' in group['routes'] for group in data['groups'] if group['id'] in ('tcl', 'tcl_roku', 'roku'))
    assert any(source['id'] == 'roku_mobile' and source['url'].startswith('https://support.roku.com/') for source in data['sources'])


def test_pin_picture_highlights_input_before_a_separate_confirmation_picture():
    steps = setup_routes()['lg_pair']['steps']
    entry = next(i for i, step in enumerate(steps) if step['title'] == 'Enter the real PIN')
    assert steps[entry]['action'] == 'type'
    assert steps[entry]['items'][steps[entry]['focus']] == 'PIN'
    assert steps[entry + 1]['action'] == 'tap'
    assert steps[entry + 1]['items'][steps[entry + 1]['focus']] == 'Next'


def test_faster_google_setup_states_platform_limits_and_checks_the_tv_result():
    route = setup_routes()['google_fast']
    assert 'iOS 17' in route['applies_to'] and 'Android 9' in route['applies_to']
    assert '3.3100002' in route['steps'][1]['note']
    assert route['steps'][-1]['surface'] == 'tv'
    assert 'Home screen' in route['steps'][-1]['instruction']


def test_assistant_choice_pictures_do_not_single_out_an_unselected_provider():
    routes = setup_routes()
    for identifier in ('lg_account5', 'lg_account6'):
        step = routes[identifier]['steps'][-1]
        assert step['items'][step['focus']] == 'Your chosen assistant guide'
    for step in routes['vizio_assist']['steps']:
        if 'Google Home or' in step['instruction']:
            assert 'chosen' in step['items'][step['focus']].lower()


def test_legacy_sony_remote_start_precedes_the_google_account_selection():
    steps = setup_routes()['sony_legacy']['steps']
    start = next(i for i, step in enumerate(steps) if step['screen'] == 'Remote start')
    account = next(i for i, step in enumerate(steps) if step['title'] == 'Choose the TV Google account')
    assert start < account

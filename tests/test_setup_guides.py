"""Illustrated setup is guidance, never a record of device authorization."""
import importlib
import json
from pathlib import Path
from xml.etree import ElementTree


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


def test_roku_model_system_picture_highlights_system_instead_of_network():
    from tools.export_picture_guide import svg

    route = setup_routes()['roku_model']
    picture = ElementTree.fromstring(svg(route['steps'][2], 3, route))
    highlights = [node.text for node in picture.findall('.//text') if node.text and '3 → ' in node.text]
    assert highlights == ['3 → System']


def test_roku_pictures_name_the_actual_menu_at_each_step():
    from tools.export_picture_guide import svg

    for identifier in ('roku_model', 'roku_network'):
        route = setup_routes()[identifier]
        for number in range(2, 6):
            step = route['steps'][number - 1]
            picture = ElementTree.fromstring(svg(step, number, route))
            labels = [node.text for node in picture.findall('.//text')]
            assert step['screen'] in labels, (identifier, number)


def test_every_picture_has_one_numbered_action_and_matching_accessible_label():
    from tools.export_picture_guide import svg

    for route in setup_routes().values():
        for number, step in enumerate(route['steps'], 1):
            picture = ElementTree.fromstring(svg(step, number, route))
            highlighted = [node.text for node in picture.findall('.//text')
                           if node.text and node.text.startswith(f'{number} → ')]
            assert len(highlighted) == 1, (route['id'], number)
            assert step['items'][step['focus']] in picture.attrib['aria-label'], (route['id'], number)


def test_picture_instructions_fit_a_short_reading_step():
    for route in setup_routes().values():
        for number, step in enumerate(route['steps'], 1):
            assert len(step['instruction'].split()) <= 30, (route['id'], number)


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


def test_every_roku_tv_group_can_restore_the_phone_handoff_after_rotation():
    data = json.loads((Path(__file__).resolve().parents[1] / 'contracts/setup_guides_v1.json').read_text())
    for group in data['groups']:
        if {'roku_network', 'roku_model'} & set(group['routes']):
            assert 'roku_phone' in group['routes'], group['id']


def test_phone_wifi_guides_keep_the_three_system_menus_separate():
    routes = setup_routes()
    iphone = routes['phone_iphone']['steps']
    pixel = routes['phone_pixel']['steps']
    galaxy = routes['phone_galaxy']['steps']
    assert 'Wi-Fi' in iphone[1]['items']
    assert 'Network & internet' in pixel[1]['items']
    assert 'Internet' in pixel[2]['items']
    assert 'Connections' in galaxy[1]['items']
    assert 'Wi-Fi' in galaxy[2]['items']
    assert 'checkmark' in iphone[-1]['instruction']
    assert 'Connected' in pixel[-1]['instruction']
    assert all(step['surface'] == 'phone' for route in (iphone, pixel, galaxy) for step in route)


def test_pin_picture_highlights_input_before_a_separate_confirmation_picture():
    steps = setup_routes()['lg_pair']['steps']
    entry = next(i for i, step in enumerate(steps) if step['title'] == 'Enter the real PIN')
    assert steps[entry]['action'] == 'type'
    assert steps[entry]['items'][steps[entry]['focus']] == 'PIN'
    assert steps[entry + 1]['action'] == 'tap'
    assert steps[entry + 1]['items'][steps[entry + 1]['focus']] == 'Next'


def test_primary_phone_pairing_includes_installation_and_lg_network_confirmation():
    routes = setup_routes()
    for identifier, app in [('samsung_ok', 'SmartThings'), ('samsung_pin', 'SmartThings'), ('lg_pair', 'LG ThinQ'), ('google_remote', 'Google TV'), ('vizio_pair', 'VIZIO Mobile')]:
        step = routes[identifier]['steps'][1]
        assert step['surface'] == 'phone'
        assert step['screen'] == 'App Store or Google Play'
        assert app in step['instruction']
        assert 'install' in step['instruction'].lower()
    lg = routes['lg_pair']['steps']
    select_device = next(i for i, step in enumerate(lg) if step['screen'] == 'Add a Device')
    assert lg[select_device + 1]['items'][lg[select_device + 1]['focus']] == 'Next'
    assert 'same Wi-Fi' in lg[select_device + 1]['instruction']
    assert lg[select_device + 2]['screen'] == 'Select Device'


def test_new_vizio_account_and_phone_pairing_follow_distinct_official_codes():
    data = json.loads((Path(__file__).resolve().parents[1] / 'contracts/setup_guides_v1.json').read_text())
    routes = setup_routes()
    sources = {source['id']: source['url'] for source in data['sources']}
    new = routes['vizio_walmart']
    assert new['sources'] == ['vizio_new_account', 'vizio_pair']
    assert [step['items'][step['focus']] for step in new['steps'][:4]] == [
        'My Hub', 'Connect your Walmart account', 'TV QR code', 'Sign in / Create account'
    ]
    assert new['steps'][-2]['items'][new['steps'][-2]['focus']] == 'Enter 4-digit code'
    assert '6-digit code' in routes['vizio_account']['steps'][-2]['items'][0]
    assert 'vizio_walmart' in next(group for group in data['groups'] if group['id'] == 'vizio')['primary_routes']
    assert sources['vizio_pair'] == 'https://www.vizio.com/en/mobile'
    assert sources['vizio_new_account'] == 'https://www.vizio.com/en/overview-account'
    assert 'google_link' not in routes['vizio_alexa']['sources']


def test_vizio_qr_picture_puts_the_code_on_the_tv():
    from tools.export_picture_guide import svg

    route = setup_routes()['vizio_walmart']
    picture = ElementTree.fromstring(svg(route['steps'][2], 3, route))
    labels = [node.text for node in picture.findall('.//text') if node.text]
    assert 'TV screen' in labels
    assert 'Phone camera' in labels
    assert '3 → TV QR code' in labels


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

"""Illustrated setup is guidance, never a record of device authorization."""
import importlib
import json
from pathlib import Path


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

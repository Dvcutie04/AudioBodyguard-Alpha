"""A TCL Roku owner must be able to find the network screen without a Google TV detour."""
import json
from pathlib import Path


def test_tcl_roku_has_a_short_network_and_model_path():
    data = json.loads((Path(__file__).resolve().parents[1] / 'contracts/setup_guides_v1.json').read_text())
    groups = {g['id']: g for g in data['groups']}
    routes = {r['id']: r for r in data['routes']}
    assert 'roku_network' in groups['tcl_roku']['routes']
    assert 'roku_model' in groups['tcl_roku']['routes']
    network = routes['roku_network']
    assert len(network['steps']) <= 6
    assert [s['items'][s['focus']] for s in network['steps']][1:4] == ['Settings', 'Network', 'About']
    assert network['models'] == []  # The supplied photo does not establish a model number.
    assert 'IP address' in network['steps'][-1]['instruction']

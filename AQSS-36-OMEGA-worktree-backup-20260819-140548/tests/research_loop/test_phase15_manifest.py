import pytest
import json
from src.research_loop.phase15.validate_manifest import validate_manifest

def test_manifest_validation_function(tmp_path):
    schema_content = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["experiment_id"],
        "properties": {
            "experiment_id": {"type": "string"}
        }
    }
    manifest_content = {"experiment_id": "AQSS36-P15-001"}
    s = tmp_path / "schema.json"
    m = tmp_path / "manifest.json"
    with open(s, "w") as f:
        json.dump(schema_content, f)
    with open(m, "w") as f:
        json.dump(manifest_content, f)
    assert validate_manifest(str(m), str(s)) is True

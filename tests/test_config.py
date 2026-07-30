from __future__ import annotations

import json
from pathlib import Path

import pytest

from timesync_sim.config import ConfigurationError, load_ca_configuration
from timesync_sim.models import TopologyConfig


def test_example_ca_configuration_loads() -> None:
    root = Path(__file__).resolve().parents[1]
    node, topology, path = load_ca_configuration(str(root / "configs" / "ca_101.json"))
    assert node.es_id == 101
    assert topology.endpoint_for(101).role == "CA"
    assert path.name == "ca_101.json"


def test_duplicate_es_id_is_rejected() -> None:
    raw = {
        "endpoints": [
            {"es_id": 1, "name": "A", "role": "CM", "ip": "127.0.0.1", "port": 1},
            {"es_id": 1, "name": "B", "role": "CA", "ip": "127.0.0.1", "port": 2}
        ],
        "ca_parameters": {
            "1": {"l2": 0, "clock_drift_rate": 0, "relative_offset_delay": 0}
        }
    }
    with pytest.raises(ValueError, match="duplicate ES_ID"):
        TopologyConfig.model_validate(raw)


def test_node_role_mismatch_is_rejected(tmp_path: Path) -> None:
    topology = {
        "endpoints": [
            {"es_id": 1, "name": "CM", "role": "CM", "ip": "127.0.0.1", "port": 10001}
        ],
        "ca_parameters": {}
    }
    node = {
        "role": "CA",
        "es_id": 1,
        "t2": 200,
        "dmax": 10,
        "topology_path": "topology.json"
    }
    (tmp_path / "topology.json").write_text(json.dumps(topology), encoding="utf-8")
    node_path = tmp_path / "node.json"
    node_path.write_text(json.dumps(node), encoding="utf-8")
    with pytest.raises(ConfigurationError, match="declares CA"):
        load_ca_configuration(str(node_path))

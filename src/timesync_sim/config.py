from __future__ import annotations

import json
from pathlib import Path
from typing import Tuple, Type, TypeVar

from pydantic import BaseModel, ValidationError

from .models import CANodeConfig, CMNodeConfig, TopologyConfig


T = TypeVar("T", bound=BaseModel)


class ConfigurationError(RuntimeError):
    pass


def _load_json(path: Path) -> object:
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError as exc:
        raise ConfigurationError(f"Configuration file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigurationError(f"Invalid JSON in {path}: {exc}") from exc
    except OSError as exc:
        raise ConfigurationError(f"Unable to read {path}: {exc}") from exc


def _validate(model_type: Type[T], raw: object, path: Path) -> T:
    try:
        return model_type.model_validate(raw)
    except ValidationError as exc:
        raise ConfigurationError(f"Validation failed for {path}:\n{exc}") from exc


def load_cm_configuration(path: str) -> Tuple[CMNodeConfig, TopologyConfig, Path]:
    config_path = Path(path).expanduser().resolve()
    node = _validate(CMNodeConfig, _load_json(config_path), config_path)
    topology_path = (config_path.parent / node.topology_path).resolve()
    topology = _validate(TopologyConfig, _load_json(topology_path), topology_path)
    _validate_node_in_topology(node.es_id, "CM", topology, config_path)
    return node, topology, config_path


def load_ca_configuration(path: str) -> Tuple[CANodeConfig, TopologyConfig, Path]:
    config_path = Path(path).expanduser().resolve()
    node = _validate(CANodeConfig, _load_json(config_path), config_path)
    topology_path = (config_path.parent / node.topology_path).resolve()
    topology = _validate(TopologyConfig, _load_json(topology_path), topology_path)
    _validate_node_in_topology(node.es_id, "CA", topology, config_path)
    return node, topology, config_path


def _validate_node_in_topology(
    es_id: int,
    expected_role: str,
    topology: TopologyConfig,
    node_path: Path,
) -> None:
    try:
        endpoint = topology.endpoint_for(es_id)
    except KeyError as exc:
        raise ConfigurationError(
            f"ES_ID {es_id} from {node_path} does not exist in topology.json"
        ) from exc
    if endpoint.role != expected_role:
        raise ConfigurationError(
            f"ES_ID {es_id} has role {endpoint.role} in topology.json, "
            f"but {node_path.name} declares {expected_role}"
        )

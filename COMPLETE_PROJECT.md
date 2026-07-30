# Complete Project Output

## 1. 完整目录结构

```text
time_sync_ca_sim/
├── COMPLETE_PROJECT.md
├── README.md
├── requirements.txt
├── pytest.ini
├── setup_env.cmd
├── run_all_demo.cmd
├── run_cm.py
├── run_ca.py
├── configs/
│   ├── topology.json
│   ├── cm_1.json
│   ├── cm_2.json
│   ├── ca_101.json
│   └── ca_102.json
├── src/
│   └── timesync_sim/
│       ├── __init__.py
│       ├── constants.py
│       ├── models.py
│       ├── config.py
│       ├── protocol.py
│       ├── math_utils.py
│       ├── logic.py
│       ├── network.py
│       ├── cm_engine.py
│       ├── ca_engine.py
│       └── gui/
│           ├── __init__.py
│           ├── common.py
│           ├── cm_window.py
│           ├── ca_window.py
│           └── integrity_dialog.py
└── tests/
    ├── conftest.py
    ├── test_config.py
    ├── test_logic.py
    ├── test_math_utils.py
    └── test_protocol.py
```

## 2. requirements.txt

```text
PySide6-Essentials==6.8.3
pydantic==2.10.6
pytest==8.3.5
```

### Windows CMD 环境配置与运行

```bat
cd /d C:\path\to\time_sync_ca_sim
setup_env.cmd
run_all_demo.cmd
```

手动运行单个进程：

```bat
call .venv\Scripts\activate.bat
python run_cm.py configs\cm_1.json
python run_ca.py configs\ca_101.json
```

## 3. 每个文件的完整代码

### `README.md`

```markdown
# Time Synchronization + CA Communication Simulator

A Windows-oriented Python 3.9 project that runs each Clock Manager (CM) and Clock Agent (CA) as a separate PySide6 process. Processes communicate through UDP unicast endpoints declared in `configs/topology.json`.

## 1. Project structure

```text
time_sync_ca_sim/
├── README.md
├── requirements.txt
├── pytest.ini
├── setup_env.cmd
├── run_all_demo.cmd
├── run_cm.py
├── run_ca.py
├── configs/
│   ├── topology.json
│   ├── cm_1.json
│   ├── cm_2.json
│   ├── ca_101.json
│   └── ca_102.json
├── src/
│   └── timesync_sim/
│       ├── __init__.py
│       ├── constants.py
│       ├── models.py
│       ├── config.py
│       ├── protocol.py
│       ├── math_utils.py
│       ├── logic.py
│       ├── network.py
│       ├── cm_engine.py
│       ├── ca_engine.py
│       └── gui/
│           ├── __init__.py
│           ├── common.py
│           ├── cm_window.py
│           ├── ca_window.py
│           └── integrity_dialog.py
└── tests/
    ├── conftest.py
    ├── test_config.py
    ├── test_logic.py
    ├── test_math_utils.py
    └── test_protocol.py
```

## 2. Environment setup on Windows CMD

Open **Command Prompt**, not PowerShell, then run:

```bat
cd /d C:\path\to\time_sync_ca_sim
setup_env.cmd
```

Equivalent manual commands:

```bat
cd /d C:\path\to\time_sync_ca_sim
py -3.9 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pytest
```

If `py -3.9` is unavailable but `python` points to Python 3.9, use:

```bat
python -m venv .venv
```

## 3. Run the supplied four-process demonstration

```bat
cd /d C:\path\to\time_sync_ca_sim
run_all_demo.cmd
```

This launches:

- CM ES_ID 1 on `127.0.0.1:12001`
- CM ES_ID 2 on `127.0.0.1:12002`
- CA ES_ID 101 on `127.0.0.1:12101`
- CA ES_ID 102 on `127.0.0.1:12102`

Start the CMs and CAs close together in time. Their process start clocks are independent; the CA display is aligned to the currently selected CM when requests arrive.

## 4. Run one process manually

Activate the environment first:

```bat
call .venv\Scripts\activate.bat
```

Run with a configuration path:

```bat
python run_cm.py configs\cm_1.json
python run_ca.py configs\ca_101.json
```

Run without a path to use the file-selection and confirmation dialog:

```bat
python run_cm.py
python run_ca.py
```

Each ES must have a unique IP/port pair. Closing a window stops that process.

## 5. Configuration format

### CM node JSON

```json
{
  "role": "CM",
  "es_id": 1,
  "t1": 100.0,
  "e1": 0.1,
  "topology_path": "topology.json"
}
```

### CA node JSON

```json
{
  "role": "CA",
  "es_id": 101,
  "t2": 300.0,
  "dmax": 50.0,
  "topology_path": "topology.json"
}
```

### Topology JSON

`ca_parameters` is keyed by CA ES_ID. JSON object keys are strings on disk and are converted to integers by Pydantic.

```json
{
  "endpoints": [
    {
      "es_id": 1,
      "name": "CM1",
      "role": "CM",
      "ip": "127.0.0.1",
      "port": 12001
    },
    {
      "es_id": 101,
      "name": "CA101",
      "role": "CA",
      "ip": "127.0.0.1",
      "port": 12101
    }
  ],
  "ca_parameters": {
    "101": {
      "l2": 0.25,
      "clock_drift_rate": 0.00001,
      "relative_offset_delay": 1.5
    }
  }
}
```

## 6. Implemented timing behavior

- Each CM has a local monotonic 1000 ms cycle.
- At configured T1, a CM sends the current request and the completed previous `clock_offset_list` in the same event-loop iteration.
- The first cycle sends no list.
- Responses received at a CM phase greater than 500 ms are excluded.
- A cycle's list becomes complete at the next 1000 ms boundary and is transmitted at the next T1.
- A CA replies to every valid CM request after `max(0, T2 - request.T1)` milliseconds.
- T1 and T2 inside messages are fixed configuration values; they are not generated from UDP timestamps.
- `relative_offset_error` uses decimal `ROUND_HALF_UP` to 0.001.
- `None` is encoded as JSON `null` and displayed as `Unknown`.
- A selected CM list is calculated immediately but only becomes the CA's effective list at the next selected-CM cycle boundary.
- During that pending interval, time integrity checks continue using the previous effective list.

## 7. CM selection behavior

- The first structurally valid request starts the election window.
- Window duration is `max(0, T2 - request.T1)`, rounded upward to the next whole millisecond because `QTimer` uses integer milliseconds.
- The smallest CM ES_ID seen during the window is selected.
- After initial election, a newly appearing lower ES_ID does not trigger a proactive switch.
- The selected CM is unavailable when no new list has arrived for at least 2000 ms.
- On unavailability, the smallest ES_ID among CMs with a list newer than 2000 ms is selected.
- A higher-priority CM recovery does not replace a currently available CM.

## 8. Time integrity check

For a received CA data message:

1. `Dmax == 0` passes.
2. Unknown `local_clock_offset[sender]` passes.
3. Otherwise, a reset-counter mismatch discards.
4. Otherwise, `age` equals the message's configured `transmission_latency`.
5. Only `0 < age < Dmax` passes.

The receiver opens a non-modal flowchart window and highlights the traversed decisions and final result.

## 9. Tests

```bat
call .venv\Scripts\activate.bat
python -m pytest
```

The tests cover configuration validation, duplicate ES_ID detection, protocol serialization, ROUND_HALF_UP behavior, local-offset calculation, CM election/failover helpers, and time-integrity branches.

## 10. Current limitations and assumptions

- Windows timer scheduling and Qt event-loop latency can shift an action by several milliseconds. Logical timestamps remain fixed, but the 500 ms and 2000 ms decisions use real process time.
- Separate CM processes are not started from a shared global epoch. A CA derives the selected CM's cycle phase from request receipt time minus that request's T1.
- UDP on localhost normally has negligible delay, but UDP remains unreliable and unordered. No retransmission or acknowledgement layer is added.
- A virtual link is represented as direct UDP unicast to a topology endpoint. BAG, switch routing, bandwidth policing, redundancy, and AFDX frame behavior are outside this implementation.
- `T1` and `T2` ranges and `T1 < T2` are intentionally not validated. Negative response/election delays are clamped to zero because Qt cannot schedule a negative timer.
- Fractional timer delays are rounded upward to an integer millisecond. Message calculations retain the configured numeric values.
- A failover may immediately use the most recent cached list from the newly selected CM, then publishes its calculated local offsets at that CM's next inferred cycle boundary.
- Switching CM clears the effective list and local offsets before the new source becomes effective. This prevents stale offsets from being presented as belonging to the new source.
- Reset cancels scheduled responses and pending local-offset applications. CA data messages are sent immediately, so there is no queued CA data message to cancel.
- Datagram sender IP/port is not cryptographically authenticated. The protocol validates message structure, ES_ID, role, and destination fields.
- The GUI shows numeric values to three decimal places, while local-offset calculations are not forcibly quantized unless the specified formula requires it.
- The project does not simulate true clock drift over time; `clock_drift_rate` is used only in `relative_offset_error`.
```

### `requirements.txt`

```text
PySide6-Essentials==6.8.3
pydantic==2.10.6
pytest==8.3.5
```

### `pytest.ini`

```ini
[pytest]
testpaths = tests
addopts = -q
```

### `setup_env.cmd`

```bat
@echo off
setlocal
cd /d "%~dp0"

py -3.9 -m venv .venv
if errorlevel 1 goto :error

call .venv\Scripts\activate.bat
if errorlevel 1 goto :error

python -m pip install --upgrade pip
if errorlevel 1 goto :error

python -m pip install -r requirements.txt
if errorlevel 1 goto :error

python -m pytest
if errorlevel 1 goto :error

echo.
echo Environment setup and tests completed successfully.
exit /b 0

:error
echo.
echo Setup failed. Review the command output above.
exit /b 1
```

### `run_all_demo.cmd`

```bat
@echo off
setlocal
cd /d "%~dp0"

if not exist .venv\Scripts\python.exe (
    echo .venv is missing. Run setup_env.cmd first.
    exit /b 1
)

start "CM 1" .venv\Scripts\python.exe run_cm.py configs\cm_1.json
start "CM 2" .venv\Scripts\python.exe run_cm.py configs\cm_2.json
start "CA 101" .venv\Scripts\python.exe run_ca.py configs\ca_101.json
start "CA 102" .venv\Scripts\python.exe run_ca.py configs\ca_102.json
```

### `run_cm.py`

```python
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication, QMessageBox

from timesync_sim.cm_engine import CMEngine
from timesync_sim.config import ConfigurationError, load_cm_configuration
from timesync_sim.gui.cm_window import CMWindow
from timesync_sim.gui.common import choose_json_configuration


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Time Sync CM Simulator")

    config_path = sys.argv[1] if len(sys.argv) > 1 else None
    if config_path is None:
        config_path = choose_json_configuration(
            None,
            "Select a CM node configuration",
            str(PROJECT_ROOT / "configs"),
        )
    if not config_path:
        return 0

    try:
        config, topology, _ = load_cm_configuration(config_path)
        engine = CMEngine(config, topology)
    except (ConfigurationError, RuntimeError) as exc:
        QMessageBox.critical(None, "CM startup failed", str(exc))
        return 1

    window = CMWindow(engine)
    window.show()
    engine.start()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
```

### `run_ca.py`

```python
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication, QMessageBox

from timesync_sim.ca_engine import CAEngine
from timesync_sim.config import ConfigurationError, load_ca_configuration
from timesync_sim.gui.ca_window import CAWindow
from timesync_sim.gui.common import choose_json_configuration


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Time Sync CA Simulator")

    config_path = sys.argv[1] if len(sys.argv) > 1 else None
    if config_path is None:
        config_path = choose_json_configuration(
            None,
            "Select a CA node configuration",
            str(PROJECT_ROOT / "configs"),
        )
    if not config_path:
        return 0

    try:
        config, topology, _ = load_ca_configuration(config_path)
        engine = CAEngine(config, topology)
    except (ConfigurationError, RuntimeError) as exc:
        QMessageBox.critical(None, "CA startup failed", str(exc))
        return 1

    window = CAWindow(engine)
    window.show()
    engine.start()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
```

### `configs/topology.json`

```json
{
  "endpoints": [
    {
      "es_id": 1,
      "name": "CM1",
      "role": "CM",
      "ip": "127.0.0.1",
      "port": 12001
    },
    {
      "es_id": 2,
      "name": "CM2",
      "role": "CM",
      "ip": "127.0.0.1",
      "port": 12002
    },
    {
      "es_id": 101,
      "name": "CA101",
      "role": "CA",
      "ip": "127.0.0.1",
      "port": 12101
    },
    {
      "es_id": 102,
      "name": "CA102",
      "role": "CA",
      "ip": "127.0.0.1",
      "port": 12102
    }
  ],
  "ca_parameters": {
    "101": {
      "l2": 0.25,
      "clock_drift_rate": 0.00001,
      "relative_offset_delay": 1.5
    },
    "102": {
      "l2": 0.4,
      "clock_drift_rate": 0.00002,
      "relative_offset_delay": 2.0
    }
  }
}
```

### `configs/cm_1.json`

```json
{
  "role": "CM",
  "es_id": 1,
  "t1": 100.0,
  "e1": 0.1,
  "topology_path": "topology.json"
}
```

### `configs/cm_2.json`

```json
{
  "role": "CM",
  "es_id": 2,
  "t1": 120.0,
  "e1": 0.2,
  "topology_path": "topology.json"
}
```

### `configs/ca_101.json`

```json
{
  "role": "CA",
  "es_id": 101,
  "t2": 300.0,
  "dmax": 50.0,
  "topology_path": "topology.json"
}
```

### `configs/ca_102.json`

```json
{
  "role": "CA",
  "es_id": 102,
  "t2": 320.0,
  "dmax": 50.0,
  "topology_path": "topology.json"
}
```

### `src/timesync_sim/__init__.py`

```python
"""Time synchronization and CA communication simulator."""

__version__ = "1.0.0"
```

### `src/timesync_sim/constants.py`

```python
from __future__ import annotations

PROTOCOL_VERSION = 1
CYCLE_MS = 1000
RESPONSE_CUTOFF_MS = 500
CM_UNAVAILABLE_MS = 2000
REQUEST_NUMBER_MODULUS = 65536
RESET_COUNTER_MODULUS = 256
DISPLAY_DECIMALS = 3
```

### `src/timesync_sim/models.py`

```python
from __future__ import annotations

from typing import Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator


Role = Literal["CM", "CA"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Endpoint(StrictModel):
    es_id: int = Field(ge=0)
    name: str = Field(min_length=1)
    role: Role
    ip: str = Field(min_length=1)
    port: int = Field(ge=1, le=65535)


class CAParameters(StrictModel):
    l2: float = Field(default=0.0, ge=0.0, le=655.35)
    clock_drift_rate: float = Field(ge=0.0)
    relative_offset_delay: float = Field(ge=0.0, le=655.35)


class TopologyConfig(StrictModel):
    endpoints: List[Endpoint]
    ca_parameters: Dict[int, CAParameters]

    @model_validator(mode="after")
    def validate_topology(self) -> "TopologyConfig":
        ids = [endpoint.es_id for endpoint in self.endpoints]
        duplicates = sorted({es_id for es_id in ids if ids.count(es_id) > 1})
        if duplicates:
            raise ValueError(f"topology.json contains duplicate ES_ID values: {duplicates}")

        endpoint_ids = set(ids)
        ca_ids = {endpoint.es_id for endpoint in self.endpoints if endpoint.role == "CA"}
        parameter_ids = set(self.ca_parameters.keys())
        missing = sorted(ca_ids - parameter_ids)
        extra = sorted(parameter_ids - ca_ids)
        if missing:
            raise ValueError(f"Missing CA parameters for ES_ID values: {missing}")
        if extra:
            raise ValueError(f"CA parameters exist for non-CA ES_ID values: {extra}")

        endpoint_pairs = [(endpoint.ip, endpoint.port) for endpoint in self.endpoints]
        duplicate_pairs = sorted({pair for pair in endpoint_pairs if endpoint_pairs.count(pair) > 1})
        if duplicate_pairs:
            raise ValueError(f"Duplicate IP/port endpoint values: {duplicate_pairs}")
        return self

    def endpoint_for(self, es_id: int) -> Endpoint:
        for endpoint in self.endpoints:
            if endpoint.es_id == es_id:
                return endpoint
        raise KeyError(f"Unknown ES_ID: {es_id}")

    def endpoints_by_role(self, role: Role) -> List[Endpoint]:
        return [endpoint for endpoint in self.endpoints if endpoint.role == role]


class CMNodeConfig(StrictModel):
    role: Literal["CM"]
    es_id: int = Field(ge=0)
    t1: float
    e1: float = Field(default=0.0, ge=0.0, le=655.35)
    topology_path: str = Field(min_length=1)


class CANodeConfig(StrictModel):
    role: Literal["CA"]
    es_id: int = Field(ge=0)
    t2: float
    dmax: float = Field(ge=0.0)
    topology_path: str = Field(min_length=1)


class RequestMessage(StrictModel):
    protocol_version: Literal[1] = 1
    message_type: Literal["request"]
    cm_es_id: int = Field(ge=0)
    request_number: int = Field(ge=0, le=65535)
    t1: float


class ResponseMessage(StrictModel):
    protocol_version: Literal[1] = 1
    message_type: Literal["response"]
    cm_es_id: int = Field(ge=0)
    ca_es_id: int = Field(ge=0)
    request_number: int = Field(ge=0, le=65535)
    t1: float
    t2: float
    reset_counter: int = Field(ge=0, le=255)


class ClockOffsetEntry(StrictModel):
    ca_es_id: int = Field(ge=0)
    relative_offset: Optional[float]
    reset_counter: Optional[int] = Field(default=None, ge=0, le=255)
    relative_offset_error: float


class ClockOffsetListMessage(StrictModel):
    protocol_version: Literal[1] = 1
    message_type: Literal["clock_offset_list"]
    cm_es_id: int = Field(ge=0)
    request_number: int = Field(ge=0, le=65535)
    number_of_ca: int = Field(ge=0)
    entries: List[ClockOffsetEntry]

    @model_validator(mode="after")
    def validate_entry_count(self) -> "ClockOffsetListMessage":
        if self.number_of_ca != len(self.entries):
            raise ValueError("number_of_ca does not match entries length")
        entry_ids = [entry.ca_es_id for entry in self.entries]
        if len(entry_ids) != len(set(entry_ids)):
            raise ValueError("clock_offset_list contains duplicate CA ES_ID entries")
        return self

    def entry_for(self, ca_es_id: int) -> Optional[ClockOffsetEntry]:
        for entry in self.entries:
            if entry.ca_es_id == ca_es_id:
                return entry
        return None


class DataMessage(StrictModel):
    protocol_version: Literal[1] = 1
    message_type: Literal["ca_data"]
    sender_ca_es_id: int = Field(ge=0)
    receiver_ca_es_id: int = Field(ge=0)
    reset_counter: int = Field(ge=0, le=255)
    transmission_latency: int = Field(ge=0)
    payload: str = "CA communication test message"


AnyMessage = Union[
    RequestMessage,
    ResponseMessage,
    ClockOffsetListMessage,
    DataMessage,
]
```

### `src/timesync_sim/config.py`

```python
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
```

### `src/timesync_sim/protocol.py`

```python
from __future__ import annotations

import json
from typing import Dict, Type

from pydantic import ValidationError

from .models import (
    AnyMessage,
    ClockOffsetListMessage,
    DataMessage,
    RequestMessage,
    ResponseMessage,
    StrictModel,
)


class ProtocolError(RuntimeError):
    pass


MESSAGE_MODELS: Dict[str, Type[StrictModel]] = {
    "request": RequestMessage,
    "response": ResponseMessage,
    "clock_offset_list": ClockOffsetListMessage,
    "ca_data": DataMessage,
}


def encode_message(message: AnyMessage) -> bytes:
    return message.model_dump_json(exclude_none=False).encode("utf-8")


def decode_message(payload: bytes) -> AnyMessage:
    try:
        raw = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError(f"Invalid JSON datagram: {exc}") from exc

    if not isinstance(raw, dict):
        raise ProtocolError("Datagram root must be a JSON object")
    message_type = raw.get("message_type")
    model_type = MESSAGE_MODELS.get(message_type)
    if model_type is None:
        raise ProtocolError(f"Unsupported message_type: {message_type!r}")
    try:
        return model_type.model_validate(raw)  # type: ignore[return-value]
    except ValidationError as exc:
        raise ProtocolError(f"Invalid {message_type} message: {exc}") from exc
```

### `src/timesync_sim/math_utils.py`

```python
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional


THREE_DECIMALS = Decimal("0.001")


def round_half_up_3(value: float) -> float:
    """Round a number to 0.001 with decimal ROUND_HALF_UP semantics."""
    return float(Decimal(str(value)).quantize(THREE_DECIMALS, rounding=ROUND_HALF_UP))


def calculate_relative_offset_error(
    clock_drift_rate: float,
    e1: float,
    l2: float,
) -> float:
    value = (
        Decimal("3000") * Decimal(str(clock_drift_rate))
        + Decimal(str(e1))
        + Decimal(str(l2))
    )
    return float(value.quantize(THREE_DECIMALS, rounding=ROUND_HALF_UP))


def calculate_local_clock_offset(
    remote_relative_offset: Optional[float],
    local_relative_offset: Optional[float],
    remote_relative_offset_error: Optional[float],
    local_relative_offset_error: Optional[float],
    remote_delay: Optional[float],
    local_delay: Optional[float],
) -> Optional[float]:
    values = (
        remote_relative_offset,
        local_relative_offset,
        remote_relative_offset_error,
        local_relative_offset_error,
        remote_delay,
        local_delay,
    )
    if any(value is None for value in values):
        return None

    result = (
        Decimal(str(remote_relative_offset))
        - Decimal(str(local_relative_offset))
        + Decimal(str(remote_relative_offset_error))
        - Decimal(str(local_relative_offset_error))
        + max(Decimal(str(remote_delay)), Decimal(str(local_delay)))
    )
    return float(result)
```

### `src/timesync_sim/logic.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set

from .constants import CM_UNAVAILABLE_MS
from .math_utils import calculate_local_clock_offset
from .models import ClockOffsetListMessage


@dataclass(frozen=True)
class IntegrityStep:
    key: str
    text: str
    passed: Optional[bool]


@dataclass(frozen=True)
class IntegrityTrace:
    accepted: bool
    steps: List[IntegrityStep]
    reason: str


def choose_initial_cm(first_cm_es_id: int, request_cm_ids: Iterable[int]) -> int:
    candidates: Set[int] = set(request_cm_ids)
    if candidates:
        return min(candidates)
    return first_cm_es_id


def choose_cm_after_timeout(
    current_cm_es_id: Optional[int],
    last_clock_list_ms: Dict[int, int],
    now_ms: int,
) -> Optional[int]:
    if current_cm_es_id is not None:
        last = last_clock_list_ms.get(current_cm_es_id)
        if last is not None and now_ms - last < CM_UNAVAILABLE_MS:
            return current_cm_es_id

    available = sorted(
        cm_es_id
        for cm_es_id, last in last_clock_list_ms.items()
        if now_ms - last < CM_UNAVAILABLE_MS
    )
    if available:
        return available[0]
    return current_cm_es_id


def compute_local_offsets_from_list(
    clock_list: ClockOffsetListMessage,
    local_ca_es_id: int,
    relative_offset_delays: Dict[int, float],
) -> Dict[int, Optional[float]]:
    local_entry = clock_list.entry_for(local_ca_es_id)
    results: Dict[int, Optional[float]] = {}
    for remote_entry in clock_list.entries:
        if remote_entry.ca_es_id == local_ca_es_id:
            continue
        if local_entry is None:
            results[remote_entry.ca_es_id] = None
            continue
        results[remote_entry.ca_es_id] = calculate_local_clock_offset(
            remote_relative_offset=remote_entry.relative_offset,
            local_relative_offset=local_entry.relative_offset,
            remote_relative_offset_error=remote_entry.relative_offset_error,
            local_relative_offset_error=local_entry.relative_offset_error,
            remote_delay=relative_offset_delays.get(remote_entry.ca_es_id),
            local_delay=relative_offset_delays.get(local_ca_es_id),
        )
    return results


def evaluate_time_integrity(
    dmax: float,
    local_clock_offset: Optional[float],
    message_reset_counter: int,
    list_reset_counter: Optional[int],
    transmission_latency: int,
) -> IntegrityTrace:
    steps: List[IntegrityStep] = []

    dmax_zero = dmax == 0
    steps.append(IntegrityStep("dmax_zero", f"Dmax == 0 ({dmax})", dmax_zero))
    if dmax_zero:
        steps.append(IntegrityStep("result_pass", "PASS", True))
        return IntegrityTrace(True, steps, "Dmax is 0")

    offset_unknown = local_clock_offset is None
    steps.append(
        IntegrityStep(
            "offset_unknown",
            f"local_clock_offset is Unknown ({local_clock_offset})",
            offset_unknown,
        )
    )
    if offset_unknown:
        steps.append(IntegrityStep("result_pass", "PASS", True))
        return IntegrityTrace(True, steps, "local_clock_offset is Unknown")

    counters_equal = (
        list_reset_counter is not None
        and message_reset_counter == list_reset_counter
    )
    steps.append(
        IntegrityStep(
            "counter_equal",
            "message reset_counter == current clock_offset_list reset_counter "
            f"({message_reset_counter} vs {list_reset_counter})",
            counters_equal,
        )
    )
    if not counters_equal:
        steps.append(IntegrityStep("result_discard", "DISCARD", False))
        return IntegrityTrace(False, steps, "reset_counter mismatch or unavailable")

    age_valid = 0 < transmission_latency < dmax
    steps.append(
        IntegrityStep(
            "age_valid",
            f"0 < age < Dmax ({transmission_latency} < {dmax})",
            age_valid,
        )
    )
    if age_valid:
        steps.append(IntegrityStep("result_pass", "PASS", True))
        return IntegrityTrace(True, steps, "age is inside the permitted interval")

    steps.append(IntegrityStep("result_discard", "DISCARD", False))
    return IntegrityTrace(False, steps, "age is outside the permitted interval")
```

### `src/timesync_sim/network.py`

```python
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QHostAddress, QUdpSocket

from .models import AnyMessage, Endpoint
from .protocol import encode_message


class UdpTransport(QObject):
    datagram_received = Signal(bytes, str, int)
    error_occurred = Signal(str)

    def __init__(self, local_endpoint: Endpoint, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.local_endpoint = local_endpoint
        self.socket = QUdpSocket(self)
        self.socket.readyRead.connect(self._read_pending_datagrams)
        self.socket.errorOccurred.connect(self._on_error)

        address = QHostAddress(local_endpoint.ip)
        if not self.socket.bind(address, local_endpoint.port):
            raise RuntimeError(
                f"Unable to bind UDP socket to {local_endpoint.ip}:{local_endpoint.port}: "
                f"{self.socket.errorString()}"
            )

    def send(self, message: AnyMessage, destination: Endpoint) -> bool:
        payload = encode_message(message)
        written = self.socket.writeDatagram(
            payload,
            QHostAddress(destination.ip),
            destination.port,
        )
        if written != len(payload):
            self.error_occurred.emit(
                f"Failed to send complete datagram to {destination.ip}:{destination.port}: "
                f"{self.socket.errorString()}"
            )
            return False
        return True

    def _read_pending_datagrams(self) -> None:
        while self.socket.hasPendingDatagrams():
            datagram = self.socket.receiveDatagram()
            self.datagram_received.emit(
                bytes(datagram.data()),
                datagram.senderAddress().toString(),
                datagram.senderPort(),
            )

    def _on_error(self, socket_error: object) -> None:
        del socket_error
        self.error_occurred.emit(self.socket.errorString())
```

### `src/timesync_sim/cm_engine.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from PySide6.QtCore import QElapsedTimer, QObject, QTimer, Signal

from .constants import CYCLE_MS, REQUEST_NUMBER_MODULUS, RESPONSE_CUTOFF_MS
from .math_utils import calculate_relative_offset_error
from .models import (
    ClockOffsetEntry,
    ClockOffsetListMessage,
    CMNodeConfig,
    Endpoint,
    RequestMessage,
    ResponseMessage,
    TopologyConfig,
)
from .network import UdpTransport
from .protocol import ProtocolError, decode_message


@dataclass
class CMRequestRecord:
    cycle_index: int
    request_number: int
    completed: bool = False
    clock_offset_list: Optional[ClockOffsetListMessage] = None


class CMEngine(QObject):
    state_changed = Signal(object)
    log_message = Signal(str)
    fatal_error = Signal(str)

    def __init__(
        self,
        config: CMNodeConfig,
        topology: TopologyConfig,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.config = config
        self.topology = topology
        self.local_endpoint = topology.endpoint_for(config.es_id)
        self.ca_endpoints: List[Endpoint] = sorted(
            topology.endpoints_by_role("CA"), key=lambda endpoint: endpoint.es_id
        )

        self.relative_offset_delays = {
            ca_id: parameters.relative_offset_delay
            for ca_id, parameters in topology.ca_parameters.items()
        }
        self.relative_offset_errors = {
            ca_id: calculate_relative_offset_error(
                parameters.clock_drift_rate,
                config.e1,
                parameters.l2,
            )
            for ca_id, parameters in topology.ca_parameters.items()
        }
        self.relative_offsets: Dict[int, Optional[float]] = {
            endpoint.es_id: None for endpoint in self.ca_endpoints
        }
        self.last_reset_counters: Dict[int, Optional[int]] = {
            endpoint.es_id: None for endpoint in self.ca_endpoints
        }

        self.transport = UdpTransport(self.local_endpoint, self)
        self.transport.datagram_received.connect(self._on_datagram)
        self.transport.error_occurred.connect(self.log_message.emit)

        self.elapsed = QElapsedTimer()
        self.tick_timer = QTimer(self)
        self.tick_timer.setInterval(10)
        self.tick_timer.timeout.connect(self._on_tick)

        self.current_cycle = -1
        self.request_sent_for_cycle = False
        self.current_request_number: Optional[int] = None
        self.current_responses: Dict[int, ResponseMessage] = {}
        self.records: List[CMRequestRecord] = []
        self.last_completed_list: Optional[ClockOffsetListMessage] = None
        self.running = False

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.elapsed.start()
        self.tick_timer.start()
        self.log_message.emit(
            f"CM ES_ID={self.config.es_id} bound to "
            f"{self.local_endpoint.ip}:{self.local_endpoint.port}"
        )
        self._on_tick()

    def stop(self) -> None:
        self.running = False
        self.tick_timer.stop()

    def _on_tick(self) -> None:
        if not self.running:
            return
        now_ms = self.elapsed.elapsed()
        target_cycle = now_ms // CYCLE_MS
        while self.current_cycle < target_cycle:
            if self.current_cycle >= 0:
                self._finalize_current_cycle()
            self.current_cycle += 1
            self.request_sent_for_cycle = False
            self.current_request_number = None
            self.current_responses = {}

        phase_ms = now_ms % CYCLE_MS
        if not self.request_sent_for_cycle and phase_ms >= self.config.t1:
            self._send_cycle_messages()

        self.state_changed.emit(self.snapshot())

    def _send_cycle_messages(self) -> None:
        request_number = self.current_cycle % REQUEST_NUMBER_MODULUS
        request = RequestMessage(
            message_type="request",
            cm_es_id=self.config.es_id,
            request_number=request_number,
            t1=self.config.t1,
        )
        for endpoint in self.ca_endpoints:
            self.transport.send(request, endpoint)

        if self.last_completed_list is not None:
            for endpoint in self.ca_endpoints:
                self.transport.send(self.last_completed_list, endpoint)
            self.log_message.emit(
                f"Sent request {request_number} and clock_offset_list "
                f"{self.last_completed_list.request_number} to all CAs"
            )
        else:
            self.log_message.emit(
                f"Sent first request {request_number}; no previous clock_offset_list exists"
            )

        self.request_sent_for_cycle = True
        self.current_request_number = request_number
        self.records.append(
            CMRequestRecord(
                cycle_index=self.current_cycle,
                request_number=request_number,
            )
        )
        self.records = self.records[-2:]

    def _finalize_current_cycle(self) -> None:
        if not self.request_sent_for_cycle or self.current_request_number is None:
            return

        entries: List[ClockOffsetEntry] = []
        for endpoint in self.ca_endpoints:
            ca_id = endpoint.es_id
            response = self.current_responses.get(ca_id)
            if response is None:
                relative_offset = None
            else:
                relative_offset = response.t2 - response.t1
                self.last_reset_counters[ca_id] = response.reset_counter
            self.relative_offsets[ca_id] = relative_offset
            entries.append(
                ClockOffsetEntry(
                    ca_es_id=ca_id,
                    relative_offset=relative_offset,
                    reset_counter=self.last_reset_counters[ca_id],
                    relative_offset_error=self.relative_offset_errors[ca_id],
                )
            )

        clock_list = ClockOffsetListMessage(
            message_type="clock_offset_list",
            cm_es_id=self.config.es_id,
            request_number=self.current_request_number,
            number_of_ca=len(entries),
            entries=entries,
        )
        self.last_completed_list = clock_list
        for record in self.records:
            if (
                record.cycle_index == self.current_cycle
                and record.request_number == self.current_request_number
            ):
                record.completed = True
                record.clock_offset_list = clock_list
                break
        self.log_message.emit(
            f"Published clock_offset_list {self.current_request_number} at cycle boundary"
        )

    def _on_datagram(self, payload: bytes, sender_ip: str, sender_port: int) -> None:
        try:
            message = decode_message(payload)
        except ProtocolError as exc:
            self.log_message.emit(f"Discarded malformed datagram: {exc}")
            return

        if not isinstance(message, ResponseMessage):
            return
        if message.cm_es_id != self.config.es_id:
            return
        known_ca_ids = {endpoint.es_id for endpoint in self.ca_endpoints}
        if message.ca_es_id not in known_ca_ids:
            self.log_message.emit(
                f"Discarded response from unknown CA ES_ID={message.ca_es_id}"
            )
            return
        if self.current_request_number is None:
            return
        if message.request_number != self.current_request_number:
            self.log_message.emit(
                f"Discarded response request_number={message.request_number}; "
                f"current request is {self.current_request_number}"
            )
            return

        phase_ms = self.elapsed.elapsed() % CYCLE_MS
        if phase_ms > RESPONSE_CUTOFF_MS:
            self.log_message.emit(
                f"Response from CA {message.ca_es_id} arrived at {phase_ms} ms and missed cutoff"
            )
            return

        self.current_responses[message.ca_es_id] = message
        self.log_message.emit(
            f"Accepted response {message.request_number} from CA {message.ca_es_id} "
            f"at phase {phase_ms} ms"
        )

    def snapshot(self) -> Dict[str, object]:
        phase_ms = self.elapsed.elapsed() % CYCLE_MS if self.elapsed.isValid() else 0
        return {
            "es_id": self.config.es_id,
            "phase_ms": phase_ms,
            "cycle_index": self.current_cycle,
            "records": list(self.records),
            "relative_offset_errors": dict(self.relative_offset_errors),
        }
```

### `src/timesync_sim/ca_engine.py`

```python
from __future__ import annotations

import math
from functools import partial
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QElapsedTimer, QObject, QTimer, Signal

from .constants import (
    CM_UNAVAILABLE_MS,
    CYCLE_MS,
    RESET_COUNTER_MODULUS,
)
from .logic import (
    IntegrityTrace,
    choose_initial_cm,
    compute_local_offsets_from_list,
    evaluate_time_integrity,
)
from .models import (
    CANodeConfig,
    ClockOffsetListMessage,
    DataMessage,
    Endpoint,
    RequestMessage,
    ResponseMessage,
    TopologyConfig,
)
from .network import UdpTransport
from .protocol import ProtocolError, decode_message


class CAEngine(QObject):
    state_changed = Signal(object)
    log_message = Signal(str)
    fatal_error = Signal(str)
    integrity_checked = Signal(object, object)

    def __init__(
        self,
        config: CANodeConfig,
        topology: TopologyConfig,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.config = config
        self.topology = topology
        self.local_endpoint = topology.endpoint_for(config.es_id)
        self.cm_endpoints: Dict[int, Endpoint] = {
            endpoint.es_id: endpoint
            for endpoint in topology.endpoints_by_role("CM")
        }
        self.ca_endpoints: Dict[int, Endpoint] = {
            endpoint.es_id: endpoint
            for endpoint in topology.endpoints_by_role("CA")
        }
        self.remote_ca_ids = sorted(
            ca_id for ca_id in self.ca_endpoints if ca_id != config.es_id
        )
        self.relative_offset_delays: Dict[int, float] = {
            ca_id: parameters.relative_offset_delay
            for ca_id, parameters in topology.ca_parameters.items()
        }

        self.local_clock_offsets: Dict[int, Optional[float]] = {
            ca_id: None for ca_id in self.remote_ca_ids
        }
        self.reset_counter = 0
        self.current_used_clock_list: Optional[ClockOffsetListMessage] = None

        self.selected_cm_es_id: Optional[int] = None
        self.selected_cm_since_ms: Optional[int] = None
        self.last_clock_list_ms: Dict[int, int] = {}
        self.latest_clock_lists: Dict[int, ClockOffsetListMessage] = {}
        self.last_request_timing: Dict[int, Tuple[int, float]] = {}
        self.selected_cycle_anchor_ms: Optional[float] = None

        self.election_started = False
        self.election_finished = False
        self.election_first_cm: Optional[int] = None
        self.election_seen_cms: set[int] = set()
        self.election_timer = QTimer(self)
        self.election_timer.setSingleShot(True)
        self.election_timer.timeout.connect(self._finish_election)

        self.transport = UdpTransport(self.local_endpoint, self)
        self.transport.datagram_received.connect(self._on_datagram)
        self.transport.error_occurred.connect(self.log_message.emit)

        self.elapsed = QElapsedTimer()
        self.tick_timer = QTimer(self)
        self.tick_timer.setInterval(20)
        self.tick_timer.timeout.connect(self._on_tick)
        self.response_timers: List[QTimer] = []
        self.apply_timers: List[QTimer] = []
        self.reset_generation = 0
        self.running = False

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.elapsed.start()
        self.tick_timer.start()
        self.log_message.emit(
            f"CA ES_ID={self.config.es_id} bound to "
            f"{self.local_endpoint.ip}:{self.local_endpoint.port}"
        )
        self._on_tick()

    def stop(self) -> None:
        self.running = False
        self.tick_timer.stop()
        self._cancel_timers(self.response_timers)
        self._cancel_timers(self.apply_timers)

    def update_t2(self, new_t2: float) -> None:
        self.config.t2 = new_t2
        self.log_message.emit(f"T2 changed to {new_t2} ms")
        self.state_changed.emit(self.snapshot())

    def reset(self, new_t2: Optional[float] = None) -> None:
        self.reset_counter = (self.reset_counter + 1) % RESET_COUNTER_MODULUS
        self.local_clock_offsets = {ca_id: None for ca_id in self.remote_ca_ids}
        self.current_used_clock_list = None
        self.reset_generation += 1
        self._cancel_timers(self.response_timers)
        self._cancel_timers(self.apply_timers)
        if new_t2 is not None:
            self.config.t2 = new_t2
        self.log_message.emit(
            f"Reset completed: reset_counter={self.reset_counter}, T2={self.config.t2}"
        )
        self.state_changed.emit(self.snapshot())

    def send_ca_message(
        self,
        receiver_ca_es_id: int,
        transmission_latency: int,
        payload: str = "CA communication test message",
    ) -> None:
        endpoint = self.ca_endpoints.get(receiver_ca_es_id)
        if endpoint is None or receiver_ca_es_id == self.config.es_id:
            raise ValueError(f"Invalid receiver CA ES_ID: {receiver_ca_es_id}")
        message = DataMessage(
            message_type="ca_data",
            sender_ca_es_id=self.config.es_id,
            receiver_ca_es_id=receiver_ca_es_id,
            reset_counter=self.reset_counter,
            transmission_latency=transmission_latency,
            payload=payload,
        )
        self.transport.send(message, endpoint)
        self.log_message.emit(
            f"Sent CA message to {receiver_ca_es_id} with transmission_latency="
            f"{transmission_latency} ms"
        )

    def _on_tick(self) -> None:
        if not self.running:
            return
        self._check_selected_cm_availability()
        self.state_changed.emit(self.snapshot())

    def _on_datagram(self, payload: bytes, sender_ip: str, sender_port: int) -> None:
        try:
            message = decode_message(payload)
        except ProtocolError as exc:
            self.log_message.emit(f"Discarded malformed datagram: {exc}")
            return

        if isinstance(message, RequestMessage):
            self._handle_request(message)
        elif isinstance(message, ClockOffsetListMessage):
            self._handle_clock_offset_list(message)
        elif isinstance(message, DataMessage):
            self._handle_data_message(message)

    def _handle_request(self, message: RequestMessage) -> None:
        endpoint = self.cm_endpoints.get(message.cm_es_id)
        if endpoint is None:
            self.log_message.emit(
                f"Discarded request from unknown CM ES_ID={message.cm_es_id}"
            )
            return

        now_ms = self.elapsed.elapsed()
        self.last_request_timing[message.cm_es_id] = (now_ms, message.t1)

        if not self.election_started:
            self.election_started = True
            self.election_first_cm = message.cm_es_id
            self.election_seen_cms = {message.cm_es_id}
            window_ms = max(0, int(math.ceil(self.config.t2 - message.t1)))
            self.election_timer.start(window_ms)
            self.log_message.emit(
                f"Election window started from CM {message.cm_es_id}; length={window_ms} ms"
            )
        elif not self.election_finished:
            self.election_seen_cms.add(message.cm_es_id)

        if self.selected_cm_es_id == message.cm_es_id:
            self.selected_cycle_anchor_ms = now_ms - message.t1

        delay_ms = max(0, int(math.ceil(self.config.t2 - message.t1)))
        response_timer = QTimer(self)
        response_timer.setSingleShot(True)
        response_timer.timeout.connect(
            partial(self._send_response, message, endpoint, response_timer)
        )
        self.response_timers.append(response_timer)
        response_timer.start(delay_ms)
        self.log_message.emit(
            f"Received request {message.request_number} from CM {message.cm_es_id}; "
            f"response scheduled after {delay_ms} ms"
        )

    def _send_response(
        self,
        request: RequestMessage,
        endpoint: Endpoint,
        timer: QTimer,
    ) -> None:
        self._remove_timer(self.response_timers, timer)
        response = ResponseMessage(
            message_type="response",
            cm_es_id=request.cm_es_id,
            ca_es_id=self.config.es_id,
            request_number=request.request_number,
            t1=request.t1,
            t2=self.config.t2,
            reset_counter=self.reset_counter,
        )
        self.transport.send(response, endpoint)
        self.log_message.emit(
            f"Sent response {request.request_number} to CM {request.cm_es_id}"
        )

    def _finish_election(self) -> None:
        if self.election_finished or self.election_first_cm is None:
            return
        selected = choose_initial_cm(
            self.election_first_cm,
            self.election_seen_cms,
        )
        self.election_finished = True
        self._switch_selected_cm(selected, "initial election")

    def _handle_clock_offset_list(self, message: ClockOffsetListMessage) -> None:
        if message.cm_es_id not in self.cm_endpoints:
            self.log_message.emit(
                f"Discarded clock_offset_list from unknown CM {message.cm_es_id}"
            )
            return
        expected_ca_ids = set(self.ca_endpoints.keys())
        message_ca_ids = {entry.ca_es_id for entry in message.entries}
        if message_ca_ids != expected_ca_ids:
            self.log_message.emit(
                f"Discarded structurally invalid clock_offset_list {message.request_number}: "
                "CA ES_ID set does not match topology"
            )
            return

        now_ms = self.elapsed.elapsed()
        self.last_clock_list_ms[message.cm_es_id] = now_ms
        self.latest_clock_lists[message.cm_es_id] = message

        if message.cm_es_id != self.selected_cm_es_id:
            self.log_message.emit(
                f"Stored clock_offset_list {message.request_number} from non-selected "
                f"CM {message.cm_es_id}"
            )
            return

        self._schedule_selected_clock_list(message)

    def _schedule_selected_clock_list(self, message: ClockOffsetListMessage) -> None:
        local_entry = message.entry_for(self.config.es_id)
        if local_entry is None or local_entry.reset_counter != self.reset_counter:
            self.log_message.emit(
                f"Rejected clock_offset_list {message.request_number}: local reset_counter "
                f"{self.reset_counter} != list value "
                f"{None if local_entry is None else local_entry.reset_counter}"
            )
            return

        computed_offsets = compute_local_offsets_from_list(
            message,
            self.config.es_id,
            self.relative_offset_delays,
        )
        generation = self.reset_generation
        selected_cm = self.selected_cm_es_id
        delay_to_boundary = self._delay_to_next_selected_cycle_boundary()
        apply_timer = QTimer(self)
        apply_timer.setSingleShot(True)
        apply_timer.timeout.connect(
            partial(
                self._apply_clock_list,
                message,
                computed_offsets,
                generation,
                selected_cm,
                apply_timer,
            )
        )
        self.apply_timers.append(apply_timer)
        apply_timer.start(delay_to_boundary)
        self.log_message.emit(
            f"Accepted clock_offset_list {message.request_number}; local offsets will "
            f"become effective after {delay_to_boundary} ms"
        )

    def _apply_clock_list(
        self,
        message: ClockOffsetListMessage,
        computed_offsets: Dict[int, Optional[float]],
        generation: int,
        selected_cm: Optional[int],
        timer: QTimer,
    ) -> None:
        self._remove_timer(self.apply_timers, timer)
        if generation != self.reset_generation:
            return
        if selected_cm != self.selected_cm_es_id:
            return
        self.local_clock_offsets = dict(computed_offsets)
        self.current_used_clock_list = message
        self.log_message.emit(
            f"local_clock_offset from CM {message.cm_es_id}, list "
            f"{message.request_number}, is now effective"
        )
        self.state_changed.emit(self.snapshot())

    def _handle_data_message(self, message: DataMessage) -> None:
        if message.receiver_ca_es_id != self.config.es_id:
            return
        if message.sender_ca_es_id not in self.remote_ca_ids:
            self.log_message.emit(
                f"Discarded CA data from unknown/non-remote CA {message.sender_ca_es_id}"
            )
            return

        local_offset = self.local_clock_offsets.get(message.sender_ca_es_id)
        list_counter: Optional[int] = None
        if self.current_used_clock_list is not None:
            sender_entry = self.current_used_clock_list.entry_for(message.sender_ca_es_id)
            if sender_entry is not None:
                list_counter = sender_entry.reset_counter

        trace = evaluate_time_integrity(
            dmax=self.config.dmax,
            local_clock_offset=local_offset,
            message_reset_counter=message.reset_counter,
            list_reset_counter=list_counter,
            transmission_latency=message.transmission_latency,
        )
        self.log_message.emit(
            f"CA message from {message.sender_ca_es_id}: "
            f"{'PASS' if trace.accepted else 'DISCARD'} ({trace.reason})"
        )
        self.integrity_checked.emit(message, trace)

    def _check_selected_cm_availability(self) -> None:
        if not self.election_finished or self.selected_cm_es_id is None:
            return
        now_ms = self.elapsed.elapsed()
        last_list = self.last_clock_list_ms.get(self.selected_cm_es_id)
        reference = last_list
        if reference is None:
            reference = self.selected_cm_since_ms
        if reference is None or now_ms - reference < CM_UNAVAILABLE_MS:
            return

        available = sorted(
            cm_id
            for cm_id, timestamp in self.last_clock_list_ms.items()
            if now_ms - timestamp < CM_UNAVAILABLE_MS
        )
        if available:
            candidate = available[0]
            if candidate != self.selected_cm_es_id:
                self._switch_selected_cm(candidate, "current CM unavailable")

    def _switch_selected_cm(self, cm_es_id: int, reason: str) -> None:
        if cm_es_id == self.selected_cm_es_id:
            return
        self.selected_cm_es_id = cm_es_id
        self.selected_cm_since_ms = self.elapsed.elapsed()
        timing = self.last_request_timing.get(cm_es_id)
        if timing is not None:
            received_ms, t1 = timing
            self.selected_cycle_anchor_ms = received_ms - t1
        else:
            self.selected_cycle_anchor_ms = None

        self.local_clock_offsets = {ca_id: None for ca_id in self.remote_ca_ids}
        self.current_used_clock_list = None
        self._cancel_timers(self.apply_timers)
        self.log_message.emit(f"Selected CM changed to {cm_es_id}: {reason}")

        cached = self.latest_clock_lists.get(cm_es_id)
        if cached is not None:
            self._schedule_selected_clock_list(cached)

    def _delay_to_next_selected_cycle_boundary(self) -> int:
        if self.selected_cycle_anchor_ms is None:
            return CYCLE_MS
        now_ms = self.elapsed.elapsed()
        phase = (now_ms - self.selected_cycle_anchor_ms) % CYCLE_MS
        delay = CYCLE_MS - phase
        return max(1, int(math.ceil(delay)))

    def _display_phase_ms(self) -> int:
        if self.selected_cycle_anchor_ms is None:
            return self.elapsed.elapsed() % CYCLE_MS if self.elapsed.isValid() else 0
        return int((self.elapsed.elapsed() - self.selected_cycle_anchor_ms) % CYCLE_MS)

    def snapshot(self) -> Dict[str, object]:
        return {
            "es_id": self.config.es_id,
            "phase_ms": self._display_phase_ms(),
            "selected_cm_es_id": self.selected_cm_es_id,
            "source_request_number": (
                None
                if self.current_used_clock_list is None
                else self.current_used_clock_list.request_number
            ),
            "local_clock_offsets": dict(self.local_clock_offsets),
            "reset_counter": self.reset_counter,
            "t2": self.config.t2,
            "dmax": self.config.dmax,
            "election_finished": self.election_finished,
        }

    @staticmethod
    def _remove_timer(timers: List[QTimer], timer: QTimer) -> None:
        if timer in timers:
            timers.remove(timer)
        timer.deleteLater()

    @staticmethod
    def _cancel_timers(timers: List[QTimer]) -> None:
        for timer in list(timers):
            timer.stop()
            timer.deleteLater()
        timers.clear()
```

### `src/timesync_sim/gui/__init__.py`

```python
"""Qt Widgets user interfaces."""
```

### `src/timesync_sim/gui/common.py`

```python
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget


def choose_json_configuration(
    parent: Optional[QWidget],
    title: str,
    initial_directory: Optional[str] = None,
) -> Optional[str]:
    directory = initial_directory or str(Path.cwd())
    path, _ = QFileDialog.getOpenFileName(
        parent,
        title,
        directory,
        "JSON configuration (*.json);;All files (*)",
    )
    if not path:
        return None
    answer = QMessageBox.question(
        parent,
        "Confirm configuration",
        f"Use this configuration?\n\n{path}",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.Yes,
    )
    if answer != QMessageBox.StandardButton.Yes:
        return None
    return path


def format_optional_number(value: object, decimals: int = 3) -> str:
    if value is None:
        return "Unknown"
    if isinstance(value, (int, float)):
        return f"{float(value):.{decimals}f}"
    return str(value)
```

### `src/timesync_sim/gui/cm_window.py`

```python
from __future__ import annotations

from typing import Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..cm_engine import CMEngine, CMRequestRecord
from ..constants import CYCLE_MS
from ..models import ClockOffsetListMessage
from .common import format_optional_number


class CMWindow(QMainWindow):
    def __init__(self, engine: CMEngine) -> None:
        super().__init__()
        self.engine = engine
        self.setWindowTitle(f"Clock Manager - ES_ID {engine.config.es_id}")
        self.resize(880, 680)

        central = QWidget(self)
        root = QVBoxLayout(central)

        heading = QLabel(
            f"Clock Manager (CM) | ES_ID={engine.config.es_id} | "
            f"T1={engine.config.t1} ms | E1={engine.config.e1} ms"
        )
        heading.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        root.addWidget(heading)

        self.phase_label = QLabel("Cycle phase: 0 ms")
        self.phase_bar = QProgressBar()
        self.phase_bar.setRange(0, CYCLE_MS - 1)
        self.phase_bar.setTextVisible(True)
        root.addWidget(self.phase_label)
        root.addWidget(self.phase_bar)

        requests_group = QGroupBox("Last two sent request_numbers")
        self.requests_layout = QHBoxLayout(requests_group)
        root.addWidget(requests_group)

        list_group = QGroupBox("clock_offset_list")
        list_layout = QVBoxLayout(list_group)
        self.list_title = QLabel("Select a completed request_number.")
        list_layout.addWidget(self.list_title)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            [
                "CA_ES_ID",
                "CA_relative_offset",
                "CA_reset_counter",
                "CA_relative_offset_error",
            ]
        )
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        list_layout.addWidget(self.table)
        root.addWidget(list_group, 1)

        log_group = QGroupBox("Runtime log")
        log_layout = QVBoxLayout(log_group)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(160)
        log_layout.addWidget(self.log_view)
        root.addWidget(log_group)

        self.setCentralWidget(central)
        self.engine.state_changed.connect(self._update_state)
        self.engine.log_message.connect(self._append_log)

    def closeEvent(self, event: object) -> None:
        self.engine.stop()
        super().closeEvent(event)  # type: ignore[arg-type]

    def _update_state(self, state: Dict[str, object]) -> None:
        phase = int(state["phase_ms"])
        self.phase_label.setText(f"Cycle phase: {phase} ms / 1000 ms")
        self.phase_bar.setValue(phase)
        self.phase_bar.setFormat(f"{phase} ms")
        records = state.get("records", [])
        self._rebuild_request_buttons(records)  # type: ignore[arg-type]

    def _rebuild_request_buttons(self, records: list[CMRequestRecord]) -> None:
        while self.requests_layout.count():
            item = self.requests_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if not records:
            self.requests_layout.addWidget(QLabel("No request sent yet."))
            return

        for record in records:
            status = "complete" if record.completed else "calculating"
            button = QPushButton(f"{record.request_number}\n{status}")
            button.setMinimumWidth(150)
            button.setEnabled(record.completed and record.clock_offset_list is not None)
            if record.clock_offset_list is not None:
                button.clicked.connect(
                    lambda checked=False, message=record.clock_offset_list: self._show_clock_list(
                        message
                    )
                )
            self.requests_layout.addWidget(button)
        self.requests_layout.addStretch(1)

    def _show_clock_list(self, message: ClockOffsetListMessage) -> None:
        self.list_title.setText(
            f"CM_ES_ID={message.cm_es_id}, request_number={message.request_number}, "
            f"number_of_CAs={message.number_of_ca}"
        )
        self.table.setRowCount(len(message.entries))
        for row, entry in enumerate(message.entries):
            values = [
                str(entry.ca_es_id),
                format_optional_number(entry.relative_offset),
                "Unknown" if entry.reset_counter is None else str(entry.reset_counter),
                format_optional_number(entry.relative_offset_error),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                )
                self.table.setItem(row, column, item)
        self.table.resizeColumnsToContents()

    def _append_log(self, message: str) -> None:
        self.log_view.append(message)
```

### `src/timesync_sim/gui/ca_window.py`

```python
from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QComboBox,
)

from ..ca_engine import CAEngine
from ..constants import CYCLE_MS
from ..logic import IntegrityTrace
from ..models import DataMessage
from .common import format_optional_number
from .integrity_dialog import IntegrityDialog


class SendMessageDialog(QDialog):
    def __init__(self, receiver_ids: List[int], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Send CA message")
        layout = QFormLayout(self)
        self.receiver_combo = QComboBox()
        for es_id in receiver_ids:
            self.receiver_combo.addItem(str(es_id), es_id)
        self.latency_spin = QSpinBox()
        self.latency_spin.setRange(0, 2_147_483_647)
        self.latency_spin.setSuffix(" ms")
        self.payload_edit = QLineEdit("CA communication test message")
        layout.addRow("receiver_CA ES_ID", self.receiver_combo)
        layout.addRow("transmission_latency", self.latency_spin)
        layout.addRow("payload", self.payload_edit)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def values(self) -> tuple[int, int, str]:
        return (
            int(self.receiver_combo.currentData()),
            self.latency_spin.value(),
            self.payload_edit.text(),
        )


class CAWindow(QMainWindow):
    def __init__(self, engine: CAEngine) -> None:
        super().__init__()
        self.engine = engine
        self.integrity_dialogs: List[IntegrityDialog] = []
        self.setWindowTitle(f"Clock Agent - ES_ID {engine.config.es_id}")
        self.resize(820, 700)

        central = QWidget(self)
        root = QVBoxLayout(central)

        heading = QLabel(
            f"Clock Agent (CA) | ES_ID={engine.config.es_id} | "
            f"T2={engine.config.t2} ms | Dmax={engine.config.dmax} ms"
        )
        heading.setObjectName("heading")
        root.addWidget(heading)
        self.heading = heading

        self.phase_label = QLabel("Selected-CM cycle phase: 0 ms")
        self.phase_bar = QProgressBar()
        self.phase_bar.setRange(0, CYCLE_MS - 1)
        root.addWidget(self.phase_label)
        root.addWidget(self.phase_bar)

        self.source_label = QLabel("Current data source: election pending")
        self.source_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        root.addWidget(self.source_label)

        status_group = QGroupBox("CA state")
        status_layout = QHBoxLayout(status_group)
        self.reset_counter_label = QLabel("reset_counter: 0")
        self.t2_label = QLabel(f"T2: {engine.config.t2} ms")
        status_layout.addWidget(self.reset_counter_label)
        status_layout.addWidget(self.t2_label)
        status_layout.addStretch(1)
        root.addWidget(status_group)

        offsets_group = QGroupBox("local_clock_offset")
        offsets_layout = QVBoxLayout(offsets_group)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["remote_ES_ID", "local_clock_offset"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        offsets_layout.addWidget(self.table)
        root.addWidget(offsets_group, 1)

        button_layout = QHBoxLayout()
        self.reset_button = QPushButton("Reset")
        self.send_button = QPushButton("Send message")
        self.reset_button.clicked.connect(self._reset)
        self.send_button.clicked.connect(self._send_message)
        button_layout.addWidget(self.reset_button)
        button_layout.addWidget(self.send_button)
        button_layout.addStretch(1)
        root.addLayout(button_layout)

        log_group = QGroupBox("Runtime log")
        log_layout = QVBoxLayout(log_group)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(170)
        log_layout.addWidget(self.log_view)
        root.addWidget(log_group)

        self.setCentralWidget(central)
        self.engine.state_changed.connect(self._update_state)
        self.engine.log_message.connect(self._append_log)
        self.engine.integrity_checked.connect(self._show_integrity_dialog)

    def closeEvent(self, event: object) -> None:
        self.engine.stop()
        super().closeEvent(event)  # type: ignore[arg-type]

    def _update_state(self, state: Dict[str, object]) -> None:
        phase = int(state["phase_ms"])
        self.phase_label.setText(f"Selected-CM cycle phase: {phase} ms / 1000 ms")
        self.phase_bar.setValue(phase)
        self.phase_bar.setFormat(f"{phase} ms")

        selected = state["selected_cm_es_id"]
        request_number = state["source_request_number"]
        if selected is None:
            self.source_label.setText("Current data source: election pending")
        elif request_number is None:
            self.source_label.setText(
                f"Current data source: CM {selected}; no effective clock_offset_list"
            )
        else:
            self.source_label.setText(
                f"Current data source: CM {selected}, clock_offset_list "
                f"request_number={request_number}"
            )

        self.reset_counter_label.setText(
            f"reset_counter: {state['reset_counter']}"
        )
        self.t2_label.setText(f"T2: {state['t2']} ms")
        self.heading.setText(
            f"Clock Agent (CA) | ES_ID={self.engine.config.es_id} | "
            f"T2={state['t2']} ms | Dmax={state['dmax']} ms"
        )
        offsets = state["local_clock_offsets"]
        self._update_offsets(offsets)  # type: ignore[arg-type]

    def _update_offsets(self, offsets: Dict[int, object]) -> None:
        rows = sorted(offsets.items())
        self.table.setRowCount(len(rows))
        for row, (remote_id, offset) in enumerate(rows):
            values = [str(remote_id), format_optional_number(offset)]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                )
                self.table.setItem(row, column, item)
        self.table.resizeColumnsToContents()

    def _reset(self) -> None:
        self.engine.reset()
        value, accepted = QInputDialog.getDouble(
            self,
            "Change T2 after reset",
            "New T2 (ms). Cancel keeps the current value:",
            self.engine.config.t2,
            -1_000_000_000.0,
            1_000_000_000.0,
            3,
        )
        if accepted:
            self.engine.update_t2(value)

    def _send_message(self) -> None:
        if not self.engine.remote_ca_ids:
            QMessageBox.information(self, "No receiver", "No remote CA exists in topology.")
            return
        dialog = SendMessageDialog(self.engine.remote_ca_ids, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        receiver_id, latency, payload = dialog.values()
        try:
            self.engine.send_ca_message(receiver_id, latency, payload)
        except ValueError as exc:
            QMessageBox.critical(self, "Send failed", str(exc))

    def _show_integrity_dialog(
        self,
        message: DataMessage,
        trace: IntegrityTrace,
    ) -> None:
        dialog = IntegrityDialog(message, trace, self)
        offset = 30 * (len(self.integrity_dialogs) % 6)
        dialog.move(self.pos() + QPoint(self.width() + 20 + offset, offset))
        dialog.destroyed.connect(
            lambda _object=None, current=dialog: self._remove_dialog(current)
        )
        self.integrity_dialogs.append(dialog)
        dialog.show()
        dialog.raise_()

    def _remove_dialog(self, dialog: IntegrityDialog) -> None:
        if dialog in self.integrity_dialogs:
            self.integrity_dialogs.remove(dialog)

    def _append_log(self, message: str) -> None:
        self.log_view.append(message)
```

### `src/timesync_sim/gui/integrity_dialog.py`

```python
from __future__ import annotations

from typing import Dict, Optional, Set, Tuple

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout, QWidget

from ..logic import IntegrityTrace
from ..models import DataMessage


class IntegrityFlowWidget(QWidget):
    def __init__(self, trace: IntegrityTrace, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.trace = trace
        self.setMinimumSize(820, 560)

    def paintEvent(self, event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("white"))

        nodes: Dict[str, Tuple[QRectF, str]] = {
            "start": (QRectF(330, 15, 160, 45), "Receive CA message"),
            "dmax_zero": (QRectF(300, 90, 220, 60), "Dmax == 0?"),
            "offset_unknown": (
                QRectF(300, 190, 220, 60),
                "local_clock_offset\nUnknown?",
            ),
            "counter_equal": (
                QRectF(300, 290, 220, 60),
                "reset_counter equal?",
            ),
            "age_valid": (QRectF(300, 390, 220, 60), "0 < age < Dmax?"),
            "result_pass": (QRectF(620, 240, 150, 60), "PASS"),
            "result_discard": (QRectF(620, 390, 150, 60), "DISCARD"),
        }
        edges = [
            ("start", "dmax_zero", ""),
            ("dmax_zero", "result_pass", "Yes"),
            ("dmax_zero", "offset_unknown", "No"),
            ("offset_unknown", "result_pass", "Yes"),
            ("offset_unknown", "counter_equal", "No"),
            ("counter_equal", "age_valid", "Yes"),
            ("counter_equal", "result_discard", "No"),
            ("age_valid", "result_pass", "Yes"),
            ("age_valid", "result_discard", "No"),
        ]

        traversed: Set[str] = {"start"}
        traversed.update(step.key for step in self.trace.steps)
        traversed_edges = self._traversed_edges()

        for source, target, label in edges:
            active = (source, target) in traversed_edges
            self._draw_edge(painter, nodes[source][0], nodes[target][0], label, active)

        for key, (rect, text) in nodes.items():
            self._draw_node(painter, rect, text, key in traversed, key)

    def _traversed_edges(self) -> Set[Tuple[str, str]]:
        keys = ["start"] + [step.key for step in self.trace.steps]
        edges: Set[Tuple[str, str]] = set()
        for source, target in zip(keys, keys[1:]):
            edges.add((source, target))
        return edges

    @staticmethod
    def _draw_node(
        painter: QPainter,
        rect: QRectF,
        text: str,
        active: bool,
        key: str,
    ) -> None:
        if active:
            fill = QColor("#d7f5dd") if "discard" not in key else QColor("#ffd9d9")
            border = QColor("#187a2f") if "discard" not in key else QColor("#a11313")
        else:
            fill = QColor("#f2f2f2")
            border = QColor("#888888")
        painter.setPen(QPen(border, 2 if active else 1))
        painter.setBrush(fill)
        if key in {"dmax_zero", "offset_unknown", "counter_equal", "age_valid"}:
            painter.drawRoundedRect(rect, 18, 18)
        else:
            painter.drawRoundedRect(rect, 8, 8)
        painter.setPen(QPen(QColor("black"), 1))
        font = QFont()
        font.setBold(active)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    @staticmethod
    def _draw_edge(
        painter: QPainter,
        source: QRectF,
        target: QRectF,
        label: str,
        active: bool,
    ) -> None:
        pen = QPen(QColor("#1667a8") if active else QColor("#aaaaaa"), 3 if active else 1)
        painter.setPen(pen)
        start = QPointF(source.center().x(), source.bottom())
        end = QPointF(target.center().x(), target.top())
        if target.left() > source.right():
            start = QPointF(source.right(), source.center().y())
            end = QPointF(target.left(), target.center().y())
        painter.drawLine(start, end)

        direction = end - start
        length = max(1.0, (direction.x() ** 2 + direction.y() ** 2) ** 0.5)
        ux, uy = direction.x() / length, direction.y() / length
        left = QPointF(end.x() - 10 * ux + 5 * uy, end.y() - 10 * uy - 5 * ux)
        right = QPointF(end.x() - 10 * ux - 5 * uy, end.y() - 10 * uy + 5 * ux)
        painter.drawLine(end, left)
        painter.drawLine(end, right)
        if label:
            midpoint = QPointF((start.x() + end.x()) / 2, (start.y() + end.y()) / 2)
            painter.drawText(midpoint + QPointF(5, -5), label)


class IntegrityDialog(QDialog):
    def __init__(
        self,
        message: DataMessage,
        trace: IntegrityTrace,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setWindowTitle(
            f"Time Integrity Check: CA {message.sender_ca_es_id} -> "
            f"CA {message.receiver_ca_es_id}"
        )
        self.resize(850, 680)
        layout = QVBoxLayout(self)
        summary = QLabel(
            f"sender={message.sender_ca_es_id}, receiver={message.receiver_ca_es_id}, "
            f"message reset_counter={message.reset_counter}, "
            f"transmission_latency/age={message.transmission_latency} ms\n"
            f"Result: {'PASS' if trace.accepted else 'DISCARD'} — {trace.reason}"
        )
        summary.setWordWrap(True)
        summary.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(summary)
        layout.addWidget(IntegrityFlowWidget(trace, self), 1)
```

### `tests/conftest.py`

```python
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
```

### `tests/test_config.py`

```python
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
```

### `tests/test_logic.py`

```python
from __future__ import annotations

from timesync_sim.logic import (
    choose_cm_after_timeout,
    choose_initial_cm,
    evaluate_time_integrity,
)


def test_initial_election_chooses_smallest_seen_cm() -> None:
    assert choose_initial_cm(8, {8, 3, 5}) == 3


def test_failover_keeps_available_current_cm() -> None:
    assert choose_cm_after_timeout(5, {3: 9500, 5: 9000}, 10000) == 5


def test_failover_chooses_smallest_available_cm() -> None:
    assert choose_cm_after_timeout(5, {3: 9500, 5: 7000, 8: 9800}, 10000) == 3


def test_integrity_dmax_zero_passes() -> None:
    trace = evaluate_time_integrity(0, 12.0, 4, 3, 999)
    assert trace.accepted


def test_integrity_unknown_offset_passes() -> None:
    trace = evaluate_time_integrity(50, None, 4, 3, 999)
    assert trace.accepted


def test_integrity_counter_mismatch_discards() -> None:
    trace = evaluate_time_integrity(50, 12.0, 4, 3, 10)
    assert not trace.accepted


def test_integrity_age_interval_is_strict() -> None:
    assert evaluate_time_integrity(50, 12.0, 4, 4, 1).accepted
    assert evaluate_time_integrity(50, 12.0, 4, 4, 49).accepted
    assert not evaluate_time_integrity(50, 12.0, 4, 4, 0).accepted
    assert not evaluate_time_integrity(50, 12.0, 4, 4, 50).accepted
```

### `tests/test_math_utils.py`

```python
from __future__ import annotations

from timesync_sim.math_utils import (
    calculate_local_clock_offset,
    calculate_relative_offset_error,
    round_half_up_3,
)


def test_round_half_up_3() -> None:
    assert round_half_up_3(1.2345) == 1.235
    assert round_half_up_3(1.2344) == 1.234


def test_relative_offset_error_formula() -> None:
    result = calculate_relative_offset_error(
        clock_drift_rate=0.00001,
        e1=0.1,
        l2=0.25,
    )
    assert result == 0.38


def test_local_clock_offset_formula() -> None:
    result = calculate_local_clock_offset(
        remote_relative_offset=220.0,
        local_relative_offset=200.0,
        remote_relative_offset_error=0.66,
        local_relative_offset_error=0.38,
        remote_delay=2.0,
        local_delay=1.5,
    )
    assert result == 22.28


def test_local_clock_offset_unknown_propagates() -> None:
    assert (
        calculate_local_clock_offset(
            remote_relative_offset=None,
            local_relative_offset=200.0,
            remote_relative_offset_error=0.66,
            local_relative_offset_error=0.38,
            remote_delay=2.0,
            local_delay=1.5,
        )
        is None
    )
```

### `tests/test_protocol.py`

```python
from __future__ import annotations

import pytest

from timesync_sim.models import (
    ClockOffsetEntry,
    ClockOffsetListMessage,
    DataMessage,
    RequestMessage,
)
from timesync_sim.protocol import ProtocolError, decode_message, encode_message


def test_request_round_trip() -> None:
    original = RequestMessage(
        message_type="request",
        cm_es_id=1,
        request_number=42,
        t1=100.0,
    )
    decoded = decode_message(encode_message(original))
    assert decoded == original


def test_none_is_serialized_as_json_null() -> None:
    message = ClockOffsetListMessage(
        message_type="clock_offset_list",
        cm_es_id=1,
        request_number=7,
        number_of_ca=1,
        entries=[
            ClockOffsetEntry(
                ca_es_id=101,
                relative_offset=None,
                reset_counter=None,
                relative_offset_error=0.38,
            )
        ],
    )
    encoded = encode_message(message)
    assert b'"relative_offset":null' in encoded
    assert b'"reset_counter":null' in encoded
    assert decode_message(encoded) == message


def test_invalid_message_type_is_rejected() -> None:
    with pytest.raises(ProtocolError):
        decode_message(b'{"message_type":"not_supported"}')
```

## 4. 当前实现限制和可能需要人工确认的需求歧义

- Windows timer scheduling and Qt event-loop latency can shift an action by several milliseconds. Logical timestamps remain fixed, but the 500 ms and 2000 ms decisions use real process time.
- Separate CM processes are not started from a shared global epoch. A CA derives the selected CM cycle phase from request receipt time minus that request T1.
- UDP remains unreliable and unordered. No retransmission or acknowledgement layer is added.
- A virtual link is represented as direct UDP unicast. BAG, switch routing, bandwidth policing, redundancy, and AFDX frame behavior are outside this implementation.
- T1 and T2 ranges and T1 < T2 are intentionally not validated. Negative response or election delays are clamped to zero because Qt cannot schedule a negative timer.
- Fractional timer delays are rounded upward to an integer millisecond. Message calculations retain configured numeric values.
- A failover can use the most recent cached list from the newly selected CM and makes its result effective at the next inferred cycle boundary.
- Switching CM clears the old effective list and local offsets before the new source becomes effective. This is an implementation choice to prevent stale values from being attributed to a new source.
- Reset cancels scheduled responses and pending local-offset applications. CA data messages are sent immediately, so there is no queued CA data message to cancel.
- Datagram sender IP/port is not cryptographically authenticated. Structural fields, IDs, roles, and destinations are validated.
- The GUI displays numeric values to three decimal places. Only relative_offset_error is explicitly quantized with ROUND_HALF_UP; local offset arithmetic is not forcibly quantized.
- clock_drift_rate does not create a physically drifting clock. It is used only in relative_offset_error.
- The precise interpretation of “CM generation occupies the entire 500–1000 ms interval” is implemented as deferred publication: the result becomes externally usable only at the 1000 ms boundary, without deliberately consuming CPU for 500 ms.
- Requests, responses, and clock_offset_list messages bypass the CA data time-integrity flow, which is equivalent to treating their Dmax as zero.
- The supplied execution environment did not contain Qt, so GUI startup was not executed there. All Python files passed a Python 3.9 grammar parse and compile check; 17 non-GUI tests passed.

# Complete Project Output
本文件根据压缩包中的当前实际文件重新生成，用于集中查看完整项目。生成日期：2026-08-07。
不包含 `.pytest_cache/` 等运行缓存，也不嵌入 `COMPLETE_PROJECT.md` 自身，以避免递归。
## 1. 当前实现摘要
- 每个 CM/CA 是独立的 PySide6 进程，通过 topology 中的 UDP endpoint 通信。
- CM 以本地单调时钟运行 1000 ms 周期，在 T1 发送 request 和上一周期完成的 clock-offset list。
- CA 完成初始 CM 选举、2000 ms 不可用判定、列表缓存与 failover。
- local clock offset 在 selected-CM 下一个周期边界生效，超过 1000 ms 无有效更新后置为 Unknown。
- CA reset 会清除同步状态并取消未发送 response/未生效 list，但不会取消 receiver-side latency timer，也不会删除等待 probe handshake 的发送消息。
- CA data 的字段在点击 Send 时固定；receiver 收到 datagram 后独立等待 transmission_latency，到期时读取 receiver 最新状态并做 integrity check。
- `probe_enabled` 控制该 CA 是否主动发送 CM transport probe 和 CA peer probe；未就绪的 peer route 可使 data message 排队至握手完成。
- 当前共有 20 个测试，其中 3 个依赖 PySide6/Qt event loop。

## 2. 完整目录结构

```text
HITP simulation v2_副本/
├── README.md
├── COMPLETE_PROJECT.md
├── requirements.txt
├── pytest.ini
├── setup_env.sh
├── run_all_demo.sh
├── run_cm.py
├── run_ca.py
├── configs/
│   ├── ca_101.json
│   ├── ca_102.json
│   ├── cm_1.json
│   ├── cm_2.json
│   ├── topology-hotspot.json
│   ├── topology-local.json
│   └── topology.json
├── src/
│   └── timesync_sim/
│       ├── __init__.py
│       ├── ca_engine.py
│       ├── cm_engine.py
│       ├── config.py
│       ├── constants.py
│       ├── logic.py
│       ├── math_utils.py
│       ├── models.py
│       ├── network.py
│       ├── protocol.py
│       └── gui/
│           ├── __init__.py
│           ├── ca_window.py
│           ├── cm_window.py
│           ├── common.py
│           └── integrity_dialog.py
└── tests/
    ├── conftest.py
    ├── test_ca_message_latency.py
    ├── test_config.py
    ├── test_logic.py
    ├── test_math_utils.py
    └── test_protocol.py
```

## 3. 完整文件内容

### `README.md`

````markdown
# Time Synchronization + CA Communication Simulator

A Python/PySide6 simulator in which every Clock Manager (CM) and Clock Agent (CA) runs as a separate process. The processes exchange strict JSON protocol messages over UDP endpoints declared in a topology file.

The current implementation includes CM/CA time synchronization, CM election and failover, CA reset handling, optional UDP probe compatibility mode, CA-to-CA time-integrity checking, and receiver-side simulated transmission latency.

## 1. Project structure

```text
HITP simulation v2_副本/
├── README.md
├── COMPLETE_PROJECT.md
├── requirements.txt
├── pytest.ini
├── setup_env.sh
├── run_all_demo.sh
├── run_cm.py
├── run_ca.py
├── configs/
│   ├── topology.json
│   ├── topology-local.json
│   ├── topology-hotspot.json
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
    ├── test_protocol.py
    └── test_ca_message_latency.py
```

Generated caches such as `.pytest_cache/` are not part of the project source.

## 2. Environment setup

Dependencies are pinned in `requirements.txt`:

```text
PySide6-Essentials==6.8.3
pydantic==2.10.6
pytest==8.3.5
```

### macOS/Linux shell

The supplied setup script currently invokes `python3.13`:

```bash
cd "/path/to/HITP simulation v2_副本"
chmod +x setup_env.sh run_all_demo.sh
./setup_env.sh
```

Equivalent manual setup:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pytest
```

### Windows CMD

There is no `.cmd` setup script in the current archive. Use the equivalent commands:

```bat
cd /d C:\path\to\HITP simulation v2_副本
py -3.13 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pytest
```

If the exact `3.13` launcher name is unavailable, use a Python installation compatible with the pinned packages and replace the interpreter command accordingly.

## 3. Running the simulator

### Run one process manually

macOS/Linux:

```bash
source .venv/bin/activate
python run_cm.py configs/cm_1.json
python run_ca.py configs/ca_101.json
```

Windows CMD:

```bat
call .venv\Scripts\activate.bat
python run_cm.py configs\cm_1.json
python run_ca.py configs\ca_101.json
```

Running either launcher without a path opens a JSON file-selection and confirmation dialog:

```bash
python run_cm.py
python run_ca.py
```

Each process binds its configured UDP port on `0.0.0.0`/AnyIPv4. The topology IP is the address advertised to other ES processes. Each ES must have a unique `ES_ID`, and every topology endpoint must have a unique IP/port pair.

### Supplied demo script

```bash
./run_all_demo.sh
```

The current script starts:

- CM 1 with `configs/cm_1.json`
- CM 2 with `configs/cm_2.json`
- CA 101 with `configs/ca_101.json`

The CA 102 command is currently commented out in `run_all_demo.sh`. Uncomment it to start all four supplied processes.

## 4. Configuration

### CM node configuration

```json
{
  "role": "CM",
  "es_id": 1,
  "t1": 100.0,
  "e1": 0.1,
  "topology_path": "topology.json"
}
```

- `es_id`: non-negative ES identifier.
- `t1`: configured request timestamp/phase in milliseconds. Its range is intentionally not validated.
- `e1`: lead error in milliseconds, in `[0, 655.35]`; default `0`.
- `topology_path`: resolved relative to the node JSON file.

### CA node configuration

```json
{
  "role": "CA",
  "es_id": 101,
  "t2": 300.0,
  "dmax": 50.0,
  "topology_path": "topology.json",
  "probe_enabled": false
}
```

- `es_id`: non-negative ES identifier.
- `t2`: configured response timestamp in milliseconds. Its range is intentionally not validated.
- `dmax`: non-negative time-integrity threshold in milliseconds.
- `probe_enabled`: simulation-only transport compatibility switch; strict Boolean; defaults to `false`.

### Topology configuration

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

Topology validation rejects:

- duplicate `ES_ID` values;
- duplicate IP/port pairs;
- missing CA parameter entries;
- CA parameters belonging to non-CA endpoints;
- a node JSON whose role does not match its topology endpoint.

The supplied topology variants are:

- `topology-local.json`: all four ES processes on localhost;
- `topology-hotspot.json`: supplied hotspot addresses;
- `topology.json`: supplied cross-host addresses currently referenced by all node JSON files.

To select another topology, change `topology_path` in each relevant node configuration.

## 5. Protocol messages

All datagrams are UTF-8 JSON and use `protocol_version = 1`. Pydantic models reject unknown fields.

Implemented message types:

- `request`
- `response`
- `clock_offset_list`
- `transport_probe`
- `ca_peer_probe`
- `ca_peer_ack`
- `ca_data`

`None` is serialized as JSON `null` and displayed as `Unknown` in the GUI.

## 6. CM cycle and clock-offset-list behavior

- Each CM uses its own monotonic 1000 ms cycle.
- The CM event loop is checked every 10 ms.
- At phase `T1`, the CM sends the current `request` to every CA.
- In the same event-loop iteration, it also sends the previously completed `clock_offset_list`, if one exists.
- The first request has no previous list to send.
- `request_number = cycle_index mod 65536`.
- A CA schedules its response after `ceil(max(0, T2 - request.T1))` milliseconds.
- The response carries the CA's `T2` and `reset_counter` values at the time the response timer expires.
- The CM only accepts a response for its current request number and only when the CM cycle phase is at most 500 ms.
- For an accepted response:

```text
relative_offset = T2 - T1
```

- If no accepted response exists for a CA, that list entry's `relative_offset` is `Unknown`; the most recently received reset counter for that CA is retained.
- The current cycle's list is finalized at the next 1000 ms boundary and becomes the list sent at the following `T1`.
- The CM GUI retains two fixed request buttons to avoid UI flicker. A completed request button opens its list.

The CM calculates each CA's relative-offset error once from configuration:

```text
relative_offset_error = round_half_up_0.001(
    3000 * clock_drift_rate + E1 + L2
)
```

## 7. CA election, list application, and local offsets

### Initial CM election

- The first valid request starts the election window.
- Window length is `ceil(max(0, T2 - first_request.T1))` milliseconds.
- The smallest CM `ES_ID` observed during that window is selected.
- A lower-ID CM appearing after the initial election does not proactively replace an available selected CM.

### CM availability and failover

- A selected CM is treated as unavailable when no clock-offset list has been received from it for at least 2000 ms.
- If the selected CM has never supplied a list, time since selection is used.
- Failover chooses the smallest CM `ES_ID` whose list is newer than 2000 ms.
- Recovery of a higher-priority CM does not replace the currently available CM.

### Applying a selected CM list

- A list must contain exactly the CA set declared in topology.
- Duplicate list request numbers from the same CM are ignored.
- Lists from non-selected CMs are cached for possible failover.
- A selected list is rejected unless this CA's entry contains its current `reset_counter`.
- Local offsets are calculated immediately but become effective only at the next inferred cycle boundary of the selected CM.
- Until then, the previous effective list remains in use, except after reset or CM switch, where the effective list is cleared.
- A pending application is discarded if the CA resets or the selected CM changes before the timer expires.

For each remote CA:

```text
local_clock_offset[remote]
    = relative_offset[remote]
    - relative_offset[local]
    + relative_offset_error[remote]
    + relative_offset_error[local]
    + max(relative_offset_delay[remote], relative_offset_delay[local])
```

If any required value is unknown, the result is `Unknown`.

### Local-offset expiry

- The freshness timer starts when a newly calculated offset list becomes effective.
- If more than 1000 ms passes without another effective update, all `local_clock_offset` entries become `Unknown`.
- This timeout is measured from the last effective application, not from list reception or cycle start.

## 8. CA reset behavior

Clicking **Reset** performs the following:

- increments `reset_counter` modulo 256;
- sets all local offsets to `Unknown`;
- clears the current effective clock-offset list;
- stops the local-offset expiry timer;
- cancels scheduled CM responses that have not yet been sent;
- cancels clock-list applications that have not yet become effective;
- leaves the selected-CM/election state intact;
- leaves learned CA peer routes intact;
- does not remove CA data messages queued while waiting for a probe handshake;
- does not cancel receiver-side data-message latency timers.

After reset, the GUI offers an optional T2 change. Canceling that dialog keeps the current T2.

## 9. Optional UDP probe compatibility mode

`probe_enabled` is not part of the logical synchronization or integrity protocol. It is a simulation transport workaround for hosts or firewalls that more reliably accept UDP replies to traffic initiated from the local socket.

### `probe_enabled = false`

- No periodic probes are initiated by that CA.
- CM request/list delivery relies on normal CM direct UDP push.
- Without a fresh learned CA peer route, a CA data message is sent once directly to the peer endpoint in topology.
- No retry or delivery acknowledgement is added.

### `probe_enabled = true`

- The CA sends `transport_probe` messages to every CM every 20 ms.
- A CM can return its current request and current previous list to the probe's observed source IP/port.
- The CA sends `ca_peer_probe` messages to every other CA every 500 ms.
- Incoming peer probes receive an immediate `ca_peer_ack`.
- A learned peer route is considered fresh for 1500 ms.
- If a fresh route exists, CA data is sent immediately through it.
- If no fresh route exists, the clicked message is queued, a peer probe is sent immediately, and the message is sent when a probe, ACK, or data packet reveals a usable route.

A CA accepts and replies to incoming peer probes even when its own `probe_enabled` is `false`. A CM always accepts valid incoming transport probes.

A queued data-message object is created when **Send message** is clicked. Its payload, configured latency, destination, and sender reset counter are therefore click-time snapshots. Ordinary sender reset does not alter or delete it.

## 10. CA-to-CA transmission latency

`transmission_latency` has two simultaneous meanings:

1. it is the configured `age` used by the time-integrity calculation;
2. it creates a real receiver-side delay before the message becomes visible to CA logic and GUI.

The implemented sequence is:

```text
Send clicked
→ DataMessage fields frozen
→ direct UDP send, learned-route send, or probe queue
→ receiver process receives and decodes UDP datagram
→ receiver creates one independent single-shot timer
→ wait transmission_latency milliseconds
→ read receiver's current state
→ run time-integrity check
→ log PASS/DISCARD and open the integrity dialog
```

Important consequences:

- The latency timer starts when the receiver process receives the UDP datagram, not when the sender button is clicked.
- Probe-handshake waiting and actual network transit time are additional to the configured latency.
- Each received message has an independent timer; a later message with a shorter latency may be delivered first.
- A receiver reset during the wait does not cancel the timer.
- At timer expiry, integrity processing reads the latest receiver `local_clock_offset` and effective clock-offset list. A reset or list update during the wait can therefore change the result.
- The integrity `age` remains the configured latency, not the measured wall-clock delay.
- Closing or restarting the receiver process cancels in-memory timers and loses those pending deliveries. Preserving messages across receiver restart would require a separate network process, broker, or persistent queue.

This is an application-visible network-delay simulation. The UDP datagram has already entered the receiver process while the timer is running.

## 11. Time-integrity check

At simulated delivery time, the receiver evaluates the message in this order:

1. If `Dmax == 0`, PASS.
2. If `local_clock_offset[sender]` is `Unknown`, PASS.
3. Otherwise, compare the message's click-time sender `reset_counter` with the sender entry in the receiver's current effective list. A mismatch or unavailable list counter causes DISCARD.
4. Otherwise, set `age = transmission_latency`.
5. PASS only when `0 < age < Dmax`; the interval is strict.

The GUI opens a non-modal flowchart window and highlights the traversed decisions and final result.

## 12. Tests

The repository contains 20 tests:

- 17 non-Qt configuration, protocol, calculation, election/failover, and integrity tests;
- 3 Qt event-loop tests for receiver reset during latency, independent message timers, and probe-queued messages surviving sender reset with click-time fields.

Run all tests after installing the pinned requirements:

```bash
python -m pytest
```

The 17 non-Qt tests can be run separately with:

```bash
python -m pytest \
  tests/test_config.py \
  tests/test_logic.py \
  tests/test_math_utils.py \
  tests/test_protocol.py
```

## 13. Current limitations and assumptions

- Qt and operating-system timer scheduling can shift actions by several milliseconds.
- Fractional response, election, and list-application delays are rounded upward to whole milliseconds; configured numeric values remain unchanged inside calculations and messages.
- Separate CM processes do not share a global epoch. A CA infers the selected CM's phase from local request receipt time minus the request's configured T1.
- UDP remains unreliable and unordered. Direct data sends have no retransmission or end-to-end delivery acknowledgement.
- Virtual links are represented as direct UDP unicast. BAG, switch queuing, bandwidth policing, redundancy, fragmentation, and AFDX frame behavior are not simulated.
- `T1`, `T2`, and `T1 < T2` are intentionally not range-validated. Negative derived timer delays are clamped to zero.
- Datagram source addresses are learned for transport purposes but are not cryptographically authenticated.
- `clock_drift_rate` does not advance a physically drifting local clock; it is used only in the configured relative-offset-error formula.
- GUI numeric values are normally displayed to three decimal places. Only `relative_offset_error` is explicitly quantized with decimal `ROUND_HALF_UP` to 0.001.
- Receiver-side latency timers and sender-side probe queues exist only in process memory and do not survive process closure or restart.
````

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

### `setup_env.sh`

```bash
#!/bin/bash

set -e

cd "$(dirname "$0")"

python3.13 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo "Environment setup complete."
```

### `run_all_demo.sh`

```bash
#!/bin/bash

cd "$(dirname "$0")" || exit 1

PYTHON="$PWD/.venv/bin/python3"

"$PYTHON" run_cm.py configs/cm_1.json &
"$PYTHON" run_cm.py configs/cm_2.json &
"$PYTHON" run_ca.py configs/ca_101.json &
# "$PYTHON" run_ca.py configs/ca_102.json &

wait
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

### `configs/ca_101.json`

```json
{
  "role": "CA",
  "es_id": 101,
  "t2": 300.0,
  "dmax": 50.0,
  "topology_path": "topology.json",
  "probe_enabled": false
}
```

### `configs/ca_102.json`

```json
{
  "role": "CA",
  "es_id": 102,
  "t2": 320.0,
  "dmax": 0.0,
  "topology_path": "topology.json",
  "probe_enabled": false
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

### `configs/topology-hotspot.json`

```json
{
  "endpoints": [
    {
      "es_id": 1,
      "name": "CM1",
      "role": "CM",
      "ip": "172.20.10.3",
      "port": 12001
    },
    {
      "es_id": 2,
      "name": "CM2",
      "role": "CM",
      "ip": "172.20.10.3",
      "port": 12002
    },
    {
      "es_id": 101,
      "name": "CA101",
      "role": "CA",
      "ip": "172.20.10.3",
      "port": 12101
    },
    {
      "es_id": 102,
      "name": "CA102",
      "role": "CA",
      "ip": "172.20.10.6",
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

### `configs/topology-local.json`

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

### `configs/topology.json`

```json
{
  "endpoints": [
    {
      "es_id": 1,
      "name": "CM1",
      "role": "CM",
      "ip": "10.20.54.31",
      "port": 12001
    },
    {
      "es_id": 2,
      "name": "CM2",
      "role": "CM",
      "ip": "10.20.54.31",
      "port": 12002
    },
    {
      "es_id": 101,
      "name": "CA101",
      "role": "CA",
      "ip": "10.20.54.31",
      "port": 12101
    },
    {
      "es_id": 102,
      "name": "CA102",
      "role": "CA",
      "ip": "10.20.54.86",
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

### `src/timesync_sim/__init__.py`

```python
"""Time synchronization and CA communication simulator."""

__version__ = "1.0.0"
```

### `src/timesync_sim/ca_engine.py`

```python
from __future__ import annotations

import math
from functools import partial
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QElapsedTimer, QObject, QTimer, Qt, Signal

from .constants import (
    CM_UNAVAILABLE_MS,
    CYCLE_MS,
    LOCAL_CLOCK_OFFSET_EXPIRY_MS,
    RESET_COUNTER_MODULUS,
)
from .logic import (
    IntegrityTrace,
    choose_initial_cm,
    compute_local_offsets_from_list,
    evaluate_time_integrity,
    local_clock_offsets_are_stale,
)
from .models import (
    CANodeConfig,
    CAPeerAckMessage,
    CAPeerProbeMessage,
    ClockOffsetListMessage,
    DataMessage,
    Endpoint,
    RequestMessage,
    ResponseMessage,
    TopologyConfig,
    TransportProbeMessage,
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
        self.last_local_clock_offset_update_ms: Optional[int] = None
        self.reset_counter = 0
        self.current_used_clock_list: Optional[ClockOffsetListMessage] = None

        self.selected_cm_es_id: Optional[int] = None
        self.selected_cm_since_ms: Optional[int] = None
        self.last_clock_list_ms: Dict[int, int] = {}
        self.latest_clock_lists: Dict[int, ClockOffsetListMessage] = {}
        self.last_request_timing: Dict[int, Tuple[int, float]] = {}
        self.last_received_request_numbers: Dict[int, int] = {}
        self.last_received_clock_list_numbers: Dict[int, int] = {}
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

        self.local_offset_expiry_timer = QTimer(self)
        self.local_offset_expiry_timer.setSingleShot(True)
        self.local_offset_expiry_timer.setTimerType(Qt.PreciseTimer)
        self.local_offset_expiry_timer.timeout.connect(
            self._expire_stale_local_clock_offsets
        )

        # Some managed Windows systems only admit an immediate UDP response
        # to a locally initiated datagram.  Poll every few milliseconds from
        # the CA's bound socket; a CM can return its currently published
        # request/list directly to the observed source tuple.  Direct CM push
        # remains enabled, so unrestricted systems still receive at T1.
        self.transport_probe_timer = QTimer(self)
        self.transport_probe_timer.setTimerType(Qt.PreciseTimer)
        self.transport_probe_timer.setInterval(20)
        self.transport_probe_timer.timeout.connect(self._send_transport_probes)

        # Maintain a CA-to-CA UDP request/reply path as well.  This is separate
        # from the CM pull channel: restrictive Windows policies track each
        # source/destination port pair independently.
        self.peer_probe_timer = QTimer(self)
        self.peer_probe_timer.setInterval(500)
        self.peer_probe_timer.timeout.connect(self._send_ca_peer_probes)
        self.peer_routes: Dict[int, Tuple[str, int]] = {}
        self.peer_route_last_seen_ms: Dict[int, int] = {}
        self.pending_peer_messages: Dict[int, List[DataMessage]] = {
            ca_id: [] for ca_id in self.remote_ca_ids
        }
        self.peer_route_logged: set[int] = set()

        self.response_timers: List[QTimer] = []
        self.apply_timers: List[QTimer] = []
        # One receiver-side timer per CA data message.  A datagram has already
        # reached this process when its timer is created, but the message is
        # not exposed to CA integrity processing until its configured
        # transmission_latency has elapsed.  Reset deliberately does not
        # cancel these timers: they represent messages already in flight.
        self.data_delivery_timers: List[QTimer] = []
        self.reset_generation = 0
        self.running = False

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.elapsed.start()
        self.tick_timer.start()
        if self.config.probe_enabled:
            self.transport_probe_timer.start()
            self.peer_probe_timer.start()
        self.log_message.emit(
            f"CA ES_ID={self.config.es_id} listening on UDP "
            f"0.0.0.0:{self.local_endpoint.port}; advertised as "
            f"{self.local_endpoint.ip}:{self.local_endpoint.port}"
        )
        self.log_message.emit(
            "Loaded CM endpoints: "
            + ", ".join(
                f"CM {endpoint.es_id}={endpoint.ip}:{endpoint.port}"
                for endpoint in sorted(
                    self.cm_endpoints.values(), key=lambda item: item.es_id
                )
            )
        )
        self.log_message.emit(
            "Simulation UDP probes: "
            + ("enabled" if self.config.probe_enabled else "disabled")
        )
        if self.config.probe_enabled:
            self._send_transport_probes()
            self._send_ca_peer_probes()
        self._on_tick()

    def stop(self) -> None:
        self.running = False
        self.tick_timer.stop()
        self.transport_probe_timer.stop()
        self.peer_probe_timer.stop()
        self.local_offset_expiry_timer.stop()
        self._cancel_timers(self.response_timers)
        self._cancel_timers(self.apply_timers)
        # Stopping closes this CA process, so its in-memory simulated network
        # deliveries cannot survive.  Ordinary reset intentionally leaves
        # these timers running.
        self._cancel_timers(self.data_delivery_timers)

    def update_t2(self, new_t2: float) -> None:
        self.config.t2 = new_t2
        self.log_message.emit(f"T2 changed to {new_t2} ms")
        self.state_changed.emit(self.snapshot())

    def reset(self, new_t2: Optional[float] = None) -> None:
        self.reset_counter = (self.reset_counter + 1) % RESET_COUNTER_MODULUS
        self.local_clock_offsets = {ca_id: None for ca_id in self.remote_ca_ids}
        self.last_local_clock_offset_update_ms = None
        self.local_offset_expiry_timer.stop()
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
        route = self._fresh_peer_route(receiver_ca_es_id)
        if route is not None:
            self.transport.send_to(message, route[0], route[1])
            self.log_message.emit(
                f"Sent CA message to {receiver_ca_es_id} with transmission_latency="
                f"{transmission_latency} ms"
            )
            return

        if not self.config.probe_enabled:
            # Original simulation behavior: perform one direct UDP send using
            # the endpoint declared in topology.json. No transport-only probe,
            # ACK, queueing, or retry is introduced by this CA.
            self.transport.send(message, endpoint)
            self.log_message.emit(
                f"Sent CA message directly to {receiver_ca_es_id} with "
                f"transmission_latency={transmission_latency} ms "
                "(probe_enabled=false)"
            )
            return

        # Compatibility mode: do not sacrifice the user's first data message
        # merely to open a UDP path. Queue it, initiate the transport handshake,
        # and send it as soon as either a probe or ACK reveals a usable route.
        # The message object was created at click time, so its reset_counter,
        # latency, and payload remain that click-time snapshot even if this CA
        # resets before the handshake completes.  Reset does not clear it.
        self.pending_peer_messages[receiver_ca_es_id].append(message)
        self._send_ca_peer_probe(receiver_ca_es_id)
        self.log_message.emit(
            f"Queued CA message to {receiver_ca_es_id}; waiting for UDP peer handshake"
        )

    def _send_transport_probes(self) -> None:
        for cm_es_id, endpoint in self.cm_endpoints.items():
            probe = TransportProbeMessage(
                message_type="transport_probe",
                ca_es_id=self.config.es_id,
                cm_es_id=cm_es_id,
                last_request_number=self.last_received_request_numbers.get(cm_es_id),
                last_clock_list_request_number=(
                    self.last_received_clock_list_numbers.get(cm_es_id)
                ),
            )
            self.transport.send(probe, endpoint)

    def _send_ca_peer_probes(self) -> None:
        for ca_es_id in self.remote_ca_ids:
            self._send_ca_peer_probe(ca_es_id)

    def _send_ca_peer_probe(self, receiver_ca_es_id: int) -> None:
        endpoint = self.ca_endpoints[receiver_ca_es_id]
        probe = CAPeerProbeMessage(
            message_type="ca_peer_probe",
            sender_ca_es_id=self.config.es_id,
            receiver_ca_es_id=receiver_ca_es_id,
        )
        self.transport.send(probe, endpoint)

    def _fresh_peer_route(self, ca_es_id: int) -> Optional[Tuple[str, int]]:
        route = self.peer_routes.get(ca_es_id)
        seen_ms = self.peer_route_last_seen_ms.get(ca_es_id)
        if route is None or seen_ms is None:
            return None
        if self.elapsed.elapsed() - seen_ms >= 1500:
            return None
        return route

    def _record_peer_route(
        self,
        ca_es_id: int,
        sender_ip: str,
        sender_port: int,
    ) -> None:
        self.peer_routes[ca_es_id] = (sender_ip, sender_port)
        self.peer_route_last_seen_ms[ca_es_id] = self.elapsed.elapsed()
        if ca_es_id not in self.peer_route_logged:
            self.peer_route_logged.add(ca_es_id)
            self.log_message.emit(
                f"CA peer UDP path ready: CA {ca_es_id} at {sender_ip}:{sender_port}"
            )
        self._flush_pending_peer_messages(ca_es_id)

    def _flush_pending_peer_messages(self, ca_es_id: int) -> None:
        route = self._fresh_peer_route(ca_es_id)
        if route is None:
            return
        queued = self.pending_peer_messages.get(ca_es_id, [])
        while queued:
            message = queued.pop(0)
            self.transport.send_to(message, route[0], route[1])
            self.log_message.emit(
                f"Sent queued CA message to {ca_es_id} with transmission_latency="
                f"{message.transmission_latency} ms"
            )

    def _handle_ca_peer_probe(
        self,
        message: CAPeerProbeMessage,
        sender_ip: str,
        sender_port: int,
    ) -> None:
        if message.receiver_ca_es_id != self.config.es_id:
            return
        if message.sender_ca_es_id not in self.remote_ca_ids:
            return
        self._record_peer_route(message.sender_ca_es_id, sender_ip, sender_port)
        ack = CAPeerAckMessage(
            message_type="ca_peer_ack",
            sender_ca_es_id=self.config.es_id,
            receiver_ca_es_id=message.sender_ca_es_id,
        )
        self.transport.send_to(ack, sender_ip, sender_port)

    def _handle_ca_peer_ack(
        self,
        message: CAPeerAckMessage,
        sender_ip: str,
        sender_port: int,
    ) -> None:
        if message.receiver_ca_es_id != self.config.es_id:
            return
        if message.sender_ca_es_id not in self.remote_ca_ids:
            return
        self._record_peer_route(message.sender_ca_es_id, sender_ip, sender_port)

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
        elif isinstance(message, CAPeerProbeMessage):
            self._handle_ca_peer_probe(message, sender_ip, sender_port)
        elif isinstance(message, CAPeerAckMessage):
            self._handle_ca_peer_ack(message, sender_ip, sender_port)
        elif isinstance(message, DataMessage):
            self._schedule_data_message_delivery(message, sender_ip, sender_port)

    def _handle_request(self, message: RequestMessage) -> None:
        endpoint = self.cm_endpoints.get(message.cm_es_id)
        if endpoint is None:
            self.log_message.emit(
                f"Discarded request from unknown CM ES_ID={message.cm_es_id}"
            )
            return

        if self.last_received_request_numbers.get(message.cm_es_id) == message.request_number:
            return
        self.last_received_request_numbers[message.cm_es_id] = message.request_number

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

        if (
            self.last_received_clock_list_numbers.get(message.cm_es_id)
            == message.request_number
        ):
            return
        self.last_received_clock_list_numbers[message.cm_es_id] = message.request_number

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
        self.last_local_clock_offset_update_ms = self.elapsed.elapsed()
        self.local_offset_expiry_timer.start(LOCAL_CLOCK_OFFSET_EXPIRY_MS + 1)
        self.current_used_clock_list = message
        self.log_message.emit(
            f"local_clock_offset from CM {message.cm_es_id}, list "
            f"{message.request_number}, is now effective"
        )
        self.state_changed.emit(self.snapshot())

    def _expire_stale_local_clock_offsets(self) -> None:
        now_ms = self.elapsed.elapsed()
        if not local_clock_offsets_are_stale(
            self.last_local_clock_offset_update_ms,
            now_ms,
        ):
            if self.last_local_clock_offset_update_ms is not None:
                age_ms = now_ms - self.last_local_clock_offset_update_ms
                remaining_ms = max(
                    1,
                    LOCAL_CLOCK_OFFSET_EXPIRY_MS + 1 - age_ms,
                )
                self.local_offset_expiry_timer.start(remaining_ms)
            return

        had_known_value = any(
            value is not None for value in self.local_clock_offsets.values()
        )
        self.local_clock_offsets = {ca_id: None for ca_id in self.remote_ca_ids}
        self.last_local_clock_offset_update_ms = None
        if had_known_value:
            self.log_message.emit(
                "local_clock_offset expired after more than 1000 ms without "
                "an effective update; all entries set to Unknown"
            )
            self.state_changed.emit(self.snapshot())

    def _schedule_data_message_delivery(
        self,
        message: DataMessage,
        sender_ip: str,
        sender_port: int,
    ) -> None:
        if message.receiver_ca_es_id != self.config.es_id:
            return
        if message.sender_ca_es_id not in self.remote_ca_ids:
            self.log_message.emit(
                f"Discarded CA data from unknown/non-remote CA {message.sender_ca_es_id}"
            )
            return

        self._record_peer_route(
            message.sender_ca_es_id,
            sender_ip,
            sender_port,
        )

        delivery_timer = QTimer(self)
        delivery_timer.setSingleShot(True)
        delivery_timer.setTimerType(Qt.PreciseTimer)
        delivery_timer.timeout.connect(
            partial(
                self._deliver_data_message,
                message,
                delivery_timer,
            )
        )
        self.data_delivery_timers.append(delivery_timer)
        delivery_timer.start(message.transmission_latency)

    def _deliver_data_message(
        self,
        message: DataMessage,
        timer: QTimer,
    ) -> None:
        self._remove_timer(self.data_delivery_timers, timer)

        # Read receiver state only when the simulated latency expires.  A reset
        # or a new effective clock-offset list during the wait therefore
        # changes the integrity result exactly as it would at actual arrival.
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
        self.last_local_clock_offset_update_ms = None
        self.local_offset_expiry_timer.stop()
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
    TransportProbeMessage,
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
        self.current_request_message: Optional[RequestMessage] = None
        self.current_clock_list_message: Optional[ClockOffsetListMessage] = None
        self.current_responses: Dict[int, ResponseMessage] = {}
        self.learned_ca_routes: Dict[int, tuple[str, int]] = {}
        # Per-CA probe reply throttling. A burst of probes can already be in flight
        # before the CA receives the first reply and reports updated sequence numbers.
        self.last_probe_reply_ms: Dict[int, int] = {}
        self.last_probe_reply_signature: Dict[
            int, tuple[Optional[int], Optional[int]]
        ] = {}
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
            f"CM ES_ID={self.config.es_id} listening on UDP "
            f"0.0.0.0:{self.local_endpoint.port}; advertised as "
            f"{self.local_endpoint.ip}:{self.local_endpoint.port}"
        )
        self.log_message.emit(
            "Loaded CA destinations: "
            + ", ".join(
                f"CA {endpoint.es_id}={endpoint.ip}:{endpoint.port}"
                for endpoint in self.ca_endpoints
            )
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
            self.current_request_message = None
            self.current_clock_list_message = None
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
        self.current_request_message = request
        self.current_clock_list_message = self.last_completed_list

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

        if isinstance(message, TransportProbeMessage):
            self._handle_transport_probe(message, sender_ip, sender_port)
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

    def _handle_transport_probe(
        self,
        message: TransportProbeMessage,
        sender_ip: str,
        sender_port: int,
    ) -> None:
        if message.cm_es_id != self.config.es_id:
            return
        known_ca_ids = {endpoint.es_id for endpoint in self.ca_endpoints}
        if message.ca_es_id not in known_ca_ids:
            return

        route = (sender_ip, sender_port)
        previous_route = self.learned_ca_routes.get(message.ca_es_id)
        self.learned_ca_routes[message.ca_es_id] = route
        if previous_route != route:
            self.log_message.emit(
                f"Learned solicited UDP route for CA {message.ca_es_id}: "
                f"{sender_ip}:{sender_port}"
            )

        request_to_deliver = None
        if (
            self.current_request_message is not None
            and message.last_request_number
            != self.current_request_message.request_number
        ):
            request_to_deliver = self.current_request_message

        clock_list_to_deliver = None
        if (
            self.current_clock_list_message is not None
            and message.last_clock_list_request_number
            != self.current_clock_list_message.request_number
        ):
            clock_list_to_deliver = self.current_clock_list_message

        signature = (
            None if request_to_deliver is None else request_to_deliver.request_number,
            None
            if clock_list_to_deliver is None
            else clock_list_to_deliver.request_number,
        )
        if signature == (None, None):
            return

        # Several 5 ms probes may already be queued with stale acknowledgement
        # fields. Reply immediately once, then retry at most every 25 ms until a
        # later probe confirms receipt. This preserves packet-loss recovery while
        # preventing hundreds of duplicate sends and log lines per second.
        now_ms = self.elapsed.elapsed()
        if (
            self.last_probe_reply_signature.get(message.ca_es_id) == signature
            and now_ms - self.last_probe_reply_ms.get(message.ca_es_id, -10_000) < 40
        ):
            return

        delivered: List[str] = []
        if request_to_deliver is not None and self.transport.send_to(
            request_to_deliver,
            sender_ip,
            sender_port,
        ):
            delivered.append(f"request {request_to_deliver.request_number}")

        if clock_list_to_deliver is not None and self.transport.send_to(
            clock_list_to_deliver,
            sender_ip,
            sender_port,
        ):
            delivered.append(
                f"clock_offset_list {clock_list_to_deliver.request_number}"
            )

        if not delivered:
            return

        self.last_probe_reply_ms[message.ca_es_id] = now_ms
        self.last_probe_reply_signature[message.ca_es_id] = signature

        # Delivery is intentionally not logged per probe/cycle. The learned-route
        # line plus the CA's Received request line provide useful diagnostics
        # without flooding the CM runtime log.

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
LOCAL_CLOCK_OFFSET_EXPIRY_MS = 1000
```

### `src/timesync_sim/logic.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set

from .constants import CM_UNAVAILABLE_MS, LOCAL_CLOCK_OFFSET_EXPIRY_MS
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


def local_clock_offsets_are_stale(
    last_update_ms: Optional[int],
    now_ms: int,
) -> bool:
    """Return True only after offsets have gone over 1000 ms without update."""
    return (
        last_update_ms is not None
        and now_ms - last_update_ms > LOCAL_CLOCK_OFFSET_EXPIRY_MS
    )


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
        + Decimal(str(local_relative_offset_error))
        + max(Decimal(str(remote_delay)), Decimal(str(local_delay)))
    )
    return float(result)
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
    # Simulation-only transport compatibility switch. When True, this CA
    # actively sends both CA-to-CM transport probes and CA-to-CA peer probes.
    # Incoming probes are still accepted when False, allowing only the node on
    # a restrictive host to enable the workaround. Omission preserves the
    # original direct-UDP simulation behavior.
    probe_enabled: bool = Field(default=False, strict=True)


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


class TransportProbeMessage(StrictModel):
    """CA-initiated transport poll for restrictive UDP firewalls.

    A CM may immediately return the currently published request and clock
    offset list to the datagram's actual source address.  The fields only
    suppress duplicate delivery; they do not participate in synchronization
    calculations or CM selection.
    """

    protocol_version: Literal[1] = 1
    message_type: Literal["transport_probe"]
    ca_es_id: int = Field(ge=0)
    cm_es_id: int = Field(ge=0)
    last_request_number: Optional[int] = Field(default=None, ge=0, le=65535)
    last_clock_list_request_number: Optional[int] = Field(
        default=None,
        ge=0,
        le=65535,
    )


class CAPeerProbeMessage(StrictModel):
    """Transport-only CA-to-CA path warm-up message."""

    protocol_version: Literal[1] = 1
    message_type: Literal["ca_peer_probe"]
    sender_ca_es_id: int = Field(ge=0)
    receiver_ca_es_id: int = Field(ge=0)


class CAPeerAckMessage(StrictModel):
    """Immediate reply to a CA peer probe."""

    protocol_version: Literal[1] = 1
    message_type: Literal["ca_peer_ack"]
    sender_ca_es_id: int = Field(ge=0)
    receiver_ca_es_id: int = Field(ge=0)


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
    TransportProbeMessage,
    CAPeerProbeMessage,
    CAPeerAckMessage,
    DataMessage,
]
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

        # Listen on every local IPv4 interface.  The topology IP remains the
        # address advertised to other ES processes.  Binding to AnyIPv4 also
        # lets a same-computer peer reach this socket through 127.0.0.1.
        if not self.socket.bind(QHostAddress.AnyIPv4, local_endpoint.port):
            raise RuntimeError(
                f"Unable to bind UDP socket to 0.0.0.0:{local_endpoint.port} "
                f"(advertised as {local_endpoint.ip}:{local_endpoint.port}): "
                f"{self.socket.errorString()}"
            )

    def send(self, message: AnyMessage, destination: Endpoint) -> bool:
        payload = encode_message(message)

        # When both ES endpoints have the same topology IP, they are intended
        # to run on the same computer.  Use the IPv4 loopback path so Windows
        # does not route the datagram through the physical-interface firewall
        # path.  Remote peers still receive datagrams at their topology IP.
        if destination.ip == self.local_endpoint.ip:
            destination_address = QHostAddress.LocalHost
        else:
            destination_address = QHostAddress(destination.ip)

        written = self.socket.writeDatagram(
            payload,
            destination_address,
            destination.port,
        )
        if written != len(payload):
            self.error_occurred.emit(
                f"Failed to send complete datagram to {destination.ip}:{destination.port}: "
                f"{self.socket.errorString()}"
            )
            return False
        return True

    def send_to(self, message: AnyMessage, destination_ip: str, destination_port: int) -> bool:
        """Send to an address learned from an incoming datagram.

        This is used for CA-initiated transport polling.  Replying to the
        observed source tuple is more reliable behind restrictive host
        firewalls than reconstructing the return path from topology data.
        """
        payload = encode_message(message)
        written = self.socket.writeDatagram(
            payload,
            QHostAddress(destination_ip),
            destination_port,
        )
        if written != len(payload):
            self.error_occurred.emit(
                f"Failed to send complete datagram to {destination_ip}:{destination_port}: "
                f"{self.socket.errorString()}"
            )
            return False
        return True

    def _read_pending_datagrams(self) -> None:
        while self.socket.hasPendingDatagrams():
            datagram = self.socket.receiveDatagram()
            if datagram.isNull():
                continue
            payload = bytes(datagram.data())
            # Zero-length UDP datagrams are legal at the transport layer but
            # are not simulator protocol messages.  Some managed-network/Qt
            # combinations can surface them during heavy polling.  Keep them
            # out of the JSON decoder instead of flooding the runtime log.
            if not payload.strip():
                continue
            self.datagram_received.emit(
                payload,
                datagram.senderAddress().toString(),
                datagram.senderPort(),
            )

    def _on_error(self, socket_error: object) -> None:
        del socket_error
        self.error_occurred.emit(self.socket.errorString())
```

### `src/timesync_sim/protocol.py`

```python
from __future__ import annotations

import json
from typing import Dict, Type

from pydantic import ValidationError

from .models import (
    AnyMessage,
    CAPeerAckMessage,
    CAPeerProbeMessage,
    ClockOffsetListMessage,
    DataMessage,
    RequestMessage,
    ResponseMessage,
    StrictModel,
    TransportProbeMessage,
)


class ProtocolError(RuntimeError):
    pass


MESSAGE_MODELS: Dict[str, Type[StrictModel]] = {
    "request": RequestMessage,
    "response": ResponseMessage,
    "clock_offset_list": ClockOffsetListMessage,
    "transport_probe": TransportProbeMessage,
    "ca_peer_probe": CAPeerProbeMessage,
    "ca_peer_ack": CAPeerAckMessage,
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

### `src/timesync_sim/gui/__init__.py`

```python
"""Qt Widgets user interfaces."""
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

### `src/timesync_sim/gui/cm_window.py`

```python
from __future__ import annotations

from typing import Dict, List, Optional

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
        self.empty_requests_label = QLabel("No request sent yet.")
        self.requests_layout.addWidget(self.empty_requests_label)

        # Create the two request buttons once and only update their contents.
        # Recreating them on every 10 ms state update caused visible flicker and
        # could destroy a button between mouse press and mouse release.
        self.request_buttons: List[QPushButton] = []
        self.request_messages: List[Optional[ClockOffsetListMessage]] = [None, None]
        for slot_index in range(2):
            button = QPushButton()
            button.setMinimumWidth(150)
            button.setVisible(False)
            button.clicked.connect(
                lambda checked=False, index=slot_index: self._show_request_slot(index)
            )
            self.request_buttons.append(button)
            self.requests_layout.addWidget(button)
        self.requests_layout.addStretch(1)
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
        self._update_request_buttons(records)  # type: ignore[arg-type]

    def _update_request_buttons(self, records: List[CMRequestRecord]) -> None:
        self.empty_requests_label.setVisible(not records)

        for slot_index, button in enumerate(self.request_buttons):
            if slot_index >= len(records):
                self.request_messages[slot_index] = None
                button.setEnabled(False)
                button.setVisible(False)
                continue

            record = records[slot_index]
            message = record.clock_offset_list
            status = "complete" if record.completed else "calculating"

            self.request_messages[slot_index] = message
            button.setText(f"{record.request_number}\n{status}")
            button.setEnabled(record.completed and message is not None)
            button.setVisible(True)

    def _show_request_slot(self, slot_index: int) -> None:
        message = self.request_messages[slot_index]
        if message is not None:
            self._show_clock_list(message)

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

### `tests/test_ca_message_latency.py`

```python
from __future__ import annotations

from typing import List, Tuple

from PySide6.QtCore import QCoreApplication, QEventLoop, QObject, QTimer, Signal

import timesync_sim.ca_engine as ca_engine_module
from timesync_sim.ca_engine import CAEngine
from timesync_sim.models import (
    CAParameters,
    CANodeConfig,
    ClockOffsetEntry,
    ClockOffsetListMessage,
    DataMessage,
    Endpoint,
    TopologyConfig,
)


class FakeTransport(QObject):
    datagram_received = Signal(bytes, str, int)
    error_occurred = Signal(str)

    def __init__(self, local_endpoint: Endpoint, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.local_endpoint = local_endpoint
        self.sent: List[Tuple[object, Endpoint]] = []
        self.sent_to: List[Tuple[object, str, int]] = []

    def send(self, message: object, destination: Endpoint) -> bool:
        self.sent.append((message, destination))
        return True

    def send_to(self, message: object, destination_ip: str, destination_port: int) -> bool:
        self.sent_to.append((message, destination_ip, destination_port))
        return True


def _application() -> QCoreApplication:
    return QCoreApplication.instance() or QCoreApplication([])


def _wait(milliseconds: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(milliseconds, loop.quit)
    loop.exec()


def _topology() -> TopologyConfig:
    return TopologyConfig(
        endpoints=[
            Endpoint(es_id=101, name="CA101", role="CA", ip="127.0.0.1", port=30101),
            Endpoint(es_id=102, name="CA102", role="CA", ip="127.0.0.1", port=30102),
        ],
        ca_parameters={
            101: CAParameters(l2=0.0, clock_drift_rate=0.0, relative_offset_delay=0.0),
            102: CAParameters(l2=0.0, clock_drift_rate=0.0, relative_offset_delay=0.0),
        },
    )


def _engine(monkeypatch: object, es_id: int, probe_enabled: bool = False) -> CAEngine:
    _application()
    monkeypatch.setattr(ca_engine_module, "UdpTransport", FakeTransport)  # type: ignore[attr-defined]
    return CAEngine(
        CANodeConfig(
            role="CA",
            es_id=es_id,
            t2=200.0,
            dmax=100.0,
            topology_path="unused.json",
            probe_enabled=probe_enabled,
        ),
        _topology(),
    )


def _clock_list(sender_reset_counter: int) -> ClockOffsetListMessage:
    return ClockOffsetListMessage(
        message_type="clock_offset_list",
        cm_es_id=1,
        request_number=1,
        number_of_ca=2,
        entries=[
            ClockOffsetEntry(
                ca_es_id=101,
                relative_offset=10.0,
                reset_counter=sender_reset_counter,
                relative_offset_error=0.0,
            ),
            ClockOffsetEntry(
                ca_es_id=102,
                relative_offset=0.0,
                reset_counter=0,
                relative_offset_error=0.0,
            ),
        ],
    )


def test_receiver_reset_keeps_in_flight_message_and_delivery_uses_latest_state(
    monkeypatch: object,
) -> None:
    engine = _engine(monkeypatch, es_id=102)
    delivered: list[tuple[DataMessage, object]] = []
    engine.integrity_checked.connect(lambda message, trace: delivered.append((message, trace)))

    engine.local_clock_offsets[101] = 5.0
    engine.current_used_clock_list = _clock_list(sender_reset_counter=7)
    message = DataMessage(
        message_type="ca_data",
        sender_ca_es_id=101,
        receiver_ca_es_id=102,
        reset_counter=7,
        transmission_latency=40,
        payload="survives reset",
    )

    engine._schedule_data_message_delivery(message, "127.0.0.1", 30101)
    _wait(5)
    assert delivered == []
    assert len(engine.data_delivery_timers) == 1

    engine.reset()
    assert len(engine.data_delivery_timers) == 1

    # Model a new receiver state becoming effective before simulated arrival.
    engine.local_clock_offsets[101] = 5.0
    engine.current_used_clock_list = _clock_list(sender_reset_counter=8)

    _wait(70)
    assert len(delivered) == 1
    delivered_message, trace = delivered[0]
    assert delivered_message == message
    assert not trace.accepted
    assert trace.reason == "reset_counter mismatch or unavailable"
    assert engine.data_delivery_timers == []
    engine.stop()


def test_multiple_received_messages_have_independent_delivery_timers(
    monkeypatch: object,
) -> None:
    engine = _engine(monkeypatch, es_id=102)
    delivery_order: list[str] = []
    engine.integrity_checked.connect(
        lambda message, _trace: delivery_order.append(message.payload)
    )

    slow = DataMessage(
        message_type="ca_data",
        sender_ca_es_id=101,
        receiver_ca_es_id=102,
        reset_counter=0,
        transmission_latency=80,
        payload="slow",
    )
    fast = DataMessage(
        message_type="ca_data",
        sender_ca_es_id=101,
        receiver_ca_es_id=102,
        reset_counter=0,
        transmission_latency=10,
        payload="fast",
    )

    engine._schedule_data_message_delivery(slow, "127.0.0.1", 30101)
    engine._schedule_data_message_delivery(fast, "127.0.0.1", 30101)

    _wait(35)
    assert delivery_order == ["fast"]
    _wait(80)
    assert delivery_order == ["fast", "slow"]
    engine.stop()


def test_probe_pending_message_survives_sender_reset_with_click_time_snapshot(
    monkeypatch: object,
) -> None:
    engine = _engine(monkeypatch, es_id=101, probe_enabled=True)
    engine.elapsed.start()

    engine.send_ca_message(102, 25, "queued before reset")
    queued = engine.pending_peer_messages[102]
    assert len(queued) == 1
    assert queued[0].reset_counter == 0

    engine.reset()
    assert engine.reset_counter == 1
    assert len(queued) == 1
    assert queued[0].reset_counter == 0

    engine._record_peer_route(102, "127.0.0.1", 30102)
    transport = engine.transport
    sent_data = [item[0] for item in transport.sent_to if isinstance(item[0], DataMessage)]  # type: ignore[attr-defined]
    assert len(sent_data) == 1
    assert sent_data[0].reset_counter == 0
    assert sent_data[0].transmission_latency == 25
    assert sent_data[0].payload == "queued before reset"
    assert engine.pending_peer_messages[102] == []
    engine.stop()
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
    assert result == 23.04


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

## 4. 当前边界
- receiver reset 后，在途消息仍会按 timer 到期；receiver 进程关闭或重启后，内存 timer 无法保留。
- sender reset 不会删除 probe queue，但 sender 进程关闭或重启后，内存 queue 同样无法保留。
- transmission latency 从 receiver 实际收到 UDP datagram 后开始，因此 probe handshake 和真实网络传输时间会额外叠加。
- integrity check 使用配置的 transmission_latency 作为 age，不使用实际 wall-clock elapsed time。
- `run_all_demo.sh` 当前只启动两个 CM 和 CA101；CA102 行处于注释状态。
- `setup_env.sh` 当前固定调用 `python3.13`。

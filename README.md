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

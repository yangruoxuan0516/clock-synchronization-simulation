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

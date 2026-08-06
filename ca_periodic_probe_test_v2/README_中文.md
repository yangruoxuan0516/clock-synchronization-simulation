# v2 重要修正

这个版本修正了两个会造成错误结论的问题：

1. 不再启用 `SO_REUSEADDR`。如果旧测试进程仍占用 UDP 端口，新进程会明确启动失败，不会让两个 B 进程同时接收同一个端口的数据。
2. 每个包都会声明本端 `probe_mode`。A/B 模式不一致时会显示 `peer probe_mode mismatch` 并中止自动测试。
3. `until_ack` 模式下，只要空闲期间发送或收到任何 probe，结果会标为 `INVALID/CONTAMINATED`，不会错误地显示为有效 PASS。
4. B 收到 DATA 并发送 DATA_ACK 时，会明确打印 `DATA_ACK #... sent`。

每轮测试前确认端口没有旧进程占用。

macOS：

```bash
lsof -nP -iUDP:40101
lsof -nP -iUDP:40102
```

Windows CMD：

```bat
netstat -ano -p udp | findstr :40101
netstat -ano -p udp | findstr :40102
```

如果有旧 PID，先结束旧进程，再启动本轮脚本。

---

# 两台电脑 UDP 周期 Probe 必要性测试

这个测试包用于回答一个具体问题：

> CA–CA 的 UDP 路径在第一次 probe/ACK 成功后，是否还需要每 500 ms 永久发送 probe，才能保证长时间空闲后的下一条数据仍可送达？

脚本只使用 Python 标准库，不需要安装第三方包。

## 文件

- `peer_probe_test.py`：两台电脑运行同一份程序。
- `A_until_ack.json` / `B_until_ack.json`：成功建立路径后停止 probe。
- `A_periodic.json` / `B_periodic.json`：每 500 ms 永久 probe。
- `run_*.bat`：Windows CMD 启动脚本。
- `run_*.sh`：macOS/Linux 启动脚本。
- 运行后生成 CSV 日志。

## 测试环境要求

最适合在两台处于同一局域网的电脑上测试，例如：

- Windows + macOS；
- 两台 Windows；
- 两台 macOS。

两台电脑必须能够互相访问对方的 UDP 端口：

- Computer A：UDP `40101`
- Computer B：UDP `40102`

首次运行时，Windows Defender Firewall 或 macOS 防火墙可能弹出提示，需要允许 Python 接收局域网连接。

不要在公司网络、访客 Wi-Fi 或启用了客户端隔离的热点上先下结论；这类网络可能禁止终端之间直接通信。

## 第一步：确认两台电脑的局域网 IP

示例：

- Computer A：`192.168.1.101`
- Computer B：`192.168.1.102`

Windows CMD：

```bat
ipconfig
```

查找当前网卡的 IPv4 Address。

macOS：

```bash
ipconfig getifaddr en0
```

如果使用其他网卡，可在“系统设置 → 网络”中查看 IP。

## 第二步：修改四份 JSON

在 Computer A 上：

- `A_until_ack.json`
- `A_periodic.json`

把：

```json
"peer_ip": "CHANGE_TO_PC_B_IP"
```

改为 Computer B 的 IP。

在 Computer B 上：

- `B_until_ack.json`
- `B_periodic.json`

把：

```json
"peer_ip": "CHANGE_TO_PC_A_IP"
```

改为 Computer A 的 IP。

其余参数不需要改。

## 第三步：测试 until_ack

这组测试表示：

```text
尚未发现 peer：每 500 ms 重试 probe
收到 peer 的 probe 或 ACK：停止 probe
route_ttl_ms = null：进程不重启时，学习到的 route 永不过期
```

### Computer B 先启动

Windows CMD：

```bat
run_B_until_ack.bat
```

macOS/Linux：

```bash
bash run_B_until_ack.sh
```

### Computer A 再启动

Windows CMD：

```bat
run_A_until_ack.bat
```

macOS/Linux：

```bash
bash run_A_until_ack.sh
```

A 配置为自动测试发送端。路径建立后，它会依次：

1. 空闲 5 秒后发送 DATA；
2. 空闲 30 秒后发送 DATA；
3. 空闲 60 秒后发送 DATA；
4. 空闲 300 秒后发送 DATA；
5. 空闲 600 秒后发送 DATA。

每次 DATA 都要求 B 返回 `data_ack`。A 端显示：

```text
PASS DATA #...: ACK received
```

表示该次空闲后通信成功。

关键观察值：

```text
probes_sent_during_idle=0
```

在 `until_ack` 模式下应当为 0。这证明空闲期间确实没有周期 probe。

## 第四步：测试 periodic

关闭两边程序，改用：

- `B_periodic`
- `A_periodic`

Windows：

```bat
run_B_periodic.bat
run_A_periodic.bat
```

macOS/Linux：

```bash
bash run_B_periodic.sh
bash run_A_periodic.sh
```

这一轮每 500 ms 会发送 probe。自动测试使用相同的空闲时间。

## 如何判断是否需要周期 probe

### 情况 A

- `until_ack` 全部 PASS；
- `periodic` 也全部 PASS。

结论：

> 在本次测试的两台电脑、操作系统、防火墙和网络环境中，没有证据说明成功握手后还需要永久周期 probe。

推荐实现：

```text
未建立路径时重试 probe
建立成功后停止
进程重启后重新建立
```

### 情况 B

- `until_ack` 在较长空闲时间后稳定 FAIL；
- `periodic` 在相同条件下稳定 PASS；
- 重复测试结果一致。

结论：

> 当前环境可能存在 UDP 防火墙/NAT/状态跟踪超时，周期 keepalive 有实际作用。

此时再逐渐增大 probe 周期，例如 1 秒、5 秒、15 秒、30 秒，寻找最低必要频率，而不是直接固定 500 ms。

### 情况 C

两种模式都偶发 FAIL。

不能据此证明周期 probe 必要。应检查：

- 防火墙是否放行；
- 两台电脑是否处于同一子网；
- Wi-Fi 是否启用客户端隔离；
- IP 是否写错；
- 程序是否绑定了正确端口；
- 是否发生休眠、网络切换或 VPN 干扰。

## 必须额外做的场景

### 1. 启动顺序测试

先启动 A，等待 30 秒，再启动 B；然后反过来。

`until_ack` 会在尚未成功时继续重试，因此双方最终应建立路径。

### 2. 长时间空闲

至少完成 10 分钟测试。条件允许时，可把 JSON 中：

```json
"auto_idle_tests_sec": [5, 30, 60, 300, 600]
```

改成：

```json
"auto_idle_tests_sec": [60, 600, 1800, 3600]
```

### 3. 对方进程重启

建立路径后关闭 B，再重新启动 B。

由于 B 启动后会主动 probe，A 应重新收到 B 的 probe。随后在 A 输入：

```text
send after restart
```

检查是否 PASS。

### 4. 网络断开再恢复

建立路径后临时断开 Wi-Fi/网线，再恢复，然后输入：

```text
send after reconnect
```

如果失败，手动输入：

```text
probe
```

再重发。这用于区分：

- 正常空闲是否需要 keepalive；
- 异常断网恢复是否需要重新 handshake。

这两个问题不要混在一起。

## 交互命令

运行时可输入：

```text
status
probe
send hello
auto
help
quit
```

`status` 会显示：

- learned route；
- route age；
- 最后一次 probe 距今多久；
- 最后一次收到 peer 数据距今多久；
- probe/data/ACK 计数。

## CSV 日志

日志文件示例：

- `A_until_ack.csv`
- `B_until_ack.csv`
- `A_periodic.csv`
- `B_periodic.csv`

关键事件：

- `peer_route_ready`
- `idle_wait_start`
- `data_test_pass`
- `data_test_fail`
- `idle_test_result`
- `auto_test_complete`

`idle_test_result` 的 `details_json` 中包含：

- `configured_idle_sec`
- `actual_idle_sec`
- `probes_sent_during_idle`
- `probes_received_during_idle`
- `ok`
- `rtt_ms`

## 关于跨电脑时间

脚本不会用两台电脑的 monotonic clock 相减来计算单向延迟，因为不同电脑的 monotonic clock 没有共同基准。

测试的成功判据是：

```text
A 发送 DATA
B 收到并返回 DATA_ACK
A 在 timeout 内收到 ACK
```

RTT 由同一台 A 电脑的 monotonic clock 计算，因此有效。

## 建议的实验顺序

1. `until_ack`，5 秒和 30 秒；
2. `until_ack`，1 分钟、5 分钟和 10 分钟；
3. `periodic`，相同空闲时间；
4. 两组各重复至少 3 次；
5. 测试双方不同启动顺序；
6. 测试 B 进程重启；
7. 最后再测试网络断开恢复。

只有当 `until_ack` 长期稳定失败、而 `periodic` 在同样环境下稳定成功，才应认定周期 probe 有必要。

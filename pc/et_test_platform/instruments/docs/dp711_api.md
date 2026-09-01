# RIGOL DP711 Python API 清单

本文列出 DP711 Driver 当前公开原子 API。所有方法均来自 DP700 Programming Guide；
`operations.py` 的组合操作另列，不计入 108 个原子 API 覆盖数。

## 1. 连接与入口

- `create_dp711_serial_driver(port, baudrate=9600, parity=NONE, timeout_s=2.0)`：创建未打开的 RS232 Driver。
- `Dp711Driver.open()`：打开连接。
- `Dp711Driver.close()`：关闭连接。

调用示例：

```python
driver = create_dp711_serial_driver("COM3")
driver.open()
driver.source.voltage_set(5.0)
driver.source.current_set(1.0)
driver.output.enabled_set(True)
measurement = driver.measurement.all_get()
driver.output.enabled_set(False)
driver.close()
```

## 2. 原子 API

### 2.1 `basic`

共 15 个：

- `apply_set(voltage_v, current_a)`
- `apply_get()`
- `display_enabled_set(enabled)`
- `display_enabled_get()`
- `identity_get()`
- `options_get()`
- `state_recall(position)`
- `reset()`
- `state_save(position)`
- `self_test_get()`
- `channel_number_set(channel)`
- `channel_number_get()`
- `channel_select()`
- `channel_selected_get()`
- `license_set(license_code)`

### 2.2 `measurement`

共 4 个：

- `all_get()`
- `current_get()`
- `power_get()`
- `voltage_get()`

### 2.3 `memory`

共 6 个：

- `delete(file_type, position)`
- `load(file_type, position)`
- `locked_set(file_type, position, locked)`
- `locked_get(file_type, position)`
- `store(file_type, position)`
- `valid_get(file_type, position)`

### 2.4 `output`

共 18 个：

- `cvcc_get()`
- `mode_get()`
- `ocp_alarm_get()`
- `ocp_questionable_get()`
- `ocp_clear()`
- `ocp_enabled_set(enabled)`
- `ocp_enabled_get()`
- `ocp_value_set(current_a)`
- `ocp_value_get(limit)`
- `ovp_alarm_get()`
- `ovp_questionable_get()`
- `ovp_clear()`
- `ovp_enabled_set(enabled)`
- `ovp_enabled_get()`
- `ovp_value_set(voltage_v)`
- `ovp_value_get(limit)`
- `enabled_set(enabled)`
- `enabled_get()`

### 2.5 `source`

共 16 个：

- `current_set(current_a)`
- `current_get(limit)`
- `current_protection_clear()`
- `current_protection_value_set(current_a)`
- `current_protection_value_get(limit)`
- `current_protection_enabled_set(enabled)`
- `current_protection_enabled_get()`
- `current_protection_tripped_get()`
- `voltage_set(voltage_v)`
- `voltage_get(limit)`
- `voltage_protection_clear()`
- `voltage_protection_value_set(voltage_v)`
- `voltage_protection_value_get(limit)`
- `voltage_protection_enabled_set(enabled)`
- `voltage_protection_enabled_get()`
- `voltage_protection_tripped_get()`

### 2.6 `system`

共 37 个：

- `beep()`
- `beeper_enabled_set(enabled)`
- `beeper_enabled_get()`
- `brightness_set(brightness)`
- `brightness_get(limit)`
- `rs232_baudrate_set(baudrate)`
- `rs232_baudrate_get()`
- `rs232_data_bits_set(data_bits)`
- `rs232_data_bits_get()`
- `rs232_parity_set(parity)`
- `rs232_parity_get()`
- `rs232_stop_bits_set(stop_bits)`
- `rs232_stop_bits_get()`
- `error_get()`
- `fan_test_get()`
- `key_locked_set(key, locked)`
- `key_locked_get(key)`
- `remote_lock_enabled_set(enabled)`
- `remote_lock_enabled_get()`
- `language_set(language)`
- `language_get()`
- `local_mode_set()`
- `panel_lock_enabled_set(enabled)`
- `panel_lock_enabled_get()`
- `power_on_mode_set(mode)`
- `power_on_mode_get()`
- `screen_image_get()`
- `remote_mode_set()`
- `rwlock_set(enabled)`
- `screen_saver_enabled_set(enabled)`
- `screen_saver_enabled_get()`
- `self_test_get()`
- `trigger_input_enabled_set(enabled)`
- `trigger_input_enabled_get()`
- `trigger_output_enabled_set(enabled)`
- `trigger_output_enabled_get()`
- `scpi_version_get()`

### 2.7 `timer`

共 12 个：

- `cycles_set(cycles)`
- `cycles_get()`
- `end_state_set(state)`
- `end_state_get()`
- `groups_set(groups)`
- `groups_get()`
- `parameter_set(group, voltage_v, current_a, duration_s)`
- `parameter_get(first_group, count)`
- `enabled_set(enabled)`
- `enabled_get()`
- `trigger_mode_set(mode)`
- `trigger_mode_get()`

## 3. Operations 组合层

- `configure_and_enable(voltage_v, current_a)`：设置电压、电流并打开输出。
- `safe_output_off(clear_protection=False)`：关闭输出，可选清除 OCP/OVP 标志。
- `read_output()`：读取电压、电流、功率。

Operations 只是复用原子 API，不新增设备命令语义。

## 4. 验证状态

- Programming Guide 规范化命令语义覆盖：108 / 108。
- 无硬件协议单元测试：已执行。
- 真实 DP711 HIL：`NOT_EXECUTED`。

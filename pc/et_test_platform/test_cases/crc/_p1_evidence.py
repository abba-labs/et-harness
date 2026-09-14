# CRC P1 的报告投影：只消费已经返回的数据，不访问设备，不决定 PASS/FAIL。
from __future__ import annotations

import hashlib
from dataclasses import asdict

from ...drivers.crc import CrcIrqEvent


def p1_artifact_name(case_id, parameters):
    """Keep the previous per-Case artifact filenames."""
    suffixes = {
        "crc_p1_008": "auto_length_reload", "crc_p1_009": "check_match",
        "crc_p1_010": "check_mismatch_irq", "crc_p1_012": "fifo_overflow_recovery",
        "crc_p1_014": "irq_clear", "crc_p1_015": "irq_mask_raw_status",
        "crc_p1_016": "length_error_irq", "crc_p1_018": "bus_error_irq_recovery",
    }
    if case_id == "crc_p1_001":
        suffix = f"poly_{parameters['polynomial']:08x}"
    elif case_id == "crc_p1_002":
        suffix = f"seed_{parameters['initial_value']:08x}"
    elif case_id == "crc_p1_003":
        suffix = f"{parameters['mode'].name.lower()}_swap_{int(parameters['byte_swap'])}"
    elif case_id == "crc_p1_004":
        suffix = f"refin_{int(parameters['ref_in'])}"
    elif case_id == "crc_p1_005":
        suffix = f"refout_{int(parameters['ref_out'])}"
    elif case_id == "crc_p1_006":
        suffix = f"xor_{parameters['xor_out'].name.lower()}"
    elif case_id == "crc_p1_007":
        suffix = f"{parameters['mode'].name.lower()}_{parameters['length_bytes']}"
    elif case_id == "crc_p1_013":
        suffix = parameters["event"].name.lower()
    else:
        suffix = suffixes[case_id]
    return f"{case_id}_{suffix}.json"


def p1_input_metadata(case_id, parameters, vector):
    """Expected values come only from immutable PC input, never a DUT response."""
    data = {key: getattr(value, "name", value) for key, value in parameters.items()}
    data.update(mode=vector.config.mode.name, length_bytes=len(vector.payload))
    if vector.payload:
        key = "recovery_expected_crc" if case_id in {"crc_p1_012", "crc_p1_018"} else "expected_crc"
        data[key] = vector.expected
    if case_id == "crc_p1_007":
        unit = int(vector.config.mode) // 8
        data["expected_input_count"] = len(vector.payload) // unit + len(vector.payload) % unit
    if case_id == "crc_p1_008":
        data["first_expected_crc"], data["second_expected_crc"] = vector.expected, vector.second_expected
    if case_id == "crc_p1_010":
        data["check_value"] = vector.expected ^ 1
    if case_id == "crc_p1_012":
        data.update(fifo_threshold=1, write_count=7, expected_overflow=True)
    if case_id in {"crc_p1_013", "crc_p1_016", "crc_p1_018"}:
        event = parameters.get("event", CrcIrqEvent.LENGTH_ERROR if case_id == "crc_p1_016" else CrcIrqEvent.BUS_ERROR)
        data["expected_irq_event"] = event.name
    return data


def _at(items, index):
    return items[index] if index < len(items) else None


def p1_result_projection(case_id, parameters, vector, driver):
    """Project original Observation keys; missing reads stay missing, never fabricated zeros."""
    data = p1_input_metadata(case_id, parameters, vector)
    observations = []
    data.update(
        measurement_schema="et.measurement.v1", ip="crc", case_id=case_id,
        instance=f"crc{driver.instance_id}", config=asdict(vector.config),
        payload_hex=vector.payload.hex(), payload_sha256=hashlib.sha256(vector.payload).hexdigest(),
        second_payload_hex=vector.second_payload.hex(),
        calculations=[asdict(item) for item in driver.calculations],
        irq_snapshots=[asdict(item) for item in driver.irq_snapshots],
        length_readbacks=list(driver.length_readbacks),
        fifo_states=[asdict(item) for item in driver.fifo_states],
        bursts=[asdict(item) for item in driver.bursts],
    )
    if vector.payload:
        data["expected"] = vector.expected
    calc = _at(driver.calculations, 0)
    if calc is not None:
        data.update(actual=calc.result, remaining_input_count=calc.remaining_input_count)

    def observe(key, value, endpoint):
        data[key] = value
        observations.append((key, value, endpoint))

    def calculation(index, prefix):
        actual = _at(driver.calculations, index)
        if actual is not None:
            observe(f"{prefix}actual_crc", actual.result, "RESULT.CRC")
            observe(f"{prefix}remaining_input_count", actual.remaining_input_count, "LENGTH.REMAINING_INPUT_COUNT")
            data[f"{prefix}actual"] = actual.result

    def irq_bits(index, event, raw_key, status_key):
        actual = _at(driver.irq_snapshots, index)
        if actual is not None:
            observe(raw_key, bool(actual.raw & event), f"IRQ_RAW.{event.name}")
            observe(status_key, bool(actual.status & event), f"IRQ_STATUS.{event.name}")

    def latch(index, event, event_key, raw_key):
        actual = _at(driver.irq_snapshots, index)
        if actual is not None:
            observe(event_key, int(actual.last_event), f"ISR.LATCHED.{event.name}")
            observe(raw_key, int(actual.last_raw), f"ISR.LAST_RAW.{event.name}")
            data.update(last_event=int(actual.last_event), last_raw=int(actual.last_raw))

    def counts(before_index, after_index, prefix=""):
        before, after = _at(driver.irq_snapshots, before_index), _at(driver.irq_snapshots, after_index)
        if before is not None:
            data[f"{prefix}event_count_before"] = before.event_count
        if after is not None:
            data[f"{prefix}event_count_after"] = after.event_count
        if before is not None and after is not None:
            data[f"{prefix}event_count_delta"] = after.event_count - before.event_count

    if case_id == "crc_p1_007" and driver.length_readbacks:
        observe("programmed_input_count", driver.length_readbacks[0], "LENGTH.REMAINING_INPUT_COUNT")
    elif case_id == "crc_p1_008":
        calculation(0, "first_")
        calculation(1, "second_")
        data.update(first_expected=vector.expected, second_expected=vector.second_expected)
    elif case_id in {"crc_p1_009", "crc_p1_010"}:
        index = int(case_id == "crc_p1_010")
        irq_bits(index, CrcIrqEvent.CHECK_ERROR, "check_error_raw", "check_error_status")
        if index:
            counts(0, 1)
            latch(1, CrcIrqEvent.CHECK_ERROR, "isr_latched_event", "isr_last_raw")
            data["wrong_check"] = vector.expected ^ 1
    elif case_id == "crc_p1_012":
        if driver.fifo_states:
            observe("overflow_before", driver.fifo_states[0].overflow, "FIFO.OVERFLOW")
        if driver.bursts:
            observe("overflow_after", driver.bursts[0].overflow, "FIFO.OVERFLOW")
        calculation(0, "recovery_")
        data["recovery_expected"] = vector.expected
    elif case_id == "crc_p1_013":
        event = parameters["event"]
        counts(0, 1)
        counts(2, 3, "disabled_")
        latch(1, event, "delivered_isr_event", "delivered_isr_last_raw")
        actual = _at(driver.irq_snapshots, 3)
        if actual is not None:
            observe("disabled_force_raw", bool(actual.raw & event), f"IRQ_RAW.{event.name}")
    elif case_id == "crc_p1_014":
        event = CrcIrqEvent.BUS_ERROR
        counts(0, 2)
        irq_bits(1, event, "raw_before_clear", "status_before_clear")
        irq_bits(2, event, "raw_after_clear", "status_after_clear")
        for index, prefix in ((1, "pending"), (2, "cleared")):
            actual = _at(driver.irq_snapshots, index)
            if actual is not None:
                data[f"{prefix}_raw"], data[f"{prefix}_status"] = int(actual.raw), int(actual.status)
    elif case_id == "crc_p1_015":
        event = CrcIrqEvent.LENGTH_ERROR
        counts(0, 1, "masked_")
        counts(0, 2, "unmasked_")
        irq_bits(1, event, "masked_raw_status", "masked_effective_status")
        irq_bits(2, event, "unmasked_raw_status", "unmasked_effective_status")
        latch(2, event, "unmasked_isr_event", "unmasked_isr_last_raw")
        for index, prefix in ((1, "masked"), (2, "delivered")):
            actual = _at(driver.irq_snapshots, index)
            if actual is not None:
                data.update({f"{prefix}_raw": int(actual.raw), f"{prefix}_status": int(actual.status),
                             f"{prefix}_event_count": actual.event_count})
    elif case_id in {"crc_p1_016", "crc_p1_018"}:
        event = CrcIrqEvent.LENGTH_ERROR if case_id == "crc_p1_016" else CrcIrqEvent.BUS_ERROR
        index = 1 if case_id == "crc_p1_016" else 2
        counts(index - 1, index)
        irq_bits(index, event, "irq_raw_status", "irq_status")
        latch(index, event, "isr_latched_event", "isr_last_raw")
        if case_id == "crc_p1_018":
            counts(0, 1, "legal_")
            irq_bits(1, event, "legal_bus_error_raw", "legal_bus_error_status")
            calculation(0, "recovery_")
            data["recovery_expected"] = vector.expected
            actual = _at(driver.irq_snapshots, 2)
            if actual is not None:
                data.update(error_event_count_after=actual.event_count, error_raw=int(actual.raw), error_status=int(actual.status))
    # Preserve the legacy JSON raw fields as well as the structured arrays.
    if case_id in {"crc_p1_010", "crc_p1_016"}:
        actual = _at(driver.irq_snapshots, 1)
        if actual is not None:
            data.update(raw=int(actual.raw), status=int(actual.status))
    if case_id == "crc_p1_013":
        actual = _at(driver.irq_snapshots, 3)
        if actual is not None:
            data["disabled_force_raw"] = int(actual.raw)
    if case_id == "crc_p1_015":
        actual = _at(driver.irq_snapshots, 2)
        if actual is not None:
            data.update(delivered_last_event=int(actual.last_event), delivered_last_raw=int(actual.last_raw))
    # Do not classify this execution: pytest/canonical result owns the verdict.
    return data, observations

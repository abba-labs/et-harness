# 当前运行事实的按需提取。
# 职责：提供有界摘要和精确指定字段，不复制规范、配置或Session全文。
# 边界：输出是待提炼事实，不是长期知识，不推测根因或宣布问题关闭。
# 依赖：标准库和已校验的Canonical输入。

from __future__ import annotations

import json
from datetime import timedelta, timezone

from record_model import list_value, object_value, timestamp
from record_source import RecordInput
from record_transaction import safe_name

MAX_FACTS_BYTES = 256 * 1024


def _cell(value: object, *, limit: int = 600) -> str:
    text = str(value if value is not None else "未知").replace("\r", " ").replace("\n", " ")
    text = text.replace("|", "\\|")
    return text if len(text) <= limit else text[:limit] + "…（摘要截短；原值见当前Result）"


def render_facts(
    incoming: RecordInput, *, cases: tuple[str, ...] = (), keys: tuple[str, ...] = ()
) -> bytes:
    selected = {safe_name(case).upper() for case in cases} or set(incoming.cases)
    if selected - set(incoming.cases):
        raise ValueError(
            f"Case was not selected in this Session: {sorted(selected - set(incoming.cases))}"
        )
    if keys and not cases:
        raise ValueError("field extraction requires explicit --case")
    first = next(iter(incoming.cases.values()))[0]
    session = first.session
    finished = timestamp(session["finished_at"]).astimezone(timezone(timedelta(hours=8)))
    lines = [
        f"# {incoming.chip} {incoming.ip} 当前运行事实",
        "",
        "临时提取，不是Case知识或新测试；不得根据本摘要自动确认根因/关闭问题。",
        "",
        f"适用：{incoming.chip} / {first.lane}；Source={_cell(session.get('source_revision'))}；Dirty={_cell(session.get('source_dirty'))}。",
        f"测试完成：{finished:%Y-%m-%d %H:%M CST}；bitstream={_cell(session.get('bitstream_id'))}；设备身份={_cell(session.get('device_identity'))}。",
        f"原始结果：{first.origin}（按需读取，不复制全文）。",
        "",
    ]
    matched: set[str] = set()
    for case in sorted(selected):
        lines.extend([f"## {case}", "", "| 参数 | 原始结果 | 失败/未执行信息 |", "|---|---|---|"])
        for snapshot in incoming.cases[case]:
            result = snapshot.result or {}
            lines.append(
                f"| {_cell(snapshot.selection.get('parameter_id') or '无参数')} | {snapshot.status} | {_cell(result.get('error') or ('未执行' if snapshot.result is None else '无'))} |"
            )
        lines.append("")
        if not cases:
            continue
        for snapshot in incoming.cases[case]:
            result = snapshot.result or {}
            fields = {
                "measurement." + name: value
                for name, value in object_value(
                    result.get("measurements", {}), "measurements"
                ).items()
            }
            observations: dict[str, list[dict[str, object]]] = {}
            for entry in list_value(result.get("observations", []), "observations"):
                observation = object_value(entry, "observation")
                key = "observation." + str(observation["key"])
                observations.setdefault(key, []).append(observation)
            fields.update(observations)
            lines.extend(
                [f"### 参数：{_cell(snapshot.selection.get('parameter_id') or '无参数')}", ""]
            )
            if not keys:
                lines.extend(
                    [
                        "可提取字段（用 --key 精确选择）：",
                        "",
                        *[f"- `{key}`" for key in sorted(fields)],
                        "",
                    ]
                )
            for key in keys:
                if key not in fields:
                    lines.extend([f"{key}：该参数未记录此字段。", ""])
                    continue
                matched.add(key)
                value = json.dumps(fields[key], ensure_ascii=False, indent=2, allow_nan=False)
                lines.extend([f"{key}：", "", "````json", value, "````", ""])
    if set(keys) - matched:
        raise ValueError(
            f"requested field is absent from selected results: {sorted(set(keys) - matched)}"
        )
    data = ("\n".join(lines).rstrip() + "\n").encode("utf-8")
    if len(data) > MAX_FACTS_BYTES:
        raise ValueError(
            "fact selection exceeds 256 KiB; select fewer Cases/fields; source retained"
        )
    return data

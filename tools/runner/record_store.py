# 固定芯片/IP目录的Markdown知识入口。
# 职责：定位知识文件，生成轻量索引，保留人工Case正文。
# 边界：不保存Canonical副本、计数或保护快照，不改写Case知识。
# 依赖：标准库和既有文件事务。

from __future__ import annotations

from pathlib import Path

from record_transaction import publish, recover, safe_name, safe_path

BEGIN = "<!-- ET_RECORD_AUTO_BEGIN -->"
END = "<!-- ET_RECORD_AUTO_END -->"
MAX_MARKDOWN_BYTES = 16 * 1024


def record_root(repository: Path, chip: str, ip: str) -> Path:
    return safe_path(
        repository, f"artifacts/records/{safe_name(chip).upper()}/{safe_name(ip).upper()}"
    )


def working_root(repository: Path, chip: str, ip: str) -> Path:
    return safe_path(
        repository,
        f"artifacts/runs/record-maintenance/{safe_name(chip).upper()}_{safe_name(ip).upper()}",
    )


# 仅索引有机器区；Case正文永远由人或Agent维护，不能调用此函数生成Case。
def index_markdown(root: Path, titles: dict[str, str], *, legacy_count: int) -> bytes:
    lines = ["## Case知识索引", "", "本索引不汇总测试状态；当前测试结果见运行工作区。", ""]
    lines.extend(f"- [{title}](cases/{case}.md)" for case, title in sorted(titles.items()))
    if not titles:
        lines.append("尚无已提炼的Case知识。")
    if legacy_count:
        lines.extend(["", f"另有{legacy_count}份旧自动记录待提炼；本次未修改旧证据。"])
    generated = "\n".join(lines)
    path = safe_path(root, "README.md")
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing.count(BEGIN) != 1 or existing.count(END) != 1:
            raise ValueError("index has missing/duplicate markers; preserve and repair it manually")
        prefix, remainder = existing.split(BEGIN)
        _, suffix = remainder.split(END)
    else:
        prefix, suffix = f"# {root.parent.name} {root.name} Case知识\n\n", "\n"
    return (prefix + BEGIN + "\n\n" + generated + "\n\n" + END + suffix).encode("utf-8")


def refresh_index(root: Path, work: Path) -> int:
    from record_check import check_records

    recover(root, work)
    check = check_records(root)
    titles = dict(check["titles"])
    content = index_markdown(root, titles, legacy_count=int(check["legacy_count"]))
    return publish(root, work, {"README.md": content}, validate=lambda: check_records(root))

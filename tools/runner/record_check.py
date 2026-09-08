# Case Markdown知识的轻量离线检查。
# 职责：检查身份、适用基线、正文、链接及最小附件，识别未迁移旧记录。
# 边界：不判断自然语言根因是否成立，不要求JSON/ZIP副本，不修改文件。
# 依赖：标准库、记录路径和Hash工具。

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

from record_store import BEGIN, END, MAX_MARKDOWN_BYTES
from record_transaction import digest, safe_name, safe_path

LINK = re.compile(r"\]\(([^)]+)\)")
MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024


# 本地链接只允许仓库内文件；知识附件只绑定本Case明确引用的文件。
def _links(path: Path, body: str, repository: Path, root: Path) -> dict[str, str]:
    attachments: dict[str, str] = {}
    for match in LINK.finditer(body):
        reference = match.group(1).strip().strip("<>")
        parsed = urlsplit(reference)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            continue
        if parsed.scheme or parsed.netloc or "\\" in reference:
            raise ValueError(f"unsupported knowledge link: {path.name}: {reference}")
        target = path if not parsed.path else path.parent / unquote(parsed.path)
        try:
            relative = target.resolve().relative_to(repository.resolve()).as_posix()
        except ValueError as exc:
            raise ValueError(f"knowledge link escapes repository: {reference}") from exc
        target = safe_path(repository, relative)
        if relative.startswith("artifacts/records/") and any(
            part in {"current", "_maintenance"} for part in Path(relative).parts[2:]
        ):
            raise ValueError("knowledge must not depend on replaceable current/maintenance files")
        if not target.is_file():
            raise ValueError(f"missing knowledge link: {path.name}: {reference}")
        if target.is_relative_to(root):
            local = target.relative_to(root).as_posix()
            if local.startswith("attachments/"):
                if not local.startswith(f"attachments/{path.stem}/"):
                    raise ValueError(f"attachment must belong to this Case: {reference}")
                if target.stat().st_size > MAX_ATTACHMENT_BYTES:
                    raise ValueError(f"knowledge attachment exceeds 25 MiB: {reference}")
                attachments[local] = digest(target.read_bytes())
            elif local.startswith("evidence/") or local in {"results.json", "test_report.xlsx"}:
                raise ValueError("knowledge must not depend on legacy JSON/ZIP/report copies")
        if parsed.fragment and target.suffix.lower() == ".md":
            text = target.read_text(encoding="utf-8")
            anchor = unquote(parsed.fragment)
            headings = {
                re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")
                for heading in re.findall(r"^#{1,6}\s+(.+)$", text, re.MULTILINE)
            }
            if f'id="{anchor}"' not in text and anchor not in headings:
                raise ValueError(f"missing knowledge anchor: {path.name}: {reference}")
    if sum(safe_path(root, name).stat().st_size for name in attachments) > MAX_ATTACHMENT_BYTES:
        raise ValueError("Case knowledge attachments exceed 25 MiB in total")
    return attachments


def check_document(path: Path, root: Path, repository: Path) -> tuple[str, dict[str, str]]:
    safe_path(root, path.relative_to(root).as_posix())
    if path.stat().st_size > MAX_MARKDOWN_BYTES:
        raise ValueError(f"Case knowledge exceeds 16 KiB; distill it before contributing: {path}")
    data = path.read_bytes()
    body = data.decode("utf-8-sig")
    case = path.stem
    heading = re.search(r"^#\s+([^\r\n]+)", body)
    if not re.fullmatch(rf"{re.escape(root.name)}_P\d+_\d+", case):
        raise ValueError(f"Case filename does not belong to this IP: {path.name}")
    if heading is None or not re.match(rf"{re.escape(case)}(?:\s|$)", heading.group(1)):
        raise ValueError(f"Case heading and filename disagree: {path.name}")
    if BEGIN in body or END in body:
        raise ValueError(f"legacy automatic Case record requires explicit distillation: {case}")
    baseline = re.search(r"^适用基线：(.+)$", body, re.MULTILINE)
    if baseline is None or not re.search(
        rf"\b{re.escape(root.parent.name)}\b\s*/\s*(?:FPGA|HIL|SIL)\b",
        baseline.group(1),
        re.IGNORECASE,
    ):
        raise ValueError(f"missing chip/Lane applicability baseline: {case}")
    if "源码" not in baseline.group(1) and "版本" not in baseline.group(1):
        raise ValueError(f"missing version or explicit unknown version: {case}")
    if not re.search(r"^##\s+.+\n\s*\n\S", body, re.MULTILINE):
        raise ValueError(f"knowledge requires a non-empty result/problem section: {case}")
    if not re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2} CST", body):
        raise ValueError(f"knowledge requires a dated conclusion: {case}")
    attachments = _links(path, body, repository, root)
    return heading.group(1), {f"cases/{case}.md": digest(data), **attachments}


# 默认包含旧记录数量但不将其当作已贡献知识；显式Case检查必须全部通过新格式。
def check_records(root: Path, *, cases: tuple[str, ...] = ()) -> dict[str, object]:
    repository = root.parents[3]
    safe_path(repository, root.relative_to(repository).as_posix())
    if not root.is_dir():
        raise ValueError(f"knowledge directory does not exist: {root}")
    requested = {safe_name(case).upper() for case in cases}
    paths = sorted(safe_path(root, "cases").glob("*.md"))
    found = {path.stem for path in paths}
    if requested - found:
        raise ValueError(f"missing Case knowledge: {sorted(requested - found)}")
    titles: dict[str, str] = {}
    files: dict[str, str] = {}
    legacy = 0
    for path in paths:
        if requested and path.stem not in requested:
            continue
        safe_path(root, path.relative_to(root).as_posix())
        if not requested and BEGIN.encode() in path.read_bytes():
            legacy += 1
            continue
        title, referenced = check_document(path, root, repository)
        titles[path.stem] = title
        files.update(referenced)
    return {
        "status": "PASS",
        "check": "Markdown structure and links only; not root-cause or hardware validation",
        "chip": root.parent.name,
        "ip": root.name,
        "case_count": len(titles),
        "legacy_count": legacy,
        "titles": titles,
        "files": files,
    }

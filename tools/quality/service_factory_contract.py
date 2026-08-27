# Firmware Service Factory标记区域的唯一结构校验器。
# 职责：识别并验证R300允许的include、声明和薄Factory实现。
# 边界：只检查平台Factory胶水结构，不判断IP命令或硬件行为。
# 依赖：仅标准库。

from __future__ import annotations

import re

FACTORY_REGION_BEGIN = "/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */"
FACTORY_REGION_END = "/* ET_PLATFORM_SERVICE_FACTORY_END */"


# 删除真实C注释，同时保留字符串和字符字面量中的注释标记。
def strip_c_comments(text: str) -> str:

    output: list[str] = []
    index = 0
    state = "normal"

    while index < len(text):
        current = text[index]
        following = text[index + 1] if index + 1 < len(text) else ""

        if state == "normal":
            if current == '"':
                output.append(current)
                state = "string"
                index += 1
                continue

            if current == "'":
                output.append(current)
                state = "character"
                index += 1
                continue

            if current == "/" and following == "/":
                output.append(" ")
                state = "line_comment"
                index += 2
                continue

            if current == "/" and following == "*":
                output.append(" ")
                state = "block_comment"
                index += 2
                continue

            output.append(current)
            index += 1
            continue

        if state in {"string", "character"}:
            output.append(current)

            if current == "\\" and following:
                output.append(following)
                index += 2
                continue

            if (state == "string" and current == '"') or (state == "character" and current == "'"):
                state = "normal"

            index += 1
            continue

        if state == "line_comment":
            if current in "\r\n":
                output.append(current)
                state = "normal"

            index += 1
            continue

        if current == "*" and following == "/":
            state = "normal"
            index += 2
            continue

        if current in "\r\n":
            output.append(current)

        index += 1

    # 非法的未闭合块注释必须保持可见，由上层失败关闭。
    return text if state == "block_comment" else "".join(output)


# 将Factory区域压缩为稳定C Token文本，排除注释和排版差异。
def _compact_code(text: str) -> str:

    return "".join(strip_c_comments(text).split())


# 验证头文件中的公共Factory include或声明。
def _header_region_kind(code: str, ip: str) -> str | None:

    if code == '#include"et_service_factory.h"':
        return "include"

    declaration = (
        f"intet_{ip}_service_create(void*storage,uint16_tinstance_id,"
        "constet_service_factory_context_t*context,"
        "constet_service_descriptor_t**descriptor);"
    )
    return "declaration" if code == declaration else None


# 验证源文件中的Factory严格保持为参数校验、既有init和Descriptor返回。
def _source_region_is_thin_factory(code: str, ip: str) -> bool:

    identifier = re.escape(ip)
    pattern = re.compile(
        rf"^intet_{identifier}_service_create\(void\*storage,uint16_tinstance_id,"
        rf"constet_service_factory_context_t\*context,"
        rf"constet_service_descriptor_t\*\*descriptor\)\{{"
        rf"et_{identifier}_service_t\*service=\(et_{identifier}_service_t\*\)storage;"
        rf"if\(\(service==NULL\)\|\|\(context==NULL\)\|\|"
        rf"\(context->irq_manager==NULL\)\|\|\(descriptor==NULL\)\)"
        rf"\{{return-1;\}}"
        rf"if\(et_{identifier}_service_init\(service,"
        rf"(?:\([A-Za-z_][A-Za-z0-9_]*\))?instance_id,context->irq_manager"
        rf"(?:,context->irq_priority)?\)!=0\)\{{return-1;\}}"
        rf"\*descriptor=et_{identifier}_service_descriptor\(service\);"
        rf"return\(\*descriptor==NULL\)\?-1:0;\}}$"
    )
    return pattern.fullmatch(code) is not None


# 验证一个Service文件中的全部Marker，并返回可供同步门禁剥离的完整区域。
def validated_factory_regions(
    text: str, *, ip: str, suffix: str
) -> tuple[list[tuple[int, int]], list[str]]:

    begin_count = text.count(FACTORY_REGION_BEGIN)
    end_count = text.count(FACTORY_REGION_END)
    if begin_count == 0 and end_count == 0:
        return [], []

    if begin_count != end_count:
        return [], ["factory markers must be balanced"]

    regions: list[tuple[int, int]] = []
    kinds: list[str] = []
    cursor = 0

    while cursor < len(text):
        begin = text.find(FACTORY_REGION_BEGIN, cursor)
        if begin < 0:
            break

        content_start = begin + len(FACTORY_REGION_BEGIN)
        end = text.find(FACTORY_REGION_END, content_start)
        if end < 0 or text.find(FACTORY_REGION_BEGIN, content_start, end) >= 0:
            return [], ["factory markers must not be nested or overlap"]

        code = _compact_code(text[content_start:end])
        if suffix == ".h":
            kind = _header_region_kind(code, ip)
        elif suffix == ".c" and _source_region_is_thin_factory(code, ip):
            kind = "implementation"
        else:
            kind = None

        if kind is None:
            return [], ["factory region contains content outside the thin Factory contract"]

        regions.append((begin, end + len(FACTORY_REGION_END)))
        kinds.append(kind)
        cursor = end + len(FACTORY_REGION_END)

    expected_kinds = ["include", "declaration"] if suffix == ".h" else ["implementation"]
    if kinds != expected_kinds:
        return [], [f"factory regions must be exactly {expected_kinds}, observed {kinds}"]

    return regions, []


# 只有通过结构验证的薄Factory区域才允许从公共IP语义比较中剥离。
def strip_valid_factory_regions(text: str, *, ip: str, suffix: str) -> tuple[str, list[str]]:

    regions, errors = validated_factory_regions(text, ip=ip, suffix=suffix)
    if errors or not regions:
        return text, errors

    parts: list[str] = []
    cursor = 0

    for begin, end in regions:
        parts.append(text[cursor:begin])
        cursor = end

    parts.append(text[cursor:])
    return "".join(parts), []

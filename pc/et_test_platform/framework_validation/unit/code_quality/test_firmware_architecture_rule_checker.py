# Framework Validation测试模块。
#
# 职责：验证test_firmware_architecture_rule_checker 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).parents[5]
CHECKER = ROOT / "tools/quality/check_firmware_architecture_rules.py"
IP_CHANGE_CHECKER = ROOT / "tools/quality/check_ip_change_rules.py"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Firmware architecture checker")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_checker() -> ModuleType:
    return load_module("firmware_arch_checker", CHECKER)


def test_firmware_checker_rejects_cross_ip_wrap(tmp_path: Path) -> None:
    checker = load_checker()
    path = tmp_path / "et_uart_service.c"
    path.write_text('#include "et_dma_wrap.h"\n', encoding="utf-8")
    assert any("ETFW101" in error for error in checker.check_file(path))


def test_firmware_checker_accepts_own_wrap(tmp_path: Path) -> None:
    checker = load_checker()
    path = tmp_path / "et_uart_service.c"
    path.write_text('#include "et_uart_wrap.h"\n', encoding="utf-8")
    assert checker.check_file(path) == []


# 测试Feature：Service头文件和源文件遵守同一跨IP Wrap边界。
#
# 测试方法：在UART Service头文件中包含DMA Wrap，并调用正式检查函数。
#
# 通过条件：头文件中的跨IP依赖产生ETFW101，不能通过移动include绕过门禁。
def test_firmware_checker_rejects_cross_ip_wrap_from_service_header(tmp_path: Path) -> None:

    checker = load_checker()
    path = tmp_path / "et_uart_service.h"
    path.write_text('#include "et_dma_wrap.h"\n', encoding="utf-8")

    assert any("ETFW101" in error for error in checker.check_file(path))


# 测试Feature：普通IP Service可使用受限的Framework Resource公共接口。
#
# 测试方法：构造同时包含本IP Wrap和Resource Wrap的AES Service头文件。
#
# 通过条件：Resource接口不被误判为其他Feature IP Wrap。
def test_firmware_checker_accepts_framework_resource_api(tmp_path: Path) -> None:

    checker = load_checker()
    path = tmp_path / "et_aes_service.h"
    path.write_text(
        '#include "et_aes_wrap.h"\n#include "et_resource_wrap.h"\n',
        encoding="utf-8",
    )

    assert checker.check_file(path) == []


# 测试Feature：公共Wrap只能包含与自身职责对应的Chip Driver头文件。
#
# 测试方法：
# 1. 分别构造使用本IP Driver和跨IP Driver的最小UART Wrap源文件。
# 2. 调用全量软件门禁使用的通用Wrap Driver边界检查函数。
#
# 通过条件：本IP Driver被接受，跨IP Driver被明确拒绝。
def test_firmware_checker_enforces_own_driver_family(tmp_path: Path) -> None:

    checker = load_checker()
    own = tmp_path / "et_uart_wrap.c"
    own.write_text('#include "et6x_uart.h"\n', encoding="utf-8")
    cross_ip = tmp_path / "et_uart_wrap.c"

    assert checker.check_wrap_driver_boundary(own) == []

    cross_ip.write_text('#include "et6x_ahbdma.h"\n', encoding="utf-8")
    errors = checker.check_wrap_driver_boundary(cross_ip)

    assert any("ETFW201" in error for error in errors)
    assert any("cross-IP driver et6x_ahbdma.h" in error for error in errors)


# 测试Feature：公共职责Wrap可以没有具体Chip Driver依赖。
#
# 测试方法：构造只包含自身公共头的Resource Wrap并运行同一检查函数。
#
# 通过条件：没有Chip Driver include时不产生误报。
def test_firmware_checker_accepts_wrap_without_chip_driver(tmp_path: Path) -> None:

    checker = load_checker()
    path = tmp_path / "et_resource_wrap.c"
    path.write_text('#include "et_resource_wrap.h"\n', encoding="utf-8")

    assert checker.check_wrap_driver_boundary(path) == []


# 测试Feature：SYSCNT可以调用承载其实现的Cortex Driver，但仍禁止跨IP Driver。
# 测试方法：先验证真实SDK归属，再逐一注入时钟、系统路由和UART的非法依赖。
# 通过条件：仅Cortex依赖通过，其他依赖均产生ETFW201。
def test_firmware_checker_maps_syscnt_driver_owner(tmp_path: Path) -> None:

    checker = load_checker()
    path = tmp_path / "et_syscnt_wrap.c"
    path.write_text('#include "et6x_cortex.h"\n', encoding="utf-8")
    assert checker.check_wrap_driver_boundary(path) == []

    for family in ("crg", "sysctrl", "uart", "ahbdma"):
        path.write_text(f'#include "et6x_{family}.h"\n', encoding="utf-8")
        assert any("ETFW201" in error for error in checker.check_wrap_driver_boundary(path))


# 测试Feature：公共ETIM与SDK ETIMER名称不同，但仍属于同一IP。
# 测试方法：ETIM Wrap包含自身公共头及真实SDK头，再逐个加入其他IP依赖。
# 通过条件：仅ETIMER通过；其他Timer、路由、DMA等依赖仍精确报ETFW201。
def test_firmware_checker_maps_etim_driver_owner(tmp_path: Path) -> None:

    checker = load_checker()
    path = tmp_path / "et_etim_wrap.c"
    own = '#include "et_etim_wrap.h"\n#include "et6x_etimer.h"\n'
    path.write_text(own, encoding="utf-8")
    assert checker.check_wrap_driver_boundary(path) == []

    for family in ("stimer", "srpwm", "crg", "sysctrl", "interrupt", "gpio", "uart", "ahbdma"):
        path.write_text(own + f'#include "et6x_{family}.h"\n', encoding="utf-8")
        errors = checker.check_wrap_driver_boundary(path)
        assert len(errors) == 1
        assert f"ETFW201 wrap etim includes cross-IP driver et6x_{family}.h" in errors[0]


# 测试Feature：ETIMER的名称映射不能被其他Wrap继承或通过前缀匹配获得。
# 测试方法：在其他真实IP及近似名称Wrap中包含ETIMER SDK头。
# 通过条件：每个非ETIM Wrap均产生一个ETFW201，不扩展跨IP授权。
def test_firmware_checker_keeps_etimer_exclusive_to_etim(tmp_path: Path) -> None:

    checker = load_checker()
    for ip in ("stimer", "srpwm", "gpio", "uart", "dma", "etim_extra", "unknown"):
        path = tmp_path / f"et_{ip}_wrap.c"
        path.write_text('#include "et6x_etimer.h"\n', encoding="utf-8")
        errors = checker.check_wrap_driver_boundary(path)
        assert len(errors) == 1
        assert f"ETFW201 wrap {ip} includes cross-IP driver et6x_etimer.h" in errors[0]


# 测试Feature：所有芯片的Chip Config必须保持为公共Wrap消费的纯编译期事实。
#
# 测试方法：
# 1. 创建一个符合命名和唯一Wrap消费关系的最小Chip Config。
# 2. 直接调用与仓库全量门禁相同的通用检查函数。
#
# 通过条件：合法配置不产生架构违规。
def test_firmware_checker_accepts_bounded_chip_wrap_config(tmp_path: Path) -> None:

    checker = load_checker()
    wrap_root = tmp_path / "wrap"
    wrap_root.mkdir()
    (wrap_root / "et_demo_wrap.c").write_text(
        "static const int demo[] = ET_CHIP_DEMO_MAP_TABLE;\n",
        encoding="utf-8",
    )
    path = tmp_path / "et_chip_wrap_config.h"
    path.write_text(
        "#ifndef DEMO_CHIP_WRAP_CONFIG_H\n"
        "#define DEMO_CHIP_WRAP_CONFIG_H\n"
        "#define ET_CHIP_DEMO_FEATURE_FLAGS 0x01u\n"
        "#define ET_CHIP_DEMO_LIMITS 8u\n"
        "#define ET_CHIP_DEMO_MAP_TABLE "
        "{{0u, DEMO0, ET_CHIP_DEMO_FEATURE_FLAGS, ET_CHIP_DEMO_LIMITS}}\n"
        "#endif\n",
        encoding="utf-8",
    )

    assert checker.check_chip_wrap_config(path, wrap_root) == []


# 测试Feature：Chip Config禁止承载运行时控制流和协议语义。
#
# 测试方法：
# 1. 在最小配置中注入函数、if控制流和Service命令常量。
# 2. 运行通用Chip Config检查函数并收集违规原因。
#
# 通过条件：三个越层事实均被拒绝，不能仅靠文件内注释约束。
def test_firmware_checker_rejects_chip_wrap_config_runtime_logic(tmp_path: Path) -> None:

    checker = load_checker()
    wrap_root = tmp_path / "wrap"
    wrap_root.mkdir()
    path = tmp_path / "et_chip_wrap_config.h"
    path.write_text(
        "#define ET_CHIP_DEMO_MAP_TABLE {{0u, DEMO0}}\n"
        "#define ET_CHIP_DEMO_SERVICE_COMMAND 1u\n"
        "int select_demo(int value) { if (value) { return 1; } return 0; }\n",
        encoding="utf-8",
    )

    errors = checker.check_chip_wrap_config(path, wrap_root)

    assert {error.split(": ", 1)[1].split(" ", 1)[0] for error in errors} >= {
        "ETFW301",
        "ETFW302",
        "ETFW303",
    }
    assert any("runtime control flow" in error for error in errors)
    assert any("function definitions" in error for error in errors)
    assert any("protocol or Case semantics" in error for error in errors)


# 测试Feature：Firmware芯片模板不是一个真实芯片适配，不要求虚构Chip IP文档。
#
# 测试方法：
# 1. 分别向IP变更检查器传入模板路径和真实ET芯片路径。
# 2. 使用同一已知IP集合解析应同步的Chip Contract。
#
# 通过条件：模板返回空集合，真实芯片仍要求同步对应Chip Contract。
def test_ip_change_checker_ignores_chip_template_but_keeps_real_chip() -> None:

    checker = load_module("ip_change_checker", IP_CHANGE_CHECKER)

    assert checker._chip_ips_for_path("firmware/chips/_template/README.md", ("dma",)) == set()
    assert checker._chip_ips_for_path(
        "firmware/chips/et6801/config/et_chip_wrap_config.h", ("dma",)
    ) == {("et6801", "dma")}


# 测试Feature：专用Chip Driver文件只同步自身IP，不受文件内既有跨IP文字影响。
#
# 测试方法：给AES Driver路径传入包含DMA字样的实际变更文本并解析Chip/IP身份。
#
# 通过条件：同步目标只有AES，不会因为历史DMA文字误要求修改DMA芯片文档。
def test_ip_change_checker_prefers_dedicated_file_identity_over_changed_text() -> None:

    checker = load_module("ip_change_checker_dedicated", IP_CHANGE_CHECKER)

    affected = checker._chip_ips_for_path(
        "firmware/chips/et6801/sdk/ET6x_Driver/Src/et6x_aes.c",
        ("aes", "dma"),
        changed_text="DMA request remains supported",
    )

    assert affected == {("et6801", "aes")}


# 测试Feature：通用Chip Config只根据实际Diff行识别需要同步的IP。
#
# 测试方法：模拟同一配置文件包含多个历史IP，但本次Diff只增加AES映射。
#
# 通过条件：只返回AES，不把未修改的CRC/CRG/DMA/UART事实判为本次变化。
def test_ip_change_checker_uses_changed_text_for_generic_chip_config() -> None:

    checker = load_module("ip_change_checker_generic", IP_CHANGE_CHECKER)

    affected = checker._chip_ips_for_path(
        "firmware/chips/et6801/config/et_chip_wrap_config.h",
        ("aes", "crc", "crg", "dma", "uart"),
        changed_text="#define ET_CHIP_AES_MAP_TABLE {{0u, AES_IRQn}}",
    )

    assert affected == {("et6801", "aes")}


# 测试Feature：通用表追加条目时，原末项仅改变容器标点不构成该IP事实变化。
#
# 测试方法：构造DMA末项改为续行并新增AES项的最小Git Diff。
#
# 通过条件：语义Diff只保留新增AES行，不保留内容未变的DMA行。
def test_ip_change_checker_ignores_container_punctuation_only_diff_pair() -> None:

    checker = load_module("ip_change_checker_semantic_diff", IP_CHANGE_CHECKER)
    diff = "\n".join(
        (
            "--- a/et_chip_wrap_config.h",
            "+++ b/et_chip_wrap_config.h",
            "-     {ET_CRG_WRAP_PERIPHERAL_DMA, 1u, CRG_PERIPH_AHBDMA1}}",
            "+     {ET_CRG_WRAP_PERIPHERAL_DMA, 1u, CRG_PERIPH_AHBDMA1}, \\",
            "+     {ET_CRG_WRAP_PERIPHERAL_AES, 0u, CRG_PERIPH_AES}}",
        )
    )

    assert checker._semantic_changed_lines(diff) == [
        "     {ET_CRG_WRAP_PERIPHERAL_AES, 0u, CRG_PERIPH_AES}}"
    ]


# 测试Feature：IP同步门禁忽略C源码纯排版变化。
#
# 测试方法：构造Token完全相同、空白和换行不同的Service代码。
#
# 通过条件：归一化后的公共契约文本完全一致。
def test_ip_change_checker_ignores_c_whitespace_only_changes() -> None:

    checker = load_module("ip_change_checker_c_format", IP_CHANGE_CHECKER)
    before = "if (ready) { return 0; }\n"
    after = "if (ready)\n{\n    return 0;\n}\n"

    assert checker._normalized_c_contract_text(before) == checker._normalized_c_contract_text(after)


# 测试Feature：C预处理续行变化不冒充IP语义变化。
#
# 测试方法：构造宏表达式的反斜杠续行版和单行版。
#
# 通过条件：按C预处理阶段归一化后两段文本一致。
def test_ip_change_checker_ignores_c_preprocessor_line_continuations() -> None:

    checker = load_module("ip_change_checker_c_continuation", IP_CHANGE_CHECKER)
    before = "#define MASK (FLAG_A | \\\n    FLAG_B)\n"
    after = "#define MASK (FLAG_A | FLAG_B)\n"

    assert checker._normalized_c_contract_text(before) == checker._normalized_c_contract_text(after)


# 测试Feature：解释性C注释不冒充IP公共语义变化。
#
# 测试方法：在Token完全相同的代码中增加行注释和块注释。
#
# 通过条件：移除注释并归一化后的公共契约文本完全一致。
def test_ip_change_checker_ignores_c_comment_only_changes() -> None:

    checker = load_module("ip_change_checker_c_comments", IP_CHANGE_CHECKER)
    before = "return value + offset;\n"
    after = "/* calculate final value */\nreturn value /* base */ + offset; // done\n"

    assert checker._normalized_c_contract_text(before) == checker._normalized_c_contract_text(after)


# 测试Feature：字符串和字符字面量中的注释标记保留真实C语义。
#
# 测试方法：分别构造包含双斜线和块注释标记的字符串、字符字面量。
#
# 通过条件：注释扫描只删除真实注释，不修改字面量内容。
def test_ip_change_checker_preserves_comment_markers_inside_c_literals() -> None:

    checker = load_module("ip_change_checker_c_comment_literals", IP_CHANGE_CHECKER)
    source = 'const char *url = "uart://target"; char slash = \'/\'; const char *tag = "/*aes*/";'

    assert checker._strip_c_comments(source) == source


# 测试Feature：不完整块注释必须失败关闭。
#
# 测试方法：输入一个没有结束标记的块注释。
#
# 通过条件：扫描器原样保留输入，不能把非法源码静默归一化。
def test_ip_change_checker_rejects_unterminated_c_block_comment() -> None:

    checker = load_module("ip_change_checker_c_unterminated_comment", IP_CHANGE_CHECKER)
    source = "return 0; /* incomplete"

    assert checker._strip_c_comments(source) == source


# 测试Feature：平台Service工厂胶水不冒充IP Feature契约变化。
#
# 测试方法：在原Service代码后增加一段成对标记的薄工厂实现。
#
# 通过条件：去除工厂区域后的公共IP契约文本保持一致。
def test_ip_change_checker_ignores_marked_service_factory_glue() -> None:

    checker = load_module("ip_change_checker_factory", IP_CHANGE_CHECKER)
    before = "int et_uart_handle(void) { return 0; }\n"
    factory = """
int et_uart_service_create(void *storage, uint16_t instance_id,
                           const et_service_factory_context_t *context,
                           const et_service_descriptor_t **descriptor)
{
    et_uart_service_t *service = (et_uart_service_t *)storage;
    if ((service == NULL) || (context == NULL) || (context->irq_manager == NULL) ||
        (descriptor == NULL))
    {
        return -1;
    }
    if (et_uart_service_init(service, instance_id, context->irq_manager,
                             context->irq_priority) != 0)
    {
        return -1;
    }
    *descriptor = et_uart_service_descriptor(service);
    return (*descriptor == NULL) ? -1 : 0;
}
"""
    after = before + checker._FACTORY_REGION_BEGIN + factory + checker._FACTORY_REGION_END + "\n"

    path = "firmware/services/src/et_uart_service.c"
    assert checker._normalized_c_contract_text(
        before, path=path
    ) == checker._normalized_c_contract_text(after, path=path)


# 测试Feature：不成对的Service工厂标记必须失败关闭。
#
# 测试方法：只增加开始标记并夹带实现代码，不提供结束标记。
#
# 通过条件：门禁保留全部文本并识别为语义变化。
def test_ip_change_checker_rejects_unbalanced_service_factory_markers() -> None:

    checker = load_module("ip_change_checker_factory_invalid", IP_CHANGE_CHECKER)
    before = "int et_uart_handle(void) { return 0; }\n"
    after = before + checker._FACTORY_REGION_BEGIN + "\nint changed(void) { return 1; }\n"

    path = "firmware/services/src/et_uart_service.c"
    assert checker._normalized_c_contract_text(
        before, path=path
    ) != checker._normalized_c_contract_text(after, path=path)


# 测试Feature：完整Marker不能隐藏命令或Feature实现。
#
# 测试方法：在成对Marker中加入额外命令处理调用，并执行架构检查和语义归一化。
#
# 通过条件：架构门禁报ETFW103，IP同步归一化也保留该区域。
def test_factory_marker_rejects_feature_code_even_when_balanced(tmp_path: Path) -> None:

    architecture = load_checker()
    sync_checker = load_module("ip_change_checker_factory_feature", IP_CHANGE_CHECKER)
    path = tmp_path / "et_uart_service.c"
    source = "\n".join(
        (
            sync_checker._FACTORY_REGION_BEGIN,
            "int et_uart_service_create(void) { return et_uart_handle_command(); }",
            sync_checker._FACTORY_REGION_END,
            "",
        )
    )
    path.write_text(source, encoding="utf-8")

    assert any("ETFW103" in error for error in architecture.check_service_factory_contract(path))
    normalized = sync_checker._normalized_c_contract_text(
        source, path="firmware/services/src/et_uart_service.c"
    )
    assert "et_uart_handle_command" in normalized

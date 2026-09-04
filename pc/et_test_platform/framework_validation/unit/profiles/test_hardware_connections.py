# 简化硬件连接配置的软件回归。
# 职责：验证单环境生效、handle/GPIO读取和Case内冲突。
# 边界：不操作硬件，不宣称GPIO复用或真实连线已经验证。
# 依赖：pytest、PyYAML和Profile读取入口。

from pathlib import Path

import pytest
import yaml

from et_test_platform.core.errors import ConfigurationError
from et_test_platform.profiles import hardware_connections
from et_test_platform.profiles.capabilities import ChipCapabilities, load_packaged_chip_capabilities
from et_test_platform.profiles.hardware_connections import load_hardware_connections

PROFILE = (
    Path(hardware_connections.__file__).parent
    / "bench_topologies"
    / "et6801_hardware_connections.yaml"
)


# 使用真实Capability检查实例，不用宽松替身代替。
@pytest.fixture(scope="module")
def caps() -> ChipCapabilities:

    return load_packaged_chip_capabilities("et6801")


# 每个测试只修改配置副本。
@pytest.fixture
def raw() -> dict:

    return yaml.safe_load(PROFILE.read_text(encoding="utf-8"))


# 临时文件用于验证人工编辑配置的效果。
def _write(tmp_path: Path, raw: dict) -> Path:

    path = tmp_path / "connections.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    return path


# 直接取得handle和GPIO，不需要二次查询路由目录。
def test_packaged_configuration(
    caps: ChipCapabilities, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:

    # 更换启动目录后仍从包内固定位置读取，不从当前目录寻找同名配置。
    monkeypatch.chdir(tmp_path)
    config = load_hardware_connections(capabilities=caps, expected_lane="fpga")
    selected = config.select("spi", "uart")
    assert config.lane == "fpga"
    assert selected["spi"]["dut"].handle == "spi0"
    assert selected["spi"]["dut"].gpio == {"clk": 60, "cs": 61, "mosi": 16, "miso": 55}
    assert selected["spi"]["ref"].handle == "spi1"
    assert selected["spi"]["ref"].gpio == {"clk": 65, "cs": 66, "mosi": 63, "miso": 64}
    assert selected["uart"]["dut"].handle == "uart1"
    assert selected["uart"]["dut"].gpio == {"tx": 44, "rx": 45}
    assert selected["uart"]["ref"].handle == "uart2"
    assert selected["uart"]["ref"].gpio == {"tx": 8, "rx": 9}
    with pytest.raises(TypeError):
        selected["spi"]["dut"].gpio["clk"] = 0
    with pytest.raises(TypeError):
        selected["spi"]["dut"] = selected["spi"]["ref"]


# 两套不同配置同时保存在文件中，只加载active指定的那套。
@pytest.mark.parametrize("active", ["fpga", "silicon"])
def test_one_active_environment(
    tmp_path: Path, raw: dict, caps: ChipCapabilities, active: str
) -> None:

    raw["silicon"] = {"spi": {"dut": {"handle": "spi2", "gpio": {"clk": 10}}}}
    raw["active"] = active
    config = load_hardware_connections(_write(tmp_path, raw), capabilities=caps)
    dut = config.select("spi")["spi"]["dut"]
    assert (dut.handle, dut.gpio["clk"]) == (("spi0", 60) if active == "fpga" else ("spi2", 10))
    assert ("uart" in config.ips) == (active == "fpga")


# 空硅后区不回退；未激活的错误实例不参与本次解析，切换后才报错。
def test_no_fallback_or_inactive_instance_loading(
    tmp_path: Path, raw: dict, caps: ChipCapabilities
) -> None:

    raw["active"] = "silicon"
    config = load_hardware_connections(_write(tmp_path, raw), capabilities=caps)
    with pytest.raises(ConfigurationError, match="not configured"):
        config.select("spi")
    raw["silicon"] = {"spi": {"dut": {"handle": "spi99", "gpio": {}}}}
    raw["active"] = "fpga"
    assert load_hardware_connections(_write(tmp_path, raw), capabilities=caps).select("spi")
    raw["active"] = "silicon"
    with pytest.raises(ConfigurationError, match="handle"):
        load_hardware_connections(_write(tmp_path, raw), capabilities=caps)


# 运行目标只做一致性检查，不能覆盖active。
def test_lane_mismatch(caps: ChipCapabilities) -> None:

    with pytest.raises(ConfigurationError, match="does not match"):
        load_hardware_connections(PROFILE, capabilities=caps, expected_lane="silicon")


# 跨Case复用合法；同一Case同时选中冲突引脚时拒绝，并且不遗留占用状态。
def test_local_conflicts(tmp_path: Path, raw: dict, caps: ChipCapabilities) -> None:

    raw["fpga"]["uart"]["dut"]["gpio"]["tx"] = 60
    config = load_hardware_connections(_write(tmp_path, raw), capabilities=caps)
    assert config.select("spi")
    assert config.select("uart")
    with pytest.raises(ConfigurationError, match="GPIO60 conflict"):
        config.select("spi", "uart")
    assert config.select("spi")
    raw["fpga"]["spi"]["ref"]["gpio"]["clk"] = 60
    config = load_hardware_connections(_write(tmp_path, raw), capabilities=caps)
    with pytest.raises(ConfigurationError, match="GPIO60 conflict"):
        config.select("spi")


# 换角色只改配置，handle和GPIO一起变更。
def test_swap_roles(tmp_path: Path, raw: dict, caps: ChipCapabilities) -> None:

    spi = raw["fpga"]["spi"]
    spi["dut"], spi["ref"] = spi["ref"], spi["dut"]
    config = load_hardware_connections(_write(tmp_path, raw), capabilities=caps)
    assert config.select("spi")["spi"]["dut"].handle == "spi1"
    assert config.select("spi")["spi"]["dut"].gpio["clk"] == 65


# 拒绝多选环境、错误类型和旧版遗留字段。
@pytest.mark.parametrize(
    ("section", "key", "value", "error"),
    [
        ("root", "active", ["fpga", "silicon"], "exactly one"),
        ("root", "active", "both", "exactly one"),
        ("root", "active", None, "exactly one"),
        ("root", "active", True, "exactly one"),
        ("root", "chip", "wrong_chip", "chip mismatch"),
        ("root", "routes", {}, "fields"),
        ("root", "fpga", [], "mapping"),
        ("fpga", "unknown_ip", {}, "unknown Capability IP"),
        ("fpga", "spi", {}, "at least one role"),
        ("endpoint", "handle", "spi99", "handle"),
        ("endpoint", "handle", "uart1", "handle"),
        ("endpoint", "handle", 0, "handle"),
        ("endpoint", "gpio", {"clk": -1}, "integer"),
        ("endpoint", "gpio", {"clk": True}, "integer"),
        ("endpoint", "gpio", {"clk": "60"}, "integer"),
        ("endpoint", "gpio", {"clk": 1.5}, "integer"),
        ("endpoint", "gpio", [], "mapping"),
        ("endpoint", "mux", 15, "fields"),
        ("endpoint", "wired", True, "fields"),
    ],
)
def test_invalid_configuration(
    tmp_path: Path,
    raw: dict,
    caps: ChipCapabilities,
    section: str,
    key: str,
    value: object,
    error: str,
) -> None:

    objects = {"root": raw, "fpga": raw["fpga"], "endpoint": raw["fpga"]["spi"]["dut"]}
    objects[section][key] = value
    with pytest.raises(ConfigurationError, match=error):
        load_hardware_connections(_write(tmp_path, raw), capabilities=caps)


# 重复键、破损YAML和编码错误不能被静默接受。
@pytest.mark.parametrize("data", [b"active: fpga\nactive: silicon", b"[broken", b"\xff"])
def test_invalid_yaml(tmp_path: Path, caps: ChipCapabilities, data: bytes) -> None:

    path = tmp_path / "invalid.yaml"
    path.write_bytes(data)
    with pytest.raises(ConfigurationError):
        load_hardware_connections(path, capabilities=caps)


# 缺文件、重复或未知IP选择都有明确错误。
def test_missing_input(tmp_path: Path, caps: ChipCapabilities) -> None:

    with pytest.raises(ConfigurationError, match="cannot load"):
        load_hardware_connections(tmp_path / "absent.yaml", capabilities=caps)
    config = load_hardware_connections(PROFILE, capabilities=caps)
    for names in ((), ("spi", "spi"), ("missing",)):
        with pytest.raises(ConfigurationError):
            config.select(*names)

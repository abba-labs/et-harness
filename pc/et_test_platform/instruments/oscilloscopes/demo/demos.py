# MSO5204 常用功能演示集。
#
# 职责：用可直接运行的最小示例覆盖日常测试场景，每个示例自包含、互不依赖。
# 边界：只演示调用方式与结果解读，不做 PASS/FAIL 判定，也不编排跨仪器流程。
# 依赖：仅依赖本库公开 API；运行需真实示波器在线（见 SCOPE_RESOURCE）。

from __future__ import annotations

import sys
import time
from contextlib import suppress
from pathlib import Path

from ..mso5204.models import (
    Mso5204AcquireType,
    Mso5204MeasurementItem,
    Mso5204MemoryDepth,
    Mso5204TriggerSlope,
    Mso5204TriggerSweep,
)
from ..wrapper import (
    Mso5204AcquireConfig,
    Mso5204TriggerConfig,
    Wave,
    dead_time_s,
    edge_offset_s,
    open_scope,
)

# 当前台架示波器地址；IP 由 DHCP 分配，换机器或重启示波器后需重新发现。
# 发现方法：python srpwm_bench/find_scope.py
SCOPE_RESOURCE = "TCPIP0::169.254.201.131::INSTR"

# 各示例共用的采集时基：50us/div，10kHz 方波一个周期约占 2 格，便于观察。
DEFAULT_TIME_SCALE_S = 5e-5

# 截图和波形的输出目录；仓库内 tmp/ 是唯一允许的本地草稿区。
OUTPUT_DIR = Path("tmp/mso5204_demo")


# ---------------------------------------------------------------- 基础用法


# 示例 1：连接仪器并读取身份；用于确认连到的是预期设备。
def demo_01_connect_and_identify() -> None:
    # 推荐用 with：出了异常也能保证关闭连接，不会把 VISA 链路漏在打开状态。
    with open_scope(SCOPE_RESOURCE) as scope:
        print("资源标识:", scope.identity)
        print("设备身份:", scope.identify())
        print("默认通道:", scope.channel)
        print("当前错误:", scope.last_error())


# 示例 2：一次配好通道与时基，然后读几个常用测量项。
def demo_02_basic_measure() -> None:
    with open_scope(SCOPE_RESOURCE) as scope:
        # prepare 会配置通道量程、时基、EDGE 触发并启动采集，最后等待稳定。
        scope.prepare(time_scale_s=DEFAULT_TIME_SCALE_S)

        # measure 接受枚举或 SCPI 风格字符串；无效测量返回 None。
        freq = scope.measure(Mso5204MeasurementItem.FREQUENCY)
        vpp = scope.measure("VPP")
        duty = scope.measure(Mso5204MeasurementItem.POSITIVE_DUTY)

        print(f"频率   : {freq} Hz")
        print(f"峰峰值 : {vpp} V")
        print(f"正占空比: {duty}  <- 注意：仪器返回的是比值(0~1)，不是百分比")
        if duty is not None:
            print(f"换算成百分比: {duty * 100:.2f} %")

        # 用波形自算的占空比做对照，可确认上述单位差异（波形法给的是百分比）。
        wave_duty = scope.read_wave().duty_percent()
        print(f"波形自算占空比: {wave_duty:.2f} %（Wave.duty_percent 返回百分比）")
        print("提示: 返回 None 表示仪器给了无效哨兵 9.9E+37（通常是没有有效波形）")


# 示例 3：读屏幕波形并直接做物理量分析，演示电平/周期/占空比/边沿的算法。
def demo_03_screen_waveform_analysis() -> None:
    with open_scope(SCOPE_RESOURCE) as scope:
        scope.prepare(time_scale_s=DEFAULT_TIME_SCALE_S)

        # read_wave 返回可直接分析的 Wave，已按 preamble 换算成物理单位。
        wave = scope.read_wave()

        low, high = wave.levels()
        print(f"采样点 : {len(wave)} 点, 间隔 {wave.x_increment_s:.3e} s")
        print(f"电平   : {low:.3f} ~ {high:.3f} V")
        print(f"周期   : {wave.period_s()!r}")
        print(f"频率   : {wave.frequency_hz()!r} Hz")
        print(f"占空比 : {wave.duty_percent()!r} %")

        # 边沿定位：crossings 给下标，edges 给下标+时间。
        mid = (low + high) / 2.0
        indexes = wave.crossings(mid, rising=True)
        print(f"上升沿下标: {indexes[:8]}{' ...' if len(indexes) > 8 else ''}")
        print(f"上升沿个数: {len(wave.edges(rising=True))}")


# 示例 4：读 RAW 深存储波形；测 ns 级细节必须用这条路径。
def demo_04_raw_deep_memory() -> None:
    with open_scope(SCOPE_RESOURCE) as scope:
        scope.prepare(time_scale_s=DEFAULT_TIME_SCALE_S)

        # read_wave_raw 内部会：等采集就绪 -> STOP -> 读数据 -> 读 preamble -> 恢复 RUN。
        # 不要在 RUN 状态下自己读 RAW，实测会阻塞到超时（60s）。
        started = time.monotonic()
        wave = scope.read_wave_raw(read_timeout_s=30.0)
        elapsed = time.monotonic() - started

        print(f"采样点 : {len(wave)} 点")
        print(f"分辨率 : {wave.x_increment_s:.3e} s/点")
        print(f"时长   : {wave.duration_s * 1e6:.1f} us")
        print(f"耗时   : {elapsed:.2f} s")
        print(f"频率   : {wave.frequency_hz()!r} Hz")
        print(f"占空比 : {wave.duty_percent()!r} %")


# 示例 5：用显式配置改触发；None 字段保持仪器当前状态不变。
def demo_05_configure_trigger() -> None:
    with open_scope(SCOPE_RESOURCE) as scope:
        scope.prepare(time_scale_s=DEFAULT_TIME_SCALE_S)

        # 只改想改的字段，其余不动。扫描方式会被放到最后下发。
        scope.configure_trigger(
            Mso5204TriggerConfig(
                sweep=Mso5204TriggerSweep.NORMAL,
                edge_slope=Mso5204TriggerSlope.RISING,
                edge_level_v=1.5,
            )
        )
        driver = scope.driver
        print("触发模式:", driver.trigger.mode_get())
        print("扫描方式:", driver.trigger.sweep_get())
        print("触发源  :", driver.trigger.edge_source_get())
        print("斜率    :", driver.trigger.edge_slope_get())
        print("电平    :", driver.trigger.edge_level_get())

        # 单次采集：SINGle 会立即武装，因此必须在其它触发参数之后设置。
        scope.configure_trigger(Mso5204TriggerConfig(sweep=Mso5204TriggerSweep.SINGLE))
        print("已武装单次采集，触发状态:", driver.trigger.status_get())


# 示例 6：配置采集模式；平均次数只在 AVERAGE 类型下合法。
def demo_06_configure_acquire() -> None:
    with open_scope(SCOPE_RESOURCE) as scope:
        scope.prepare(time_scale_s=DEFAULT_TIME_SCALE_S)

        # 平均采集能压制随机噪声，但会降低刷新率，适合稳定的周期信号。
        scope.configure_acquire(
            Mso5204AcquireConfig(
                acquire_type=Mso5204AcquireType.AVERAGE,
                average_count=16,
                memory_depth=Mso5204MemoryDepth.PTS_1M,
            )
        )
        driver = scope.driver
        print("采集类型:", driver.acquire.type_get())
        print("平均次数:", driver.acquire.averages_get())
        print("存储深度:", driver.acquire.memory_depth_get())
        print("采样率  :", driver.acquire.sample_rate_get(), "Sa/s")

        # 恢复普通采集，避免影响后续示例。
        scope.configure_acquire(Mso5204AcquireConfig(acquire_type=Mso5204AcquireType.NORMAL))

        # 非 AVERAGE 类型配平均次数会被拒绝（在设备 I/O 之前失败）。
        try:
            scope.configure_acquire(Mso5204AcquireConfig(average_count=8))
        except ValueError as exc:
            print("预期被拒绝:", exc)


# 示例 7：一次读取完整测量快照；适合记录一份测试现场。
def demo_07_measure_snapshot() -> None:
    with open_scope(SCOPE_RESOURCE) as scope:
        scope.prepare(time_scale_s=DEFAULT_TIME_SCALE_S)

        snap = scope.measure_signal()
        print(f"频率    : {snap.frequency_hz} Hz")
        print(f"周期    : {snap.period_s} s")
        print(f"占空比  : {snap.duty_cycle_percent}  <- 仪器原值，是比值(0~1)")
        print(f"峰峰值  : {snap.vpp_v} V")
        print(f"有效值  : {snap.vrms_v} V")
        print(f"上升时间: {snap.rise_time_s} s")
        print(f"下降时间: {snap.fall_time_s} s")
        print("提示: 该字段名带 percent 但仪器实测返回比值；")
        print("      需要百分比时请用 scope.read_wave().duty_percent()")


# 示例 8：跨通道延迟/相位测量；自动配置 A/B 源。
def demo_08_cross_channel_delay() -> None:
    with open_scope(SCOPE_RESOURCE) as scope:
        scope.prepare(time_scale_s=DEFAULT_TIME_SCALE_S)

        # 跨通道延迟/相位项必须先设 A/B 源，否则会沿用仪器上遗留的配对，结果静默错配。
        # measure_delay 会自动先配源再查询。
        delay = scope.measure_delay(Mso5204MeasurementItem.FF_DELAY, 1, 2)
        phase = scope.measure_delay(Mso5204MeasurementItem.FF_PHASE, 1, 2)
        print(f"CH1->CH2 下降沿延迟: {delay} s")
        print(f"CH1->CH2 下降沿相位: {phase} °")
        if delay is None:
            print("提示: None 通常是 CH2 上没有有效信号")


# 示例 9：统计测量；打开统计后读取极值/平均，用于观察抖动与稳定性。
def demo_09_statistics() -> None:
    with open_scope(SCOPE_RESOURCE) as scope:
        scope.prepare(time_scale_s=DEFAULT_TIME_SCALE_S)

        # 统计需要仪器侧先打开统计显示并启用对应测量项，这里只演示读取。
        scope.driver.measurement.statistics_display_set(True)
        scope.driver.measurement.statistics_item_enable("FREQuency", "CHANnel1")
        scope.driver.measurement.statistics_reset()
        time.sleep(1.0)

        for statistic in ("MAXimum", "MINimum", "AVERages"):
            value = scope.measure_statistic(statistic, "FREQuency")
            print(f"频率{statistic:>8}: {value} Hz")

        scope.driver.measurement.statistics_display_set(False)


# 示例 10：保存屏幕截图存证；仪器返回 BMP 数据，直接落盘供记录留档。
def demo_10_screenshot() -> None:
    with open_scope(SCOPE_RESOURCE) as scope:
        scope.prepare(time_scale_s=DEFAULT_TIME_SCALE_S)

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        target = OUTPUT_DIR / "screenshot.bmp"
        # 仪器返回的是 BMP 数据，这里原样落盘；目录不存在会自动创建。
        written = scope.screenshot(target)
        print(f"已写入 {target} ({written} 字节)")


# 示例 11：检查错误队列；SCPI 是被动协议，配错参数不会主动报错。
def demo_11_error_queue() -> None:
    with open_scope(SCOPE_RESOURCE) as scope:
        scope.prepare(time_scale_s=DEFAULT_TIME_SCALE_S)
        code, message = scope.last_error()
        print(f"错误队列: code={code} message={message}")
        print("提示: 每次批量改配置后查一次，能确认命令真的被仪器接受")


# 示例 12：异常处理；所有仪器异常都继承 OscilloscopeError。
def demo_12_exception_handling() -> None:
    from .._internal import InstrumentProtocolError, OscilloscopeError, OscilloscopeTimeout

    # 故意用一个不存在的地址，演示连接失败的处理方式。
    bad_scope = open_scope("TCPIP0::192.0.2.1::INSTR", timeout_s=2.0)
    try:
        bad_scope.open()
        print("意外连上了（本示例预期失败）")
    except OscilloscopeTimeout as exc:
        print("连接超时:", exc)
    except InstrumentProtocolError as exc:
        print("协议错误:", exc)
    except OscilloscopeError as exc:
        print("其他仪器错误:", type(exc).__name__, exc)
    finally:
        # close 在未打开时也安全，且不得掩盖上面的原始异常。
        with suppress(OscilloscopeError):
            bad_scope.close()

    # 正常连接下的超时处理示例。
    with open_scope(SCOPE_RESOURCE) as scope:
        scope.prepare(time_scale_s=DEFAULT_TIME_SCALE_S)
        print("正常连接的采集状态:", scope.driver.trigger.status_get())


# 示例 13：直接使用官方原子 API；便捷层没覆盖的能力从这里进。
def demo_13_atomic_api() -> None:
    with open_scope(SCOPE_RESOURCE) as scope:
        driver = scope.driver

        # 原子层一条方法对应一条 SCPI 命令：_set 写、_get 读。
        driver.channel.display_set(1, True)
        driver.channel.coupling_set(1, "DC")
        driver.channel.scale_set(1, 1.0)
        driver.channel.offset_set(1, 0.0)

        driver.timebase.mode_set("MAIN")
        driver.timebase.main_scale_set(DEFAULT_TIME_SCALE_S)

        # 注意 edge_source_set 要求 SCPI 记号，传整数会被校验拒绝。
        driver.trigger.mode_set("EDGE")
        driver.trigger.edge_source_set("CHANnel1")
        driver.trigger.edge_level_set(1.5)

        driver.basic.run()
        time.sleep(0.5)

        print("通道1量程:", driver.channel.scale_get(1), "V/div")
        print("通道1耦合:", driver.channel.coupling_get(1))
        print("主时基    :", driver.timebase.main_scale_get(), "s/div")
        print("触发源    :", driver.trigger.edge_source_get())
        print("通道数    :", driver.system.analog_channel_count_get())

        # 故意传错类型，看官方校验如何失败关闭。
        try:
            driver.trigger.edge_source_set(1)
        except ValueError as exc:
            print("预期被拒绝:", exc)


# 示例 14：双通道波形比较，算相位差与死区，并提示串扰导致的误读风险。
def demo_14_two_channel_compare() -> None:
    with open_scope(SCOPE_RESOURCE) as scope:
        scope.prepare(time_scale_s=DEFAULT_TIME_SCALE_S)

        wave_a = scope.read_wave(1)
        wave_b = scope.read_wave(2)

        span_a = wave_a.levels()[1] - wave_a.levels()[0]
        span_b = wave_b.levels()[1] - wave_b.levels()[0]
        print(
            f"CH1 幅度: {span_a:.3f} V, 频率 {wave_a.frequency_hz()!r} Hz, "
            f"占空比 {wave_a.duty_percent()!r} %"
        )
        print(
            f"CH2 幅度: {span_b:.3f} V, 频率 {wave_b.frequency_hz()!r} Hz, "
            f"占空比 {wave_b.duty_percent()!r} %"
        )

        # 幅度过小时 CH2 很可能只是串扰而非真实信号，此时相位/死区结论不可信。
        if span_b < 1.0:
            print(f"注意: CH2 幅度仅 {span_b:.3f} V，疑似串扰而非真实信号；")
            print("      下面的相位与死区读数仅供参考，请先确认 CH2 已接入有效激励。")

        # edge_offset_s 按周期对齐，不会凭空带上整数个周期。
        offset = edge_offset_s(wave_a, wave_b)
        print(f"边沿时间差: {offset} s")
        if offset is None:
            print("提示: None 表示某一路没有足够边沿（CH2 可能无信号）")

        # dead_time_s 取最小间隔，避开跨周期误配；两路时基不同时返回 None。
        dead = dead_time_s(wave_a, wave_b)
        print(f"互补死区  : {dead} s")

        # 合成数据演示：不依赖台架真实激励即可验证分析函数的语义。
        # A 每周期 5 高 5 低；B 延迟 6 点，于是 A 下降后 1 点 B 才上升。
        synthetic_a = _make_wave(high_count=5, low_count=5, periods=4)
        synthetic_b = _make_wave(high_count=5, low_count=5, periods=4, delay=6)
        print(f"合成波形死区: {dead_time_s(synthetic_a, synthetic_b)} s（预期 1e-06）")


# 示例 15：把两路波形分到上下半屏，避免都以 offset=0 居中而完全重叠。
def demo_15_split_channels() -> None:
    with open_scope(SCOPE_RESOURCE) as scope:
        scope.prepare(time_scale_s=DEFAULT_TIME_SCALE_S)
        d = scope.driver
        d.channel.display_set(1, True)
        d.channel.display_set(2, True)

        # 先重置成"重叠"状态，便于对比。
        d.channel.scale_set(1, 1.0)
        d.channel.offset_set(1, 0.0)
        d.channel.scale_set(2, 1.0)
        d.channel.offset_set(2, 0.0)
        print("已重置为重叠状态（两路 scale=1V/div offset=0）")

        # 自动排布：CH2 在上半屏、CH1 在下半屏。
        # 接口会按各路的 VMAX/VMIN 自动选量程，算出互不重叠的偏移。
        layout = scope.split_channels(upper=2, lower=1)

        print("\n排布结果:")
        for label, placement in (("上半屏", layout.upper), ("下半屏", layout.lower)):
            print(
                f"  {label} CH{placement.channel}: "
                f"scale={placement.scale_v} V/div  offset={placement.offset_v:+.4f} V"
            )
        print(f"  屏幕格数: {layout.divisions}")
        print(f"  仪器错误: {scope.last_error()}")

        # 回读确认仪器真的接受了设置。
        for channel in (1, 2):
            print(
                f"  回读 CH{channel}: scale={d.channel.scale_get(channel)} "
                f"offset={d.channel.offset_get(channel):+.4f}"
            )

        # 存一张截图，肉眼确认两路确实分开了。
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        target = OUTPUT_DIR / "split_channels.bmp"
        scope.screenshot(target)
        print(f"\n截图已存: {target}")


# 按给定占空比生成方波，用于在没有真实激励时验证分析函数；delay 为起点偏移点数。
def _make_wave(
    *,
    high_count: int,
    low_count: int,
    periods: int,
    delay: int = 0,
) -> Wave:
    samples: list[float] = [0.0] * delay
    for _ in range(periods):
        samples.extend([3.3] * high_count)
        samples.extend([0.0] * low_count)
    return Wave(samples=tuple(samples), x_increment_s=1e-6)


# ---------------------------------------------------------------- 入口


# 注册全部示例；键为编号，值为 (说明, 函数)。新增示例只需在这里登记。
DEMOS = {
    "1": ("连接与身份识别", demo_01_connect_and_identify),
    "2": ("基础测量（频率/幅值/占空比）", demo_02_basic_measure),
    "3": ("屏幕波形读取与物理量分析", demo_03_screen_waveform_analysis),
    "4": ("RAW 深存储读取（ns 级细节）", demo_04_raw_deep_memory),
    "5": ("触发配置", demo_05_configure_trigger),
    "6": ("采集配置（平均/存储深度）", demo_06_configure_acquire),
    "7": ("完整测量快照", demo_07_measure_snapshot),
    "8": ("跨通道延迟/相位", demo_08_cross_channel_delay),
    "9": ("统计测量", demo_09_statistics),
    "10": ("屏幕截图存证", demo_10_screenshot),
    "11": ("错误队列检查", demo_11_error_queue),
    "12": ("异常处理", demo_12_exception_handling),
    "13": ("官方原子 API", demo_13_atomic_api),
    "14": ("双通道波形比较", demo_14_two_channel_compare),
    "15": ("双通道上下分离（split_channels）", demo_15_split_channels),
}


# 运行指定编号的示例；传 "all" 顺序跑完全部。
def run(selection: str) -> int:
    if selection == "all":
        targets = list(DEMOS)
    elif selection in DEMOS:
        targets = [selection]
    else:
        print(f"未知示例编号 {selection!r}；用 --list 查看可用示例")
        return 2

    failures = 0
    for key in targets:
        label, func = DEMOS[key]
        print(f"\n{'=' * 70}\n示例 {key}: {label}\n{'=' * 70}")
        try:
            func()
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"[失败] {type(exc).__name__}: {exc}")
    print(f"\n{'=' * 70}\n共运行 {len(targets)} 个示例，失败 {failures} 个\n{'=' * 70}")
    return 1 if failures else 0


# 打印示例清单与使用说明；无参数或 --list 时只列清单，否则运行指定示例。
def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv

    if not args or args[0] in ("--list", "-l"):
        print("MSO5204 演示集；用法: python -m ... <编号|all>")
        for key, (label, _) in DEMOS.items():
            print(f"  {key:>2}. {label}")
        print("\n示例: python -m oscilloscopes.demo.demos 4")
        return 0 if args else 0

    return run(args[0])


if __name__ == "__main__":
    raise SystemExit(main())

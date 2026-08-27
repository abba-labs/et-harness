# Framework Validation测试模块。
#
# 职责：验证test_target_connection 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from et_test_platform.profiles.bench import SerialTargetConfig
from et_test_platform.scheduling.target_connection import create_serial_target_client


def test_serial_target_client_is_built_from_validated_bench_config() -> None:
    config = SerialTargetConfig(
        target_id="dut",
        chip_id="et6801",
        firmware_build_id="test-build",
        port="COM_TEST",
        baudrate=460800,
        bytesize=8,
        parity="N",
        stopbits=1,
        dtr=False,
        rts=True,
        request_timeout_s=0.25,
    )

    target = create_serial_target_client(config)

    assert target.identity == "serial:COM_TEST@460800"

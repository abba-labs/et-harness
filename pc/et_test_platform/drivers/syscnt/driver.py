# SYSCNT单IP原子Driver。
# 职责：公开九条原子动作，严格验证响应，不隐式组合测试流程。
# 边界：不配置其他IP、不建立Case基线、不决定PASS。
# 依赖：本IPCodec及具有超时边界的TargetClient。

from ...clients.target import TargetClient
from ...core.errors import ProtocolError
from . import codec, contract
from .contract import SYSCNT_SERVICE_ID, SyscntCommand
from .models import (
    SyscntCapabilities,
    SyscntControl,
    SyscntHaltPolicy,
    SyscntReferenceSample,
    SyscntView,
)


# 每个对象绑定一个逻辑实例；单次命令不隐式改变其他控制状态。
class SyscntDriver:
    # 构造只校验实例，不读取硬件。
    def __init__(self, target: TargetClient, instance_id: int) -> None:
        codec.encode_uint(instance_id, contract.BYTE)
        self._target = target
        self.instance_id = instance_id

    # 查询固件发布的原子动作、计数宽度和读取窗口，不进行任何硬件初始化。
    # 只等待单次响应；超时、Target拒绝或非法响应直接上抛。
    def capabilities_get(self, *, timeout_s: float | None = None) -> SyscntCapabilities:
        return codec.decode_capabilities(
            self._request(SyscntCommand.CAPABILITIES_GET, timeout_s=timeout_s)
        )

    # 只改变使能位，不清零计数；等待单次响应，错误直接上抛。
    def enable_set(self, enabled: bool, *, timeout_s: float | None = None) -> None:
        self._set_bool(SyscntCommand.ENABLE_SET, enabled, timeout_s)

    # 停止时装载初值，运行时固件拒绝；不自动停止或重新启动。
    # 等待单次响应；通信失败和Target拒绝直接上抛。
    def value_load(self, value: int, *, timeout_s: float | None = None) -> None:
        self._write(SyscntCommand.VALUE_LOAD, codec.encode_uint(value, contract.COUNT), timeout_s)

    # 读取指定窗口的连贯值；单次请求超时或撕裂读取失败直接上抛。
    def count_get(
        self, view: SyscntView = SyscntView.READ, *, timeout_s: float | None = None
    ) -> int:
        if not isinstance(view, SyscntView):
            raise ValueError("view must be SyscntView")
        body = self._request(SyscntCommand.COUNT_GET, contract.BYTE.pack(view), timeout_s=timeout_s)
        return codec.decode_words(body, contract.COUNT)[0]

    # 获取真实控制/状态；等待单次响应，不使用请求缓存代替读回。
    # 非法响应、通信失败或Target拒绝直接上抛。
    def control_get(self, *, timeout_s: float | None = None) -> SyscntControl:
        return codec.decode_control(self._request(SyscntCommand.CONTROL_GET, timeout_s=timeout_s))

    # 只设置本IP策略；不设置系统路由、不停核，单次响应失败直接上抛。
    def halt_policy_set(self, policy: SyscntHaltPolicy, *, timeout_s: float | None = None) -> None:
        if not isinstance(policy, SyscntHaltPolicy):
            raise ValueError("policy must be SyscntHaltPolicy")
        self._write(SyscntCommand.HALT_POLICY_SET, contract.BYTE.pack(policy), timeout_s)

    # 只登记非零Hz信息，不改变输入时钟；单次响应超时或拒绝直接上抛。
    def frequency_id_set(self, frequency_hz: int, *, timeout_s: float | None = None) -> None:
        payload = codec.encode_uint(frequency_hz, contract.WORD)
        if frequency_hz == 0:
            raise ValueError("frequency ID must be nonzero")
        self._write(SyscntCommand.FREQUENCY_ID_SET, payload, timeout_s)

    # 显式借用/释放参考计数器，不清零参考；等待单次响应，失败直接上抛。
    def reference_enable_set(self, enabled: bool, *, timeout_s: float | None = None) -> None:
        self._set_bool(SyscntCommand.REFERENCE_ENABLE_SET, enabled, timeout_s)

    # 返回参考前值/本IP值/参考后值，不等待测试窗口；单次响应失败直接上抛。
    def reference_sample_get(self, *, timeout_s: float | None = None) -> SyscntReferenceSample:
        return codec.decode_reference(
            self._request(SyscntCommand.REFERENCE_SAMPLE_GET, timeout_s=timeout_s)
        )

    # Boolean命令使用同一个严格边界，不把任意整数转换成True。
    def _set_bool(self, command: SyscntCommand, enabled: bool, timeout_s: float | None) -> None:
        if type(enabled) is not bool:
            raise ValueError("enabled must be bool")
        self._write(command, contract.BYTE.pack(enabled), timeout_s)

    # 所有写响应必须为空，避免固件/PC契约错配被静默接受。
    def _write(self, command: SyscntCommand, payload: bytes, timeout_s: float | None) -> None:
        if self._request(command, payload, timeout_s=timeout_s):
            raise ProtocolError(f"SYSCNT {command.name} returned an unexpected body")

    # 每次请求带实例前缀；仅只读命令可按既有Target策略重试。
    def _request(
        self, command: SyscntCommand, payload: bytes = b"", *, timeout_s: float | None = None
    ) -> bytes:
        message, _ = self._target.request(
            SYSCNT_SERVICE_ID,
            int(command),
            instance_id=self.instance_id,
            body=contract.BYTE.pack(self.instance_id) + payload,
            timeout_s=timeout_s,
            retry_safe=command
            in (
                SyscntCommand.CAPABILITIES_GET,
                SyscntCommand.COUNT_GET,
                SyscntCommand.CONTROL_GET,
                SyscntCommand.REFERENCE_SAMPLE_GET,
            ),
        )
        return message.body

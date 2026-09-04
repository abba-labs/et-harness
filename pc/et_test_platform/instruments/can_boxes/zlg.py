# ZLG CAN FD盒子的独立设备Adapter。
# 职责：配置指定盒子通道，收发Classic/FD帧，返回真实接收和错误信息。
# 边界：不扫描替代设备、不实现DUT测试流程、不把入队成功当成总线成功。
# 依赖：本包稳定模型和私有ZLG ABI。

from __future__ import annotations

import ctypes as ct
import math
import time
from dataclasses import dataclass
from pathlib import Path

from . import _zlg_abi as abi
from .models import CanBusConfig, CanFrame, CanReceivedFrame


# CAN0/CAN1直接对应厂商零基通道0/1；路径、设备索引和串号由运行配置注入。
@dataclass(frozen=True, slots=True)
class ZlgConnection:
    library: Path
    device_type: str
    device_index: int
    channel: int
    termination: bool
    serial: str = ""

    # 在任何硬件动作前校验身份；不默认选择扫描得到的第一个设备。
    def __post_init__(self) -> None:
        if self.device_type not in abi.DEVICE_TYPES:
            raise ValueError(f"unsupported ZLG device type: {self.device_type}")
        if any(type(v) is not int or v < 0 for v in (self.device_index, self.channel)):
            raise ValueError("device index and channel must be non-negative integers")
        if type(self.termination) is not bool:
            raise ValueError("termination must be bool")


# 保留本次打开后实际读取的硬件身份和厂商版本；未读取前不填造数据。
@dataclass(frozen=True, slots=True)
class ZlgDeviceInfo:
    serial: str
    hardware: str
    channels: int
    firmware_version: int
    library_version: int


# 同一盒子对象串行使用；关闭时停止通道并释放设备，不遗留自动发送任务。
class ZlgCanBox:
    # 构造不访问设备；只有open会加载SDK和打开连接。
    def __init__(self, connection: ZlgConnection) -> None:
        self.connection = connection
        self._library: ct.CDLL | None = None
        self._device: int | None = None
        self._channel: int | None = None
        self._config: CanBusConfig | None = None

    # 此标识用于Peer Observation，不依赖DUT芯片或瞬时操作结果。
    @property
    def identity(self) -> str:
        link = self.connection
        return f"zlg:{link.device_type}:{link.serial or link.device_index}:CAN{link.channel}"

    # 打开指定设备并核对串号/通道；尚不启动CAN输出。
    def open(self) -> ZlgDeviceInfo:
        if self._device is not None:
            raise RuntimeError(f"{self.identity}: device already open")
        self._library = abi.load_library(self.connection.library)
        self._device = self._library.ZCAN_OpenDevice(
            abi.DEVICE_TYPES[self.connection.device_type], self.connection.device_index, 0
        )
        if not self._device:
            self._device = None
            raise OSError(f"{self.identity}: ZCAN_OpenDevice failed")
        try:
            raw = abi.DeviceInfo()
            self._check(self._library.ZCAN_GetDeviceInf(self._device, ct.byref(raw)), "device info")
            serial = raw.serial.decode("ascii", errors="strict")
            if self.connection.serial and serial != self.connection.serial:
                raise OSError(f"{self.identity}: unexpected serial {serial!r}")
            if self.connection.channel >= raw.can_num:
                raise ValueError(f"{self.identity}: device only has {raw.can_num} channels")
            return ZlgDeviceInfo(
                serial,
                raw.hardware.decode("ascii", errors="replace"),
                raw.can_num,
                raw.fw_version,
                raw.in_version,
            )
        except BaseException as primary:
            try:
                self.close()
            except Exception as cleanup:
                raise RuntimeError(f"CAN box open cleanup also failed: {cleanup}") from primary
            raise

    # 重配前停止上一通道；SDK失败时不继续启动，保留异常供Case报告。
    def configure(self, config: CanBusConfig) -> None:
        library = self._require_device()
        self.stop()
        try:
            for key, value in (
                ("canfd_standard", int(config.non_iso)),
                ("canfd_abit_baud_rate", config.nominal_bitrate),
                ("canfd_dbit_baud_rate", config.data_bitrate),
            ):
                self._set(key, value)
            raw = abi.ChannelConfig(can_type=abi.TYPE_CANFD)
            raw.canfd.acc_mask = 0xFFFFFFFF  # 厂商接收过滤：全接收，交由DUT测试过滤规则。
            raw.canfd.mode = int(config.listen_only)
            self._channel = library.ZCAN_InitCAN(
                self._device, self.connection.channel, ct.byref(raw)
            )
            if not self._channel:
                self._channel = None
                raise OSError(f"{self.identity}: ZCAN_InitCAN failed")
            # SDK属性名称保留厂商拼写；电阻在InitCAN之后、StartCAN之前设置。
            self._set("initenal_resistance", int(self.connection.termination))
            self._check(library.ZCAN_StartCAN(self._channel), "start")
            self._config = config
        except BaseException as primary:
            try:
                self.stop()
            except Exception as cleanup:
                raise RuntimeError(f"CAN box configure cleanup also failed: {cleanup}") from primary
            raise

    # 返回仅表示SDK接受1帧；总线ACK和接收数据必须另外观测。
    def send(self, frame: CanFrame, *, single_shot: bool = True) -> None:
        library = self._require_channel()
        if self._config.listen_only:
            raise ValueError(f"{self.identity}: listen-only channel cannot transmit")
        if not frame.fd and frame.dlc > 8:
            raise NotImplementedError("ZLG Classic API cannot preserve raw DLC 9..15")
        tx = abi.FdTx() if frame.fd else abi.ClassicTx()
        tx.frame.can_id = frame.identifier
        if frame.extended:
            tx.frame.can_id |= abi.CAN_EFF_FLAG
        if frame.remote:
            tx.frame.can_id |= abi.CAN_RTR_FLAG
        tx.frame.length = frame.dlc if frame.remote else len(frame.data)
        tx.frame.flags = abi.CANFD_BRS if frame.brs else 0
        tx.frame.data[: len(frame.data)] = frame.data
        tx.transmit_type = abi.TRANSMIT_SINGLE if single_shot else abi.TRANSMIT_NORMAL
        transmit = library.ZCAN_TransmitFD if frame.fd else library.ZCAN_Transmit
        accepted = transmit(self._channel, ct.byref(tx), 1)
        if accepted != 1:
            raise OSError(f"{self.identity}: transmit accepted {accepted}, expected 1")

    # 同时检查Classic/FD队列；SDK接收非阻塞，整个等待共用一个Deadline。
    def receive(self, *, timeout_s: float = 1.0) -> CanReceivedFrame:
        library = self._require_channel()
        if not math.isfinite(timeout_s) or timeout_s <= 0:
            raise ValueError("receive timeout must be finite and positive")
        deadline = time.monotonic() + timeout_s
        while True:
            for fd, raw, receive in (
                (False, abi.ClassicRx(), library.ZCAN_Receive),
                (True, abi.FdRx(), library.ZCAN_ReceiveFD),
            ):
                count = receive(self._channel, ct.byref(raw), 1, 0)
                if count not in (0, 1):
                    raise OSError(f"{self.identity}: receive returned invalid count {count}")
                if count:
                    return self._decode(raw, fd=fd)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(
                    f"{self.identity}: receive timeout; error=0x{self.error_get():08X}"
                )
            time.sleep(min(0.001, remaining))

    # 丢弃盒子当前通道的接收缓存；不改变DUT寄存器或盒子的总线配置。
    def clear(self) -> None:
        library = self._require_channel()
        self._check(library.ZCAN_ClearBuffer(self._channel), "clear receive buffer")

    # 读取当前盒子通道的厂商错误位图；不将空接收队列当成硬件错误。
    def error_get(self) -> int:
        library = self._require_channel()
        raw = abi.ChannelError()
        self._check(library.ZCAN_ReadChannelErrInfo(self._channel, ct.byref(raw)), "read error")
        return raw.error_code

    # 停止当前通道；失败保留句柄，使close仍可释放整个设备。
    def stop(self) -> None:
        if self._channel is not None:
            self._check(self._library.ZCAN_ResetCAN(self._channel), "reset channel")
            self._channel = None
            self._config = None

    # 依次尝试释放通道和设备；任一步失败都保留错误，不遗漏后续释放。
    def close(self) -> None:
        errors: list[Exception] = []
        try:
            self.stop()
        except Exception as exc:
            errors.append(exc)
        if self._device is not None:
            try:
                self._check(self._library.ZCAN_CloseDevice(self._device), "close device")
                self._device = self._channel = self._config = None
            except Exception as exc:
                errors.append(exc)
        if errors:
            raise RuntimeError(f"{self.identity}: close failed: {errors!r}") from errors[0]

    # SDK成功值必须严格为1，不把非零错误码误认成成功。
    def _check(self, status: int, operation: str) -> None:
        if status != abi.STATUS_OK:
            raise OSError(f"{self.identity}: {operation} failed, SDK status={status}")

    def _require_device(self) -> ct.CDLL:
        if self._device is None:
            raise RuntimeError(f"{self.identity}: open device first")
        return self._library

    def _require_channel(self) -> ct.CDLL:
        library = self._require_device()
        if self._channel is None or self._config is None:
            raise RuntimeError(f"{self.identity}: configure channel first")
        return library

    def _set(self, key: str, value: int) -> None:
        path = f"{self.connection.channel}/{key}".encode("ascii")
        self._check(
            self._library.ZCAN_SetValue(self._device, path, str(value).encode("ascii")), key
        )

    # 错误帧不混入正常载荷；回显明确标注，Case不能把自身回显当成Peer回复。
    def _decode(self, raw: abi.ClassicRx | abi.FdRx, *, fd: bool) -> CanReceivedFrame:
        word = raw.frame.can_id
        if word & abi.CAN_ERR_FLAG:
            raise OSError(f"{self.identity}: received CAN error frame 0x{word:08X}")
        remote = bool(word & abi.CAN_RTR_FLAG)
        length = raw.frame.length
        if length > (64 if fd else 8):
            raise OSError(f"{self.identity}: invalid receive length {length}")
        frame = CanFrame(
            word & abi.CAN_ID_MASK,
            b"" if remote else bytes(raw.frame.data[:length]),
            extended=bool(word & abi.CAN_EFF_FLAG),
            fd=fd,
            brs=fd and bool(raw.frame.flags & abi.CANFD_BRS),
            remote=remote,
            dlc=length if remote else None,
        )
        return CanReceivedFrame(
            frame,
            raw.timestamp,
            fd and bool(raw.frame.flags & abi.CANFD_ESI),
            bool(raw.frame.flags & abi.TX_ECHO_FLAG),
        )

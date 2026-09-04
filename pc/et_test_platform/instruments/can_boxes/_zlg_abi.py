# ZLG zlgcan.h/canframe.h的Windows ABI。
# 职责：固定结构布局、函数原型和SDK常量。
# 边界：私有设备适配，不向Case泄漏ctypes结构，不执行测试流程。
# 依赖：Python ctypes；与参考SDK的原生对齐一致，不使用pack=1。

import ctypes as ct
import os
from pathlib import Path

STATUS_OK = 1
TYPE_CAN = 0
TYPE_CANFD = 1
CAN_EFF_FLAG = 0x80000000
CAN_RTR_FLAG = 0x40000000
CAN_ERR_FLAG = 0x20000000
CAN_ID_MASK = 0x1FFFFFFF
CANFD_BRS = 0x01
CANFD_ESI = 0x02
TX_ECHO_FLAG = 0x20
TRANSMIT_NORMAL = 0
TRANSMIT_SINGLE = 1
DEVICE_TYPES = {
    "USBCANFD_200U": 41,
    "USBCANFD_100U": 42,
    "USBCANFD_MINI": 43,
    "USBCANFD_800U": 59,
    "USBCANFD_400U": 76,
}


# 厂商Classic帧，长度字节仅表达0..8；不宣称支持保留DLC9..15。
class ClassicFrame(ct.Structure):
    _fields_ = [
        ("can_id", ct.c_uint32),
        ("length", ct.c_uint8),
        ("flags", ct.c_uint8),
        ("reserved", ct.c_uint16),
        ("data", ct.c_uint8 * 8),
    ]


# 厂商FD帧的length使用字节长度而非DLC编码，flags单独表达BRS和ESI。
class FdFrame(ct.Structure):
    _fields_ = [
        ("can_id", ct.c_uint32),
        ("length", ct.c_uint8),
        ("flags", ct.c_uint8),
        ("reserved", ct.c_uint16),
        ("data", ct.c_uint8 * 64),
    ]


# Classic发送项附加厂商发送策略，不包含时间戳或自动回显标志。
class ClassicTx(ct.Structure):
    _fields_ = [("frame", ClassicFrame), ("transmit_type", ct.c_uint32)]


# Classic接收项末尾是64位设备微秒时间戳，遵循原生8字节对齐。
class ClassicRx(ct.Structure):
    _fields_ = [("frame", ClassicFrame), ("timestamp", ct.c_uint64)]


# FD发送项完整容纳64字节数据及发送策略，不与Classic项混用。
class FdTx(ct.Structure):
    _fields_ = [("frame", FdFrame), ("transmit_type", ct.c_uint32)]


# FD接收项保留设备微秒时间戳，不以主机时间替换真实接收时间。
class FdRx(ct.Structure):
    _fields_ = [("frame", FdFrame), ("timestamp", ct.c_uint64)]


# ZCAN_CHANNEL_INIT_CONFIG中最大的union成员是CAN FD配置，共28字节。
class FdConfig(ct.Structure):
    _fields_ = [
        ("acc_code", ct.c_uint32),
        ("acc_mask", ct.c_uint32),
        ("abit_timing", ct.c_uint32),
        ("dbit_timing", ct.c_uint32),
        ("brp", ct.c_uint32),
        ("filter", ct.c_uint8),
        ("mode", ct.c_uint8),
        ("pad", ct.c_uint16),
        ("reserved", ct.c_uint32),
    ]


# CAN FD设备即使发送Classic帧，也必须使用此TYPE_CANFD通道配置。
class ChannelConfig(ct.Structure):
    _fields_ = [("can_type", ct.c_uint32), ("canfd", FdConfig)]


# 打开后读取厂商身份、版本和通道数，串号数组不可误声明为字符串指针。
class DeviceInfo(ct.Structure):
    _fields_ = [
        ("hw_version", ct.c_uint16),
        ("fw_version", ct.c_uint16),
        ("dr_version", ct.c_uint16),
        ("in_version", ct.c_uint16),
        ("irq_num", ct.c_uint16),
        ("can_num", ct.c_uint8),
        ("serial", ct.c_char * 20),
        ("hardware", ct.c_char * 40),
        ("reserved", ct.c_uint16 * 4),
    ]


# 厂商通道错误快照保留原始错误位图和仲裁丢失信息，不生成测试判定。
class ChannelError(ct.Structure):
    _fields_ = [
        ("error_code", ct.c_uint32),
        ("passive", ct.c_uint8 * 3),
        ("arbitration_lost", ct.c_uint8),
    ]


# 显式声明句柄为void*，避免64位Python默认int返回值截断句柄。
def load_library(path: Path) -> ct.CDLL:
    if os.name != "nt":
        raise OSError("ZLG CAN box requires Windows and a matching vendor SDK")
    resolved = path.resolve(strict=True)
    with os.add_dll_directory(str(resolved.parent)):
        library = ct.WinDLL(str(resolved))
    handle, uint = ct.c_void_p, ct.c_uint32
    signatures = {
        "ZCAN_OpenDevice": (handle, [uint, uint, uint]),
        "ZCAN_CloseDevice": (uint, [handle]),
        "ZCAN_GetDeviceInf": (uint, [handle, ct.POINTER(DeviceInfo)]),
        "ZCAN_SetValue": (uint, [handle, ct.c_char_p, ct.c_char_p]),
        "ZCAN_InitCAN": (handle, [handle, uint, ct.POINTER(ChannelConfig)]),
        "ZCAN_StartCAN": (uint, [handle]),
        "ZCAN_ResetCAN": (uint, [handle]),
        "ZCAN_ClearBuffer": (uint, [handle]),
        "ZCAN_ReadChannelErrInfo": (uint, [handle, ct.POINTER(ChannelError)]),
        "ZCAN_Transmit": (uint, [handle, ct.POINTER(ClassicTx), uint]),
        "ZCAN_TransmitFD": (uint, [handle, ct.POINTER(FdTx), uint]),
        "ZCAN_Receive": (uint, [handle, ct.POINTER(ClassicRx), uint, ct.c_int]),
        "ZCAN_ReceiveFD": (uint, [handle, ct.POINTER(FdRx), uint, ct.c_int]),
    }
    for name, (result, arguments) in signatures.items():
        function = getattr(library, name)
        function.restype, function.argtypes = result, arguments
    return library

# 示波器库自包含原始字节 Transport 抽象。
#
# 职责：定义打开、关闭、限时读写和连接标识的最小字节接口。
# 边界：不解析 SCPI 文本、不包含型号命令，也不拥有测试 Case 的超时策略。
# 依赖：仅依赖 Python 抽象基类。

from __future__ import annotations

from abc import ABC, abstractmethod


# 提供示波器库共用的 ByteTransport 抽象；只处理字节收发事实，不解释任何仪器命令语义。
class ByteTransport(ABC):
    # 返回稳定连接标识；读取该属性只使用本地字段，不访问真实仪器。
    @property
    @abstractmethod
    def identity(self) -> str:
        pass

    # 打开已显式配置的连接；不扫描设备，也不发送任何仪器命令。
    @abstractmethod
    def open(self) -> None:
        pass

    # 关闭连接并释放通信资源；不隐式改变示波器运行状态。
    @abstractmethod
    def close(self) -> None:
        pass

    # 写入完整原始字节；超时语义由本层实现承担，失败时抛出传输异常。
    @abstractmethod
    def write(
        self,
        data: bytes,
        *,
        timeout_s: float | None = None,
    ) -> None:
        pass

    # 读取不超过 max_bytes 的原始字节；无数据可读时返回空字节串。
    @abstractmethod
    def read(
        self,
        max_bytes: int,
        timeout_s: float | None = None,
    ) -> bytes:
        pass


__all__ = ["ByteTransport"]

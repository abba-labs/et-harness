# PC 控制面的原始字节 Transport 抽象。
#
# 职责：定义打开、关闭、限时读写和连接标识的最小接口。
# 边界：不解析 ET-Frame，不包含 Service/IP 语义，也不拥有 Test Case Deadline。
# 依赖：仅依赖 Python 抽象接口和平台 TransportError 语义。

from __future__ import annotations

from abc import ABC, abstractmethod


# 提供 ByteTransport 的稳定公共抽象；只暴露本层事实和行为，不把下层实现细节泄漏给调用方。
class ByteTransport(ABC):
    # 提供 identity 的通信层稳定语义；只处理字节/协议事实，不解释具体 IP 业务。
    @property
    @abstractmethod
    def identity(self) -> str:
        pass

    # Open the transport.
    #
    # 该 API 定义通信层稳定合同；超时、资源生命周期或帧语义由对应层明确承担。
    @abstractmethod
    def open(self) -> None:
        pass

    # Close the transport.
    #
    # 该 API 定义通信层稳定合同；超时、资源生命周期或帧语义由对应层明确承担。
    @abstractmethod
    def close(self) -> None:
        pass

    # 提供 write 的通信层稳定语义；只处理字节/协议事实，不解释具体 IP 业务。
    @abstractmethod
    def write(
        self,
        data: bytes,
        *,
        timeout_s: float | None = None,
    ) -> None:
        pass

    # 提供 read 的通信层稳定语义；只处理字节/协议事实，不解释具体 IP 业务。
    @abstractmethod
    def read(
        self,
        max_bytes: int,
        timeout_s: float | None = None,
    ) -> bytes:
        pass

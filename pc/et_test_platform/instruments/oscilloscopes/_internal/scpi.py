# 示波器库自包含 SCPI 文本与 IEEE488.2 数据块会话。
#
# 职责：在 ByteTransport 上发送单条 SCPI 命令，并按行或 definite-length block 读取响应。
# 边界：不解释具体型号命令、参数范围或测试 PASS/FAIL，也不自动重试修改型命令。
# 依赖：仅依赖本库 ByteTransport、OperationDeadline 和仪器协议异常。

from __future__ import annotations

from .deadline import OperationDeadline
from .errors import InstrumentProtocolError
from .transport import ByteTransport

_DEFAULT_TIMEOUT_S = 2.0
_READ_CHUNK_BYTES = 4096


# 提供一条命令对应一次写入、一次查询对应一个完整响应的 SCPI 会话。
class ScpiSession:
    def __init__(
        self,
        transport: ByteTransport,
        *,
        terminator: bytes = b"\n",
        timeout_s: float = _DEFAULT_TIMEOUT_S,
    ) -> None:
        if not terminator:
            raise ValueError("terminator must not be empty")
        if timeout_s <= 0:
            raise ValueError("timeout_s must be positive")
        self._transport = transport
        self._terminator = terminator
        self._timeout_s = float(timeout_s)
        self._rx_buffer = bytearray()

    # 返回底层连接标识；不执行 I/O；读取过程不会访问仪器硬件。
    @property
    def identity(self) -> str:
        return self._transport.identity

    # 打开底层 Transport；不发送任何仪器命令。
    def open(self) -> None:
        self._transport.open()

    # 关闭底层 Transport；同时丢弃尚未消费的响应缓存。
    def close(self) -> None:
        try:
            self._transport.close()
        finally:
            self._rx_buffer.clear()

    # 发送一条无响应 SCPI 命令；只等待本次写入完成。
    def write(self, command: str, *, timeout_s: float | None = None) -> None:
        encoded = self._encode_command(command)
        self._transport.write(encoded, timeout_s=self._timeout(timeout_s))

    # 发送一条已经组装好的原始消息；可选追加当前会话终止符，不解释消息内容。
    def write_bytes(
        self,
        payload: bytes,
        *,
        append_terminator: bool = False,
        timeout_s: float | None = None,
    ) -> None:
        data = bytes(payload)
        if not data:
            raise ValueError("payload must not be empty")
        if append_terminator:
            data += self._terminator
        self._transport.write(data, timeout_s=self._timeout(timeout_s))

    # 发送 command_prefix + IEEE488.2 definite-length block；一次写入完成整个二进制消息。
    def write_definite_block(
        self,
        command_prefix: str,
        payload: bytes,
        *,
        separator: str = " ",
        timeout_s: float | None = None,
    ) -> None:
        prefix = command_prefix.strip()
        if not prefix:
            raise ValueError("command_prefix must not be empty")
        if "\r" in prefix or "\n" in prefix:
            raise ValueError("command_prefix must contain exactly one command line")
        if "\r" in separator or "\n" in separator:
            raise ValueError("separator must not contain a line break")
        data = bytes(payload)
        length_text = str(len(data)).encode("ascii")
        if len(length_text) > 9:
            raise ValueError("IEEE488.2 block payload is too large")
        try:
            command_bytes = prefix.encode("ascii")
            separator_bytes = separator.encode("ascii")
        except UnicodeEncodeError as exc:
            raise ValueError("SCPI command prefix and separator must be ASCII") from exc
        header = b"#" + str(len(length_text)).encode("ascii") + length_text
        message = command_bytes + separator_bytes + header + data + self._terminator
        self._transport.write(message, timeout_s=self._timeout(timeout_s))

    # 发送一条查询并返回 ASCII 文本；definite-length block 会先去除块头。
    def query_text(self, command: str, *, timeout_s: float | None = None) -> str:
        response = self.query_bytes(command, timeout_s=timeout_s)
        try:
            return response.decode("ascii").strip()
        except UnicodeDecodeError as exc:
            raise InstrumentProtocolError(f"non-ASCII SCPI response for {command!r}") from exc

    # 发送一条查询并返回完整响应；支持行响应和 IEEE488.2 definite-length block。
    def query_bytes(self, command: str, *, timeout_s: float | None = None) -> bytes:
        timeout = self._timeout(timeout_s)
        deadline = OperationDeadline.start(timeout, label=f"SCPI query {command}")
        self._transport.write(self._encode_command(command), timeout_s=deadline.remaining_s())
        self._fill(1, deadline)
        if self._rx_buffer.startswith(b"#"):
            return self._read_definite_block(deadline)
        return self._read_line(deadline)

    def _encode_command(self, command: str) -> bytes:
        normalized = command.strip()
        if not normalized:
            raise ValueError("SCPI command must not be empty")
        if "\r" in normalized or "\n" in normalized:
            raise ValueError("SCPI command must contain exactly one command line")
        try:
            return normalized.encode("ascii") + self._terminator
        except UnicodeEncodeError as exc:
            raise ValueError("SCPI command must be ASCII") from exc

    def _timeout(self, timeout_s: float | None) -> float:
        timeout = self._timeout_s if timeout_s is None else float(timeout_s)
        if timeout <= 0:
            raise ValueError("timeout_s must be positive")
        return timeout

    def _fill(self, minimum_bytes: int, deadline: OperationDeadline) -> None:
        while len(self._rx_buffer) < minimum_bytes:
            chunk = self._transport.read(_READ_CHUNK_BYTES, timeout_s=deadline.remaining_s())
            if chunk:
                self._rx_buffer.extend(chunk)

    def _read_line(self, deadline: OperationDeadline) -> bytes:
        while True:
            position = self._rx_buffer.find(self._terminator)
            if position >= 0:
                result = bytes(self._rx_buffer[:position]).rstrip(b"\r")
                del self._rx_buffer[: position + len(self._terminator)]
                return result
            chunk = self._transport.read(_READ_CHUNK_BYTES, timeout_s=deadline.remaining_s())
            if chunk:
                self._rx_buffer.extend(chunk)

    def _read_definite_block(self, deadline: OperationDeadline) -> bytes:
        self._fill(2, deadline)
        digit_count_byte = self._rx_buffer[1:2]
        if not digit_count_byte.isdigit():
            raise InstrumentProtocolError("invalid IEEE488.2 block digit count")
        digit_count = int(digit_count_byte)
        if digit_count == 0:
            raise InstrumentProtocolError("indefinite-length IEEE488.2 blocks are not supported")
        header_length = 2 + digit_count
        self._fill(header_length, deadline)
        length_bytes = bytes(self._rx_buffer[2:header_length])
        if not length_bytes.isdigit():
            raise InstrumentProtocolError("invalid IEEE488.2 block payload length")
        payload_length = int(length_bytes)
        total_length = header_length + payload_length
        self._fill(total_length, deadline)
        payload = bytes(self._rx_buffer[header_length:total_length])
        del self._rx_buffer[:total_length]
        if self._rx_buffer.startswith(self._terminator):
            del self._rx_buffer[: len(self._terminator)]
        elif self._rx_buffer.startswith(b"\r" + self._terminator):
            del self._rx_buffer[: len(self._terminator) + 1]
        return payload

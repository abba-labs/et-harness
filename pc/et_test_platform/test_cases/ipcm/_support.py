# IPCM能力与执行映射解析。
# 职责：只建立类型化角色和容量，不执行配置、复位、消息或ACK流程。
# 边界：芯片值只从既有Execution Mapping读取，缺口失败关闭、不SKIP。
# 依赖：本IP Driver、Profile和CRG Driver。

from dataclasses import dataclass
from importlib import import_module

from ...core.errors import ConfigurationError
from ...drivers.crg import CrgDriver
from ...drivers.ipcm import IpcmDriver
from ...drivers.ipcm.models import IpcmCapabilities
from ...profiles import chip_execution_mappings
from ...profiles.capabilities import ChipCapabilities


# Case需要的独立执行角色与只读事实；所有Feature动作必须留在Case主体。
@dataclass(frozen=True, slots=True)
class IpcmSupport:
    local: IpcmDriver
    peer: IpcmDriver
    crg: CrgDriver
    runtime: IpcmCapabilities
    capabilities: ChipCapabilities
    instance_name: str
    local_endpoint: int
    peer_endpoint: int
    second_endpoint: int
    peer_identity: int
    mailbox_count: int
    channel_count: int
    data_word_count: int
    capacity: int

    # 只查询已加载能力；不发送命令，不把内部适配缺口改成SKIP。
    def require(self, *features: str) -> None:

        for feature in features:
            if not self.capabilities.has_feature("ipcm", feature, instance=self.instance_name):
                raise ConfigurationError(f"IPCM requires reviewed capability {feature}")


# 按chip_id加载目标私有数据，验证角色不重叠且在真实Channel容量内。
def resolve_routes(capabilities: ChipCapabilities, channel_count: int) -> tuple[int, int, int, int]:

    name = f"{chip_execution_mappings.__package__}.{capabilities.chip_id}.ipcm_routes"
    try:
        module = import_module(name)
    except ModuleNotFoundError as error:
        if error.name in (name, name.rpartition(".")[0]):
            raise ConfigurationError("IPCM dual-core execution mapping is missing") from error
        raise
    mapping = module.IPCM_EXECUTION_MAPPING
    endpoints = tuple(
        mapping[key] for key in ("local_endpoint", "peer_endpoint", "peer_secondary_endpoint")
    )
    identity = mapping["peer_executor_identity"]
    if len(set(endpoints)) != 3 or any(
        type(value) is not int or not 0 <= value < channel_count for value in endpoints
    ):
        raise ConfigurationError("IPCM endpoint mapping is invalid")
    if type(identity) is not int or identity <= 0 or not module.IPCM_EXECUTION_EVIDENCE:
        raise ConfigurationError("IPCM Peer identity/evidence is invalid")
    return (*endpoints, identity)

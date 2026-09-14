# CRC CONTEXT_RESET 补充接口说明

本文件记录本次新增接口，不替代 `crc.md` 的既有 Feature、Case、Report 契约。首个调用者是 `CRC_P0_002`；其三份配置、输入、固定 Expected 与四项判定没有修改。全仓契约检查和硬件复测尚未执行，不将本补充文件作为集成验收通过证明。

## 接口

| 项目 | 定义 |
|---|---|
| Service | CRC，`0x0102` |
| Command | `CONTEXT_RESET = 0x0015`，追加在旧命令 `0x0014` 后 |
| 实例 | 公共消息头的 CRC instance_id，不在 body 里重复编码 |
| Request body | 0 字节 |
| Response body | 0 字节；失败使用现有协议 status |
| Retry | 不标记 retry_safe，不自动重试 |
| 兼容性 | 原 20 条命令的编号、载荷、响应保持不变；本命令需要配套新固件 |

## 必须满足的前置条件

调用者已经停止所有可能访问公共资源池的独立设备，并成功完成所选 CRC 的 CRG 硬件复位。CRC 硬件复位使本外设静止，但不代表 DMA 控制器或其他总线主设备停止。

`CONTEXT_RESET` 不检测或执行 CRG 复位，也不能单独用来停止正在工作的 CRC。它是 `CrcDriver.reset()` 固定顺序中的软件清理步骤，不作为被测 IRQ Clear、Disable 或故障恢复功能的替代。

## 固件成功后的状态

通过既有 IRQ Manager 的 `et_irq_manager_unbind()`，精确释放 callback 为 `crc_irq_callback`、context 为当前 Service 的实际绑定。检查实际绑定表，而不是只依据 `irq_bound` 标志，避免漏掉失败绑定的残留记录。

在解绑成功后清理当前 Service 的 enabled、configured、mode、irq_bound、irq_enabled_sources、irq_event_count、irq_last_event、irq_last_raw、irq_route。保留 crc_id、irq_priority、irq_manager 和 descriptor。

不清空全局 Manager，不动其他 Service/实例的绑定，不写 CRC Mask/Enable/Clear 寄存器，不配置 Polynomial/Seed，不写 Resource Pool。当前 CRC Service 没有 generation 字段；不得将本接口描述成 CAN 式代次更新。

任何解绑失败立即返回 `ET_STATUS_INTERNAL_ERROR`，保留 Service 的事件记录，PC 不得继续清资源池。已经完成的解绑不会回滚；这是有序清理，不是原子事务。

## PC 公开入口

`CrcDriver.reset()` 执行：

```text
先使 PC 模式/能力缓存失效
→ CRG.reset(CRC, selected_instance)
→ CRC.CONTEXT_RESET
→ Resource.reset()
```

检查 CONTEXT_RESET 响应必须为空。任何一步异常向上抛出，后续请求不再发送。成功后 CRC 处于未配置状态，Case 仍须显式 `enable()` 和 `configure()`；reset 不替 Case 完成被测配置。

Resource Pool 是公共池，不是 CRC 私有内存。清池使本次旧资源引用不可继续使用。CRC DMA Case 迁移前，必须先落实其 DMA 停止、路由释放和失败收尾；不能直接套用只涉及 CPU 同步计算的样板。

## 首个迁移 Case 与证据

`test_crc_p0_002_mode_reference_vectors` 显式选择 `crc0`，正文调用 reset、create/write、enable/configure、calculate/result_get，最后保留 Golden/实际值/剩余计数/独立读回四项断言。

`crc0` Fixture 只提供句柄和固定收尾，不偷偷执行初始复位。运行层记录适配器保存已经返回的数据，不增加硬件读写，不在 Driver 中执行 Case 或最终判定。该适配器只服务一次稳定 CRC 基础计算，不自动推广到 IRQ、连续状态或性能测量。

旧 JSON 文件名与原字段保留，新增结果读回字段；尚未观测的值为 null。PASS 原始证据继续保留。公共报告的 FAIL-only 备注属于独立批次，本次未改报告程序。

## 验证状态

已执行边界隔离的 Python 测试和实际 CRC Service C 源码的原生调度测试；具体数量、替身边界和复跑命令见 `report/review/chatgpt_review/crc/001_crc_reference_sample_implementation.md`。

完整包导入、真实 TargetClient/Transport、实际 IRQ Manager/Wrap 联调、全仓质量门禁、Keil 构建和 HIL 尚未执行。旧固件不支持 0x0015，不可直接运行新样板并预期通过；必须先按台架人工流程构建部署匹配固件。

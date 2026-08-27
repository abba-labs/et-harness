---
schema: et.rule-document.v1
number: R300
domain: firmware
lifecycle: active
owners: [firmware_service_responsibility]
rule_ids: [ET-RULE-FIRMWARE-SERVICE]
---

# R300 Firmware Service规则

## 1. 定位

Service是PC命令到公共Wrap的薄执行层。它解析请求、校验内存安全、调用本IP Wrap并返回硬件事实；不拥有测试用例和最终PASS/FAIL。

## 2. 固定链路

```text
ET-Frame Router
  -> <IP> Service
      -> Own <IP> Wrap -> Own Chip Driver        # Feature动作
      -> Framework Resource API / IRQ Manager   # 公共资源校验与中断路由
```

普通IP Service的Feature动作必须只调用本IP Wrap。为安全解析PC传入的Resource Handle和绑定中断路由，允许调用Framework提供的Resource API或IRQ Manager；当前历史稳定接口`et_resource_wrap.h`按Framework Resource API管理，不视为其他Feature IP Wrap。

普通IP Service不得调用其他IP Service、其他Feature IP Wrap、Chip Driver、SDK或寄存器。Framework Resource API只允许完成Handle/Range校验和资源事实查询，不得承载Feature动作、跨IP测试流程或最终断言。

## 3. 一Service一IP

每个IP只有一组稳定Service ID和Command ID。Service文件固定为：

```text
firmware/services/include/et_<ip>_service.h
firmware/services/src/et_<ip>_service.c
```

公开命令表达稳定动作，如`CONFIGURE`、`START`、`STATUS_GET`。芯片差异不得产生`ET6801_CONFIGURE`或在Handler内出现芯片分支。

## 4. Handler固定步骤

```c
static et_status_t et_dma_handle_start(
    et_dma_service_t *service,
    const uint8_t *request,
    size_t request_size,
    et_response_t *response)
{
    et_dma_start_request_t decoded;

    ET_RETURN_IF_ERROR(et_dma_decode_start(request, request_size, &decoded));
    ET_RETURN_IF_ERROR(et_resource_validate_range(
        service->resources, decoded.buffer, decoded.length));

    return et_dma_wrap_start(decoded.instance, decoded.channel);
}
```

顺序固定为：

1. 精确校验Payload长度和保留位；
2. 解码为公共类型；
3. 校验指针、长度、乘加溢出和Resource边界；
4. 调用本IP Wrap执行Feature动作，或调用获准的Framework Resource API / IRQ Manager完成公共资源职责；
5. 编码事实响应；
6. 返回统一状态码。

## 5. 参数与状态

- PC必须完整下发动作所需参数；Service不得根据芯片、实例或历史Case猜默认值。
- 允许保存固定容量的异步会话、IRQ计数、传输进度和最近硬件快照。
- 禁止保存测试期望、Golden结果、Case步骤、跨IP策略和最终测试结论。
- 状态必须有显式初始化、取消、清理和复位路径；不得动态分配无界内存。

## 6. 有界执行

- 一条命令必须在有界时间内返回。
- 长传输采用`START -> STATUS_GET / RESULT_GET -> ABORT`，不得在Handler中无限轮询。
- ISR只记录最小事件并推进已启动的本IP会话；复杂分析留给PC。
- 固定小循环必须有公开上限和超时错误。

## 7. 错误与响应

- Service返回配置结果、硬件状态、计数和原始事件，不返回“测试通过”。
- 未支持能力返回`NOT_SUPPORTED`，非法配置返回`INVALID_CONFIG`，超时和硬件错误必须可区分。
- Cleanup失败和异步Fault必须可查询；禁止清零后伪装成功。
- 不在控制UART混入裸`printf`。

## 8. 扩展规则

新增芯片不得复制Service；只在Chip Driver、Board/Chip Config和Capability吸收差异。新增Feature通常只增加本Service命令和对应Wrap接口；若需要修改Framework公共层，必须先证明是多个IP共有的稳定需求。

### 8.1 Service实例注册

所有可重复实例的IP Service必须实现统一的`et_service_factory_fn`，由公共注册器按静态
`et_service_group_t`描述表初始化和注册。公共注册器不得按UART、DMA、CRC、AES等IP名称
分别保存数组、计数或复制注册循环。

每个IP只在自己的Service文件中实现一次薄工厂函数，用于：

1. 将公共逻辑实例号转换为本Service公开的实例类型；
2. 传入公共IRQ Manager和板级优先级；
3. 调用本Service既有初始化函数；
4. 返回已初始化的公共Descriptor。

工厂函数不得增加Feature动作、默认配置、测试步骤或芯片判断。新增IP时只新增本IP
Service、静态存储和一行Group描述；不得修改公共注册算法。

薄工厂所需的include、公开声明和实现必须分别完整包围在以下成对标记内，便于同步门禁
把平台注册胶水与IP行为变更准确分开：

```c
/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
/* thin factory include, declaration, or implementation */
/* ET_PLATFORM_SERVICE_FACTORY_END */
```

标记内只允许统一工厂签名、参数空指针校验、调用既有`et_<ip>_service_init()`和返回既有
Descriptor；不得包围、移动或修改命令Handler与Feature实现。

`check_firmware_architecture_rules.py`必须验证标记成对、区域数量和允许结构；任何额外调用、状态写入、命令处理或Feature逻辑均以`ETFW103`失败关闭。只有通过该结构检查的区域，IP同步门禁才允许将其作为平台注册胶水排除。

## 9. 验证

```powershell
python tools/quality/check_firmware_architecture_rules.py .
python -m pytest -q pc/et_test_platform/framework_validation/unit/firmware_contract
python tools/validate_pc.py
```

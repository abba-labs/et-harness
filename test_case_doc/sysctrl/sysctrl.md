# SYSCTRL Stable IP Contract

更新时间：2026-09-03 22:05 CST。上述路由已接入PC Driver、Service及Wrap；HIL未执行。

本文件约束已有DMAMUX接口及本轮批准的系统计数器路由接口，不代表SYSCTRL全部Feature分析完成。计数器测试方法唯一位于`../syscnt/syscnt.md`。

## 0. Stable IP Contract

- IP：`sysctrl`，Service `0x0011`，Service instance `0`。
- 只配置系统所有的信号路由；不启动计数器、DMA，不操作CRG，不做测试循环或PASS/FAIL判断。
- 所有计数器路由请求均为`instance:u8, value:u8, reserved[2]=0`，共4字节。
- 系统计数器逻辑时钟源固定为`0=INTERNAL`、`1=EXTERNAL`；目标SDK选择值放在Chip Config，实际Hz由芯片/Lane事实给出。源选择不等于频率测量。

### 0.1 Stable Service Command Contract

| Command | ID | Request bytes | Response bytes | Stable semantics |
|---|---:|---:|---:|---|
| DMA_REQUEST_CONFIGURE | 0x0001 | 12 | 0 | 旧请求保留，合法长度返回NOT_SUPPORTED，不重新解释 |
| DMA_REQUEST_RELEASE | 0x0002 | 4 | 0 | controller、interface、两个零保留字节；释放该DMAMUX接口 |
| DMA_REQUEST_CONFIGURE_V2 | 0x0003 | 4 | 0 | controller、interface、request_id、零保留字节；只路由请求 |
| SYSCNT_SOURCE_SET | 0x0004 | 4 | 0 | value为逻辑时钟源；调用前PC必须停止目标计数器 |
| SYSCNT_HALT_SET | 0x0005 | 4 | 0 | value为0/1；设置系统Debug Halt路由，不修改计数器自身暂停策略 |
| SYSCNT_ROUTING_GET | 0x0006 | 4 | 4 | 请求value=0；返回source:u8、halt_enabled:u8、reserved[2]=0，均为实际读回 |

未知实例/目标不具备路由返回NOT_SUPPORTED；非Boolean、非法源、长度或保留字节错误返回INVALID_PARAM。GET不改变任何硬件状态。PC严格校验响应长度、源枚举、Boolean和保留字节，不能把请求缓存当作读回。

## 1. Layer Responsibilities

- PC Driver只编码一个SYSCTRL动作；跨IP顺序在Case中明确编排。
- SYSCTRL Service只解析请求、调用Own Wrap、编码响应。
- SYSCTRL Wrap只做静态Chip Config映射与Own Driver调用。新芯片更换映射和Chip Driver，不往公共接口添加芯片名称。
- 本轮不修改既有DMA路由语义，不增加全局复位或时钟默认配置。

## 4. Chip Adaptation Summary

| Chip | Feature适配状态 | Case适配状态 | 主要Gap | 详细分析 |
|---|---|---|---|---|
| ET6801 |  |  | FPGA实际时钟及Halt联动由SYSCNT Case验证，尚未实测 | `ET6801_sysctrl.md` |

## 5. Common Gap / Evolution

本轮无独立SYSCTRL Formal Case，不新增机器Case块。路由操作通过使用它的SYSCNT Case验证；将来独立分析SYSCTRL时再建立完整Feature/Case目录，不能将本接口文档冒充全IP覆盖。

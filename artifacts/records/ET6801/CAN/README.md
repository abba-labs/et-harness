# ET6801 CAN Case知识

更新时间：2026-09-10 21:48 CST。

本目录长期保留每Case一份提炼型Markdown，由Agent审阅事实后维护；脚本只检查与生成导航，不自动编写结论。适用范围、问题、修复依据与未执行边界见各Case。当前运行结果仍在运行工作区，不能用这里的历史PASS替代当前回归。

本次迁移仅覆盖已经有记录的31个Case，不表示公共CAN全部42项测试目标已实现或CAN问题全部解决。无需补造未执行Case记录。正文不依赖旧`evidence/*.json`、`evidence/*.zip`、`results.json`或`test_report.xlsx`。

<!-- ET_RECORD_AUTO_BEGIN -->

## Case知识索引

本索引不汇总测试状态；当前测试结果见运行工作区。

- [CAN_P0_001 — CAN复位与受保护配置](cases/CAN_P0_001.md)
- [CAN_P0_002 — Classic内部回环与FIFO应答](cases/CAN_P0_002.md)
- [CAN_P0_003 — 正常总线双向基础通信](cases/CAN_P0_003.md)
- [CAN_P1_001 — Classic与FD帧格式、DLC边界](cases/CAN_P1_001.md)
- [CAN_P1_002 — 标准ID过滤、路由与优先匹配](cases/CAN_P1_002.md)
- [CAN_P1_003 — 扩展ID与XIDAM过滤](cases/CAN_P1_003.md)
- [CAN_P1_004 — Remote允许、拒绝及数据对照](cases/CAN_P1_004.md)
- [CAN_P1_005 — RX FIFO水位、满与索引环回](cases/CAN_P1_005.md)
- [CAN_P1_006 — RX FIFO Blocking与Overwrite](cases/CAN_P1_006.md)
- [CAN_P1_007 — 专用RX Buffer与New Data位图](cases/CAN_P1_007.md)
- [CAN_P1_008 — TX Buffer、FIFO与Queue调度](cases/CAN_P1_008.md)
- [CAN_P1_009 — TX Event FIFO阈值、丢失与恢复](cases/CAN_P1_009.md)
- [CAN_P1_010 — 8-bit与16-bit Event Marker](cases/CAN_P1_010.md)
- [CAN_P1_011 — CAN两线路IRQ投递与独立清除](cases/CAN_P1_011.md)
- [CAN_P1_012 — 固定输入时钟下的双向速率矩阵](cases/CAN_P1_012.md)
- [CAN_P1_013 — 16-bit时间戳锁存、回绕与清零](cases/CAN_P1_013.md)
- [CAN_P1_014 — Timeout四来源与禁止对照](cases/CAN_P1_014.md)
- [CAN_P1_015 — 停钟请求、应答及恢复](cases/CAN_P1_015.md)
- [CAN_P1_016 — Message RAM模式与March C-](cases/CAN_P1_016.md)
- [CAN_P1_018 — 32-bit TSU捕获、覆盖读清与时间基](cases/CAN_P1_018.md)
- [CAN_P1_020 — ISO / Non-ISO格式正反例](cases/CAN_P1_020.md)
- [CAN_P1_021 — 开启TDC的FD双向通信](cases/CAN_P1_021.md)
- [CAN_P2_001 — CAN DMU与DMA完整帧搬运](cases/CAN_P2_001.md)
- [CAN_P2_002 — TX Event的DMU/DMA搬运](cases/CAN_P2_002.md)
- [CAN_P2_003 — ECC Force中断链](cases/CAN_P2_003.md)
- [CAN_P2_004 — 多实例数据、配置与RAM隔离](cases/CAN_P2_004.md)
- [CAN_P2_005 — 内外回环物理隔离，外部捕获暂停排查](cases/CAN_P2_005.md)
- [CAN_P2_007 — DMU九类非法访问与复位恢复](cases/CAN_P2_007.md)
- [CAN_P2_008 — DMU时间戳附加与payload覆盖对照](cases/CAN_P2_008.md)
- [CAN_P2_010 — RAM Watchdog基础开关、中断与恢复](cases/CAN_P2_010.md)
- [CAN_P3_001 — 有界双向FD连续收发](cases/CAN_P3_001.md)

<!-- ET_RECORD_AUTO_END -->

## 历史来源与版本

以下为本次提炼依据，不是第二份活动状态：

- FPGA运行完成于2026-09-08 01:12 CST，31个Case、148个参数执行，139 PASS、9 FAIL；28个Case全部节点通过，3个Case存在FAIL。
- Source：`e0f70ef9f353f4d8a239bbd3778c735c01897d0b`，source_dirty=false；设备身份和bitstream_id均未知。固件自报名称中的silicon不改变Manifest的FPGA Lane。
- 历史规范SHA256：`e521ae516ac40d83236f9dbf42e394a42e4be776d8af9be3cef908f0ca4f20c4`。方法以当时规范解释；当前[公共CAN契约](../../../../test_case_doc/can/can.md)只作为继续开发入口，不能冒充旧版快照。
- Canonical Session及同目录`cases/*/result.json`保留原始事实；Manifest保存运行身份和配置定位。两者均在本工作区`artifacts/records/ET6801/CAN/current`。原始的`artifacts/runs/**`执行目录已废弃并从仓库删除，本树不引用它。
- [芯片文档](../../../../test_case_doc/can/ET6801_can.md#can-record-index)保留原测试状态、失败分析与参数级结果导航。

未闭环问题：[Non-ISO](cases/CAN_P1_020.md)、[ECC中断封装](cases/CAN_P2_003.md)；[外部回环](cases/CAN_P2_005.md)仍按用户暂停，本轮仅复测仍 FAIL。没有已验证修复。

## 冗余文件候选

迁移后候选为旧`evidence/`下31个JSON和31个ZIP，以及本目录`results.json`、`test_report.xlsx`，共64文件；实际删除尚待确认。原始运行目录、知识正文和公共/芯片契约均不在删除范围。

精确路径与保留边界由[经验库产物位置纪律](../../../experience/environment/artifact_location_discipline.md)约束；已删除的历史run不做逐字节恢复承诺。其中规范内容可从固定Source Git版本恢复；精确字节恢复依赖历史混合换行，删除前必须再次验证，而非仅凭文件名清理。

## 关键变化

- 2026-09-10 21:48 CST：对照本轮 Session（`7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，139 PASS / 9 FAIL）更新三份 FAIL 证据；PASS Case 仅记脏树不得外推。

- 2026-09-08 12:18 CST：建立固定Case档案，导入31个Case/148个参数执行（139 PASS、9 FAIL）；迁移已有三项失败分析，未关闭问题、未删除旧证据。
- 2026-09-08 16:08 CST：31个Case全部改为Agent提炼知识，保留历史版本、日期、失败与暂停决定；只列出64个冗余候选，原始运行只读保留。

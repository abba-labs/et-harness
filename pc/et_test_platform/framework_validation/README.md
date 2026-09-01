# framework_validation

PC平台自身的验证代码，不是芯片IP测试Case。

- `unit/`：协议、Client、Transport、Profile和目录契约单元测试；
- `integration/`：不依赖真实硬件的跨模块组合测试；
- `test_data/`：golden frame和模拟响应等固定测试数据。

HIL和Renode不是两套测试目录。同一个`test_cases/`场景通过不同Profile和能力
检查运行在FPGA、真实芯片或Renode环境。

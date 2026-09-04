# CAN盒子

实现位于本目录；人工入口为`tools/runner/can_box.py`。两者复用同一Adapter，Case不启动子进程、不直接调用厂商DLL。

参考接口：ET Tool的`transport/can/zlg_canfd_driver.h`、`zlg_classic_can_driver.h`及厂商`zlgcan.h/canframe.h`。这里只复用设备API语义，没有复制BootROM协议或芯片限制。CAN1对应厂商API的通道1。

## 配置

在本机`run_config.yaml`的`instruments`中增加连接。路径指向本机安装的完整ZLG SDK；保留其同级依赖和`kerneldlls`目录，Python与SDK位数必须一致。不要将参考工程的个人路径写进源码。

```yaml
instruments:
  can_box:
    enabled: true
    type: can_box
    driver: zlg_can
    connection:
      kind: usb
      library: C:/vendor/zlg/windows-x64/zlgcan.dll
      device_type: USBCANFD_200U
      device_index: 0
      channel: 1
      termination: true
      serial: "" # 获得实际串号后填写，可防止索引变化连接错误盒子。
```

GPIO及DUT Handle仍属于硬件连接YAML。位速率、静默/Non-ISO和帧内容属于Case，不放入此连接配置。Fixture通过Runner导出的`ET_INSTRUMENT_CAN_BOX_*`调用`create_zlg_can_box_from_environment()`；不增加公共Fixture或Runner分支。

## 人工工具

```powershell
.\.venv\Scripts\python.exe tools/runner/can_box.py --action check
.\.venv\Scripts\python.exe tools/runner/can_box.py --action info
.\.venv\Scripts\python.exe tools/runner/can_box.py --action send --id 0x123 --data 0102030405060708
.\.venv\Scripts\python.exe tools/runner/can_box.py --action receive --timeout-s 5
```

除`check`外必须先在配置中确认硬件动作。工具只产生诊断输出，不替代正式Registry/Pipeline测试和Excel报告。`send`默认单次发送，不持续重传；SDK接受帧不表示DUT已收到。退出时停止通道并关闭设备，不保留自动发送任务。

## 已实现边界

- Classic/FD、标准/扩展ID、Remote、BRS、Normal/Listen-only、终端电阻、指定通道。
- 读取设备身份、原始接收时间戳、ESI/回显标志和厂商错误位图；异常不吞掉。
- Classic保留DLC9..15不能通过此SDK发送，明确拒绝；此部分应由DUT内部回环验证原始DLC。
- 不提供位错误注入、可编程线路延迟、确定性TTCAN应答或示波器测量能力。
- 两个接收队列分别读取，不宣称Classic/FD混合帧的统一跨队列顺序。
- ABI、模型和Fake回归通过不表示实际盒子型号的每个参数已通过硬件验证。

## 无硬件验证

```powershell
.\.venv\Scripts\python.exe -m pytest -q pc/et_test_platform/framework_validation/unit/instruments/test_can_box.py
```

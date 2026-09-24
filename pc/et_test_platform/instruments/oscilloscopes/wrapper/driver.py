# 封装层 Driver 装配。
#
# 职责：在厂商 Driver 之上装配封装层 Operations，使台架层可用到补充的常用动作。
# 边界：不修改厂商 Driver 的任何实现，只替换其 operations 属性为封装层子类实例。
# 依赖：仅依赖厂商 Driver 与封装层 Operations。

from __future__ import annotations

from ..mso5204.driver import Mso5204Driver
from .operations import Mso5204WrapperOperations


# 把厂商 Driver 的 operations 换成封装层实现；厂商其余 31 个原子命名空间保持原样。
def install_wrapper_operations(driver: Mso5204Driver) -> Mso5204WrapperOperations:
    operations = Mso5204WrapperOperations(driver)
    driver.operations = operations  # type: ignore[assignment]
    return operations


# 创建已装配封装层 Operations 的 Driver；构造阶段不打开仪器、不发送 SCPI。
def create_wrapper_driver(session: object) -> Mso5204Driver:
    driver = Mso5204Driver(session)  # type: ignore[arg-type]
    install_wrapper_operations(driver)
    return driver


__all__ = ["create_wrapper_driver", "install_wrapper_operations"]

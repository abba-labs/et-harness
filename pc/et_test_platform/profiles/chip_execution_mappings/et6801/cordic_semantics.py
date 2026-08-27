# ET6801 已审核的 CORDIC 数值与错误刺激执行映射。
# 职责：保存 SVD 无法完整表达、且已由目标芯片资料或当前HIL表征的测试语义。
# 边界：只提供 ET6801 数据，不访问 Target、不执行硬件命令，也不包含公共 Case 流程。
# 依赖：仅依赖标准库不可变容器。

from __future__ import annotations

from types import MappingProxyType

# 定点核心函数代表向量。
# 字段顺序：arguments、scale、expected primary/secondary、primary/secondary compensation。
CORDIC_FIXED_VECTORS = MappingProxyType(
    {
        "sincos": ((0.0,), 0, 1.0, 0.0, 1.0, 1.0),
        "phase_modulus": ((0.5, 0.0), 0, 0.0, 0.5, 1.0, 1.0),
        "arctan": ((0.0,), 0, 0.0, None, 1.0, 1.0),
        "hsincos": ((0.0,), 1, 1.0, 0.0, 2.0, 2.0),
        "atanh": ((0.0,), 1, 0.0, None, 2.0, 1.0),
        "exp": ((0.0,), 1, 1.0, None, 8.0, 1.0),
        "ln": ((0.25,), 1, -0.6931471805599453, None, 4.0, 1.0),
        "sqrt": ((0.25,), 0, 0.5, None, 1.0, 1.0),
        "tan": ((0.0,), 0, 0.0, None, 1.0, 1.0),
    }
)

# 公共 Case 只按这些芯片执行参数执行Codec，不直接写入ET6801数值。
# absolute_tolerance沿用历史验证预算；当前HIL已证明ARCTAN Scale=7超出该预算，
# 因此它仍是待批准的验收边界，不能解释成ET6801全部Scale节点已经PASS。
CORDIC_NUMERIC_SEMANTICS = MappingProxyType(
    {
        "fixed_fraction_bits_16": 15,
        "fixed_fraction_bits_32": 31,
        "argument_storage_shift_16": 16,
        "argument_storage_shift_32": 0,
        "normalized_angle_divisor": 3.141592653589793,
        "direct_angle_fraction_bits_16": 12,
        "direct_angle_fraction_bits_32": 28,
        "absolute_tolerance": 1.0e-4,
        "scale_maximum": 7,
        "scale_affected_function": "arctan",
        "scale_argument": 0.5,
        "scale_input_multiplier_base": 2.0,
        "scale_output_multiplier_base": 2.0,
        "scale_output_angle_unit": 3.141592653589793,
        "precision_minimum_cycles": 1,
        "precision_maximum_cycles": 8,
        "argument_overflow_submit_count": 4,
        "argument_overflow_result_read_count": 2,
        "conversion_function": "sqrt",
        "conversion_overflow_input": 2.5,
        "conversion_underflow_input": 0.01,
        "conversion_recovery_input": 1.0,
    }
)

# 这些字符串只用于人工追溯当前映射的来源，不参与Case判定。
CORDIC_SEMANTIC_EVIDENCE = (
    "ET6801.svd:CORDIC.CTRL0/STATUS_RPT/RPT_CORDIC_FLOAT2FIXED/RES1_RPT/RES2_RPT",
    "DFP/Test/FPGATest/cordic_fpga_test.C:cases 01/02/20/22/23/29/33",
    "artifacts/runs/20260821_170400_cordic_full_hil/tests/cordic/session.json",
    "artifacts/runs/20260822_070101_086512_cordic_formal_cases/tests/cordic/session.json",
    "artifacts/runs/20260822_070244_378_cordic_p1_003_repeat/tests/cordic/session.json",
)

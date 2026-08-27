#include "et6801.h"
#include "et6x_crg.h"
#include "et_manual_test_config.h"
#include "et_manual_test_internal.h"

static void reset_peripheral_with_driver(CRG_Peripherals peripheral)
{
    CRG_unlockClockConfig();
    CRG_enablePeripheral(peripheral);
    CRG_resetPeripheral(peripheral);
    CRG_lockClockConfig();
}

static int verify_register_reset(const char *register_name, volatile uint32_t *target_register,
                                 uint32_t test_value, uint32_t reset_value,
                                 CRG_Peripherals peripheral)
{
    uint32_t round;
    uint32_t before_write;
    uint32_t after_write;
    uint32_t after_reset;
    int result = ET_MANUAL_RESULT_PASS;

    for (round = 0u; round < ET_MANUAL_CRG_REGISTER_REPEAT_COUNT; ++round)
    {
        /* 复位：每轮开始前建立相同的IP寄存器初始状态。 */
        reset_peripheral_with_driver(peripheral);
        before_write = READ_REG(*target_register);

        /* 激励：写入一个与SVD复位值不同且只包含合法字段的固定值。 */
        WRITE_REG(*target_register, test_value);
        after_write = READ_REG(*target_register);

        /* 复位：只调用CRG Driver，不直接操作CRG寄存器。 */
        reset_peripheral_with_driver(peripheral);
        after_reset = READ_REG(*target_register);

        /* 观测：逐轮打印寄存器写入和复位前后的真实读值。 */
        et_manual_log_text("[REGISTER] name=");
        et_manual_log_text(register_name);
        et_manual_log_text("\r\n");
        et_manual_log_u32("[OBSERVE] round", round + 1u);
        et_manual_log_u32("[OBSERVE] before_write", before_write);
        et_manual_log_u32("[OBSERVE] after_write", after_write);
        et_manual_log_u32("[OBSERVE] after_reset", after_reset);
        et_manual_log_u32("[EXPECT] written_value", test_value);
        et_manual_log_u32("[EXPECT] reset_value", reset_value);

        if ((before_write != reset_value) || (after_write != test_value) ||
            (after_reset != reset_value))
        {
            result = ET_MANUAL_RESULT_FAIL;
        }
    }

    return result;
}

/*
 * 测试Feature：CRG Driver软复位恢复FMAC、CRC、AES和CORDIC的配置寄存器默认值。
 * 测试方法：每个IP选择多个安全可读写寄存器，连续三轮调用CRG Driver执行复位、写入和回读。
 * 通过条件：每轮写入值均可回读，且每次CRG复位后均恢复为SVD定义的复位值。
 */
int et_manual_crg_register_reset_matrix(void)
{
    int failures = 0;

    et_manual_log_text("[MANUAL] chip=ET6801 case=crg_register_reset_matrix\r\n");

    /* FMAC：使用公开CRG Driver枚举，验证两个配置寄存器。 */
    failures += verify_register_reset(
        "FMAC.OUT_CR", &FMAC->OUT_CR, ET_MANUAL_CRG_FMAC_OUT_CR_TEST_VALUE,
        ET_MANUAL_CRG_FMAC_OUT_CR_RESET_VALUE, CRG_PERIPH_FMAC);
    failures += verify_register_reset(
        "FMAC.X1_BUF", &FMAC->X1_BUF, ET_MANUAL_CRG_FMAC_X1_BUF_TEST_VALUE,
        ET_MANUAL_CRG_FMAC_X1_BUF_RESET_VALUE, CRG_PERIPH_FMAC);

    /* CRC：使用公开CRG Driver枚举，验证控制、多项式和FIFO阈值寄存器。 */
    failures += verify_register_reset("CRC.CTRL", &CRC->CTRL,
                                      ET_MANUAL_CRG_CRC_CTRL_TEST_VALUE,
                                      ET_MANUAL_CRG_CRC_CTRL_RESET_VALUE, CRG_PERIPH_CRC);
    failures += verify_register_reset("CRC.POLY", &CRC->POLY,
                                      ET_MANUAL_CRG_CRC_POLY_TEST_VALUE,
                                      ET_MANUAL_CRG_CRC_POLY_RESET_VALUE, CRG_PERIPH_CRC);
    failures += verify_register_reset(
        "CRC.FIFO_TRHD", &CRC->FIFO_TRHD, ET_MANUAL_CRG_CRC_FIFO_TRHD_TEST_VALUE,
        ET_MANUAL_CRG_CRC_FIFO_TRHD_RESET_VALUE, CRG_PERIPH_CRC);

    /* AES：使用公开CRG Driver枚举，验证控制、密钥和长度寄存器。 */
    failures += verify_register_reset("AES.CRTL", &AES->CRTL,
                                      ET_MANUAL_CRG_AES_CRTL_TEST_VALUE,
                                      ET_MANUAL_CRG_AES_CRTL_RESET_VALUE, CRG_PERIPH_AES);
    failures += verify_register_reset("AES.WORK_KEY0", &AES->WORK_KEY0,
                                      ET_MANUAL_CRG_AES_KEY0_TEST_VALUE,
                                      ET_MANUAL_CRG_AES_KEY0_RESET_VALUE, CRG_PERIPH_AES);
    failures += verify_register_reset(
        "AES.DATA_SIZE0", &AES->DATA_SIZE0, ET_MANUAL_CRG_AES_DATA_SIZE0_TEST_VALUE,
        ET_MANUAL_CRG_AES_DATA_SIZE0_RESET_VALUE, CRG_PERIPH_AES);

    /* CORDIC0：使用公开CRG Driver枚举，验证控制和中断使能寄存器。 */
    failures += verify_register_reset(
        "CORDIC.CTRL0", &CORDIC->CTRL0, ET_MANUAL_CRG_CORDIC_CTRL0_TEST_VALUE,
        ET_MANUAL_CRG_CORDIC_CTRL0_RESET_VALUE, CRG_PERIPH_CORDIC);
    failures += verify_register_reset(
        "CORDIC.INT_EN", &CORDIC->INT_EN, ET_MANUAL_CRG_CORDIC_INT_EN_TEST_VALUE,
        ET_MANUAL_CRG_CORDIC_INT_EN_RESET_VALUE, CRG_PERIPH_CORDIC);

    et_manual_log_u32("[OBSERVE] failed_registers", (uint32_t)failures);

    return (failures == 0) ? ET_MANUAL_RESULT_PASS : ET_MANUAL_RESULT_FAIL;
}

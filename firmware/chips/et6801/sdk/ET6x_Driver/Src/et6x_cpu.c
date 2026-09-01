/** @file et6x_cpu.c @brief ET6801 CPU-owner test Driver extension. */

#include "et6x_cpu.h"

#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)

/******************** TEST DRIVER EXTENSION BEGIN ********************/

/* CPU NMI_SEL accepts writes only after this SVD-documented access key. */
#define CPU_TEST_SW_ACCESS_KEY 0x7879A8A9u
#define CPU_TEST_SW_LOCK_KEY 0x12345678u

/**
 * @brief Validate one CPU owner instance used by the test-only Driver extension.
 *
 * @param[in] CPUx CPU register block selected by the chip Wrap mapping.
 * @note This helper accepts only generated CPU0/CPU1 register block pointers and does not change
 *       CPU state.
 * @return 1 when CPUx is CPU0 or CPU1, otherwise 0.
 */
static uint8_t cpu_test_is_valid(CPU_Type *CPUx)
{
    return (uint8_t)((CPUx == CPU0) || (CPUx == CPU1));
}

/**
 * @brief Configure the M7 NMI source mask.
 *
 * @param[in] CPUx CPU register block.
 * @param[in] nmi_mask Four-bit source mask in the normalized Driver contract.
 * @note This is a test-only Driver extension. It uses the generated field mask and documented
 *       access-key sequence; no WDG or other IP state is changed.
 * @return DRV_OK when the mask is written, otherwise DRV_PARAM_ERR.
 */
DRV_Status CPU_testConfigureNmi(CPU_Type *CPUx, uint32_t nmi_mask)
{
    if ((cpu_test_is_valid(CPUx) == 0u) || ((nmi_mask & ~CPU_NMI_SEL_M7_NMI_MASK_Msk) != 0u))
    {
        return DRV_PARAM_ERR;
    }

    WRITE_REG(CPUx->KEY_CTRL, CPU_TEST_SW_ACCESS_KEY);
    MODIFY_REG(CPUx->NMI_SEL, CPU_NMI_SEL_M7_NMI_MASK_Msk, nmi_mask);
    WRITE_REG(CPUx->KEY_CTRL, CPU_TEST_SW_LOCK_KEY);

    return DRV_OK;
}

/**
 * @brief Read CPU NMI source reports and the M7 NMI status report.
 *
 * @param[in] CPUx CPU register block.
 * @param[out] snapshot Normalized NMI route snapshot.
 * @note This read-only extension reports CPU-owned facts and does not acknowledge a source.
 * @return DRV_OK when both arguments are valid, otherwise DRV_PARAM_ERR.
 */
DRV_Status CPU_testGetNmiSnapshot(CPU_Type *CPUx, CPU_TestNmiSnapshot *snapshot)
{
    uint32_t nmi_sel;

    if ((cpu_test_is_valid(CPUx) == 0u) || (snapshot == NULL))
    {
        return DRV_PARAM_ERR;
    }

    nmi_sel = READ_REG(CPUx->NMI_SEL);
    snapshot->source_raw =
        (nmi_sel & CPU_NMI_SEL_NMI_SRC_RPT_Msk) >> CPU_NMI_SEL_NMI_SRC_RPT_Pos;
    snapshot->source_masked =
        (nmi_sel & CPU_NMI_SEL_NMI_SRC_MASKED_RPT_Msk) >> CPU_NMI_SEL_NMI_SRC_MASKED_RPT_Pos;
    snapshot->nmi_mask =
        (nmi_sel & CPU_NMI_SEL_M7_NMI_MASK_Msk) >> CPU_NMI_SEL_M7_NMI_MASK_Pos;
    snapshot->nmi_status =
        (READ_REG(CPUx->STATUS_RPT) & CPU_STATUS_RPT_M7_NMI_RPT_Msk) >>
        CPU_STATUS_RPT_M7_NMI_RPT_Pos;

    return DRV_OK;
}

/**
 * @brief Return the generated CMSIS width of the CPU NMI source mask.
 *
 * @param[in] CPUx CPU register block.
 * @param[out] source_mask Normalized mask of supported NMI sources.
 * @note The returned mask is derived from the generated CMSIS field definition, not a test-case
 *       literal.
 * @return DRV_OK when both arguments are valid, otherwise DRV_PARAM_ERR.
 */
DRV_Status CPU_testGetNmiSourceMask(CPU_Type *CPUx, uint32_t *source_mask)
{
    if ((cpu_test_is_valid(CPUx) == 0u) || (source_mask == NULL))
    {
        return DRV_PARAM_ERR;
    }

    *source_mask = CPU_NMI_SEL_M7_NMI_MASK_Msk >> CPU_NMI_SEL_M7_NMI_MASK_Pos;

    return DRV_OK;
}

/********************* TEST DRIVER EXTENSION END *********************/

#endif

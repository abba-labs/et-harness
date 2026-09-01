/** @file et_cortex_wrap.c @brief Translate Cortex operations to the chip Driver. */
#include "et_cortex_wrap.h"

#include "et6x_cortex.h"

/**
 * @brief Enable the CPU instruction cache through the selected Cortex Driver.
 *
 * @note This function changes Cortex cache hardware state by enabling I-Cache. It has no Service,
 *       test-case or cross-IP side effect and does not report cache-test PASS/FAIL.
 *
 * @return ET_WRAP_STATUS_OK after the Driver enable operation is issued.
 */
et_wrap_status_t et_cortex_wrap_enable_instruction_cache(void)
{
    SCB_EnableICache();

    return ET_WRAP_STATUS_OK;
}

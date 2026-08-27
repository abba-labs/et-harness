/** @file et_system_wrap.c @brief Translate system operations to the selected Chip Driver. */
#include "et_system_wrap.h"

#include "system_et6x.h"

/**
 * @brief Refresh the SDK-maintained SystemCoreClock fact after clock configuration changes.
 *
 * @note This function asks the selected chip system Driver to recompute its core-clock software
 *       fact. It does not itself select clock sources, change dividers or execute test assertions.
 *
 * @return ET_WRAP_STATUS_OK after the SystemCoreClock refresh is issued.
 */
et_wrap_status_t et_system_wrap_update_core_clock(void)
{
    SystemCoreClockUpdate();

    return ET_WRAP_STATUS_OK;
}

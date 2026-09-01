#ifndef ET_SYSTEM_WRAP_H
#define ET_SYSTEM_WRAP_H

/**
 * @file et_system_wrap.h
 * @brief Stable bridge for CMSIS system-clock state.
 */

#include "et_wrap_status.h"

/** Refresh CMSIS SystemCoreClock from the active clock-tree state. */
et_wrap_status_t et_system_wrap_update_core_clock(void);

#endif

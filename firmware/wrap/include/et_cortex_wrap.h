#ifndef ET_CORTEX_WRAP_H
#define ET_CORTEX_WRAP_H

/** @file et_cortex_wrap.h @brief Stable Cortex core-control bridge. */

#include "et_wrap_status.h"

/** Enable Cortex instruction cache using the selected chip core Driver. */
et_wrap_status_t et_cortex_wrap_enable_instruction_cache(void);

#endif

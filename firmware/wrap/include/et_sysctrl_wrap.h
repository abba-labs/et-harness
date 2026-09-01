#ifndef ET_SYSCTRL_WRAP_H
#define ET_SYSCTRL_WRAP_H

/**
 * @file et_sysctrl_wrap.h
 * @brief Stable system-controller routing bridge.
 *
 * Request identity is resolved by the trusted PC control plane.  The Wrap
 * only validates controller/interface bounds and executes the supplied ID.
 */

#include <stdint.h>

#include "et_wrap_status.h"

/** Route one trusted DMA request ID to a controller interface. */
et_wrap_status_t et_sysctrl_wrap_configure_dma_request(uint8_t controller_id, uint8_t interface_id,
                                                       uint8_t request_id);
/** Release one controller interface by restoring its safe request route. */
et_wrap_status_t et_sysctrl_wrap_release_dma_request(uint8_t controller_id, uint8_t interface_id);

#endif

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

/** Public counter clock identities, mapped to Driver choices by Chip Config. */
typedef enum
{
    ET_SYSCTRL_SYSCNT_INTERNAL = 0u,
    ET_SYSCTRL_SYSCNT_EXTERNAL = 1u
} et_sysctrl_syscnt_source_t;

/** Actual system routing readback; no frequency or counter state is inferred. */
typedef struct
{
    uint8_t source;
    uint8_t halt_enabled;
} et_sysctrl_syscnt_routing_t;

/** Select a logical counter source; PC must stop the counter beforehand. */
et_wrap_status_t et_sysctrl_wrap_set_syscnt_source(uint8_t instance_id, uint8_t source);
/** Set only the system halt route, not the counter's own pause policy. */
et_wrap_status_t et_sysctrl_wrap_set_syscnt_halt(uint8_t instance_id, uint8_t enabled);
/** Read both routes through the owning SYSCTRL Driver. */
et_wrap_status_t et_sysctrl_wrap_get_syscnt_routing(uint8_t instance_id,
                                                    et_sysctrl_syscnt_routing_t *routing);

/** Route one trusted DMA request ID to a controller interface. */
et_wrap_status_t et_sysctrl_wrap_configure_dma_request(uint8_t controller_id, uint8_t interface_id,
                                                       uint8_t request_id);
/** Release one controller interface by restoring its safe request route. */
et_wrap_status_t et_sysctrl_wrap_release_dma_request(uint8_t controller_id, uint8_t interface_id);

#endif

#ifndef ET_RUNTIME_H
#define ET_RUNTIME_H

/**
 * @file et_runtime.h
 * @brief Lightweight owner of IRQ Manager, Service Router and Protocol.
 *
 * Runtime wires the common framework together; chip and IP setup remains in
 * board configuration, Wrap and Service layers.
 */

#include <stdint.h>

#include "et_irq_manager.h"
#include "et_protocol.h"
#include "et_service_router.h"

typedef struct
{
    uint32_t session_id;              /**< Expected PC session identity. */
    uint16_t session_open_service_id; /**< Service allowed to open session. */
    uint16_t session_open_command_id; /**< Command allowed to open session. */
    et_protocol_io_t io;              /**< Non-blocking transport callbacks. */
} et_runtime_config_t;

typedef struct
{
    et_irq_manager_t irqs;
    et_service_router_t services;
    et_protocol_t protocol;
    uint8_t started; /**< IRQ manager and protocol polling are active. */
} et_runtime_t;

/** Initialize common objects without starting IRQ dispatch. */
int et_runtime_init(et_runtime_t *runtime, const et_runtime_config_t *config);
/** Stop and release common runtime ownership. */
int et_runtime_deinit(et_runtime_t *runtime);
/** Activate IRQ dispatch and permit protocol polling. */
int et_runtime_start(et_runtime_t *runtime);
/** Perform one bounded transport, frame, message and Service progress step. */
size_t et_runtime_poll(et_runtime_t *runtime);
/** Drop incomplete receive state after a transport idle timeout. */
void et_runtime_reset_rx(et_runtime_t *runtime);
/** Report whether a partial frame is currently buffered. */
int et_runtime_rx_incomplete(const et_runtime_t *runtime);
/** Stop protocol progress and deactivate IRQ dispatch. */
void et_runtime_stop(et_runtime_t *runtime);
/** Return mutable Service Router storage for startup registration. */
et_service_router_t *et_runtime_services(et_runtime_t *runtime);
/** Return the shared IRQ Manager used by IP Services. */
et_irq_manager_t *et_runtime_irqs(et_runtime_t *runtime);
/** Return read-only protocol counters for Framework reporting. */
const et_protocol_stats_t *et_runtime_protocol_stats(const et_runtime_t *runtime);

#endif

#ifndef ET_CRG_WRAP_H
#define ET_CRG_WRAP_H

/** @file et_crg_wrap.h @brief Stable clock/reset generator bridge. */

#include <stdint.h>

#include "et_wrap_status.h"

typedef enum
{
    ET_CRG_WRAP_PERIPHERAL_UART = 0u,
    ET_CRG_WRAP_PERIPHERAL_DMA = 1u,
    ET_CRG_WRAP_PERIPHERAL_AES = 2u,
    ET_CRG_WRAP_PERIPHERAL_CORDIC = 3u,
    ET_CRG_WRAP_PERIPHERAL_FMAC = 4u,
    ET_CRG_WRAP_PERIPHERAL_CRC = 5u,
    ET_CRG_WRAP_PERIPHERAL_STIMER = 6u,
    ET_CRG_WRAP_PERIPHERAL_WDG = 7u,
    /** Inter-processor mailbox controller; instance is logical, not a CPU ID. */
    ET_CRG_WRAP_PERIPHERAL_IPCM = 8u
} et_crg_wrap_peripheral_t;

/** Stable WDG clock-source selections owned by the CRG, not by WDG. */
typedef enum
{
    ET_CRG_WRAP_WDG_CLOCK_HSOSC = 0u,
    ET_CRG_WRAP_WDG_CLOCK_APB1 = 1u
} et_crg_wrap_wdg_clock_source_t;

/** Readback of one logical WDG clock selection. */
typedef struct
{
    uint8_t source;
    uint8_t divider;
    uint8_t reserved[2];
} et_crg_wrap_wdg_clock_t;

/** Enable or disable the mapped peripheral instance clock. */
et_wrap_status_t et_crg_wrap_set_clock(uint8_t peripheral, uint8_t instance_id, uint8_t enabled);
/** Assert the mapped peripheral reset through the CRG Driver. */
et_wrap_status_t et_crg_wrap_reset(uint8_t peripheral, uint8_t instance_id);
/** Select one logical WDG clock through the CRG Driver. */
et_wrap_status_t et_crg_wrap_set_wdg_clock(uint8_t wdg_id, uint8_t source, uint8_t divider);
/** Read one logical WDG clock configuration through the CRG Driver. */
et_wrap_status_t et_crg_wrap_get_wdg_clock(uint8_t wdg_id, et_crg_wrap_wdg_clock_t *clock);

#endif

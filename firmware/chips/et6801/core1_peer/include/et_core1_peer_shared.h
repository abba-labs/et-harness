#ifndef ET_CORE1_PEER_SHARED_H
#define ET_CORE1_PEER_SHARED_H

/**
 * @file et_core1_peer_shared.h
 * @brief ET6801 Core1 ITCM smoke mailbox shared with the Core0 launcher.
 */

#include <stdint.h>

#include "et6801.h"

/* AXI SRAM1 is outside the current Core0 resource-pool linker window. */
#define ET_CORE1_PEER_MAILBOX_ADDRESS ((uintptr_t)AXI_SRAM1_BASE)
#define ET_CORE1_PEER_MAILBOX_MAGIC 0x45544331u
#define ET_CORE1_PEER_EXPECTED_CORE_INDEX 2u
#define ET_CORE1_PEER_HEARTBEAT_TARGET 2u
#define ET_CORE1_PEER_HEARTBEAT_DELAY_CYCLES 10000u
#define ET_CORE1_PEER_READY_WAIT_LIMIT 1000000u

/* ET6801 maps Core1 PFLASH1 at 0x08080000; both cores use address 0 for ITCM. */
#if defined(FLASH_CODE)
#define ET_CORE1_PEER_START_ADDRESS 0x08080000u
#else
#define ET_CORE1_PEER_START_ADDRESS 0x00000000u
#endif

typedef enum
{
    ET_CORE1_PEER_STATE_EMPTY = 0u,
    ET_CORE1_PEER_STATE_READY = 1u
} et_core1_peer_state_t;

typedef struct
{
    uint32_t magic;
    uint32_t state;
    uint32_t core_index;
    uint32_t heartbeat;
} et_core1_peer_mailbox_t;

#define ET_CORE1_PEER_MAILBOX ((volatile et_core1_peer_mailbox_t *)ET_CORE1_PEER_MAILBOX_ADDRESS)

#endif

#ifndef ET_FRAMEWORK_SERVICE_H
#define ET_FRAMEWORK_SERVICE_H

/**
 * @file et_framework_service.h
 * @brief Framework identity, echo, registry and protocol-statistics commands.
 */

#include <stdint.h>

#include "et_protocol.h"
#include "et_service_router.h"

#define ET_FRAMEWORK_SERVICE_ID 0x0000u
#define ET_FRAMEWORK_INSTANCE_ID 0u
/** Frozen Framework Wire and registry-hash dimensions. */
#define ET_FRAMEWORK_VERSION_FIELD_SIZE 2u
#define ET_FRAMEWORK_SERVICE_LIST_ENTRY_SIZE 4u
#define ET_FRAMEWORK_STATISTICS_RESPONSE_SIZE 16u
#define ET_FRAMEWORK_RESET_REASON_RESPONSE_SIZE 4u
#define ET_FRAMEWORK_REGISTRY_HASH_DIGITS 8u
#define ET_FRAMEWORK_REGISTRY_HASH_TEXT_SIZE (ET_FRAMEWORK_REGISTRY_HASH_DIGITS + 1u)
#define ET_FRAMEWORK_REGISTRY_HASH_NIBBLE_MASK 0x0fu
#define ET_FRAMEWORK_BITS_PER_BYTE 8u
#define ET_FRAMEWORK_BITS_PER_HEX_DIGIT 4u
#define ET_FRAMEWORK_FNV1A_OFFSET_BASIS 2166136261u
#define ET_FRAMEWORK_FNV1A_PRIME 16777619u

/* STATISTICS_GET response offsets; all fields are little-endian uint32_t values. */
#define ET_FRAMEWORK_STATISTICS_RX_FRAMES_OFFSET 0u
#define ET_FRAMEWORK_STATISTICS_TX_FRAMES_OFFSET 4u
#define ET_FRAMEWORK_STATISTICS_PARSE_ERRORS_OFFSET 8u
#define ET_FRAMEWORK_STATISTICS_DUPLICATE_REQUESTS_OFFSET 12u

typedef enum
{
    ET_FRAMEWORK_COMMAND_HELLO = 0x0001u,
    ET_FRAMEWORK_COMMAND_ECHO = 0x0002u,
    ET_FRAMEWORK_COMMAND_VERSION_GET = 0x0003u,
    ET_FRAMEWORK_COMMAND_SERVICE_LIST = 0x0004u,
    ET_FRAMEWORK_COMMAND_STATISTICS_GET = 0x0005u,
    ET_FRAMEWORK_COMMAND_RESET_REASON_GET = 0x0006u
} et_framework_command_t;

typedef struct
{
    const char *chip_id;            /**< Stable chip profile identity. */
    const char *firmware_build_id;  /**< Build identity reported to PC. */
    uint32_t reset_reason;          /**< Board-captured raw reset reason. */
    uint8_t reset_reason_supported; /**< reset_reason is meaningful when set. */
} et_framework_service_config_t;

typedef struct
{
    et_framework_service_config_t config;
    const et_service_router_t *router;
    const et_protocol_stats_t *protocol_stats;
    et_service_descriptor_t descriptor;
} et_framework_service_t;

/** Initialize Framework Service without mutating hardware. */
int et_framework_service_init(et_framework_service_t *service,
                              const et_framework_service_config_t *config,
                              const et_service_router_t *router,
                              const et_protocol_stats_t *protocol_stats);

/** Return the router descriptor of an initialized Framework Service. */
const et_service_descriptor_t *
et_framework_service_descriptor(const et_framework_service_t *service);

#endif

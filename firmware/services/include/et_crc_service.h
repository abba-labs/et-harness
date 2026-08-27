#ifndef ET_CRC_SERVICE_H
#define ET_CRC_SERVICE_H

/**
 * @file et_crc_service.h
 * @brief CRC firmware command service and its bounded runtime state.
 *
 * The service decodes CRC wire commands, calls only CRC Wrap and records the
 * minimum asynchronous IRQ evidence needed by the PC test plane. It does not
 * own complete test cases and never decides the final PASS or FAIL result.
 */

#include <stdint.h>

#include "et_crc_wrap.h"
#include "et_irq_manager.h"
/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
#include "et_service_factory.h"
/* ET_PLATFORM_SERVICE_FACTORY_END */
#include "et_service_router.h"

/** Stable service identifier carried by the common firmware protocol. */
#define ET_CRC_SERVICE_ID 0x0102u
/** Version of the CRC command bodies and capability response. */
#define ET_CRC_SERVICE_API_VERSION 1u
/** Fixed size, in bytes, of the CAPABILITIES_GET response body. */
#define ET_CRC_SERVICE_CAPABILITIES_SIZE 16u

/* Wire body sizes defined by the public CRC command contract, in bytes. */
#define ET_CRC_SERVICE_CONFIG_REQUEST_SIZE 12u
#define ET_CRC_SERVICE_CALCULATE_REQUEST_SIZE 12u
#define ET_CRC_SERVICE_CALCULATE_RESPONSE_SIZE 8u
#define ET_CRC_SERVICE_SOURCE_REQUEST_SIZE 4u
#define ET_CRC_SERVICE_IRQ_SNAPSHOT_RESPONSE_SIZE 20u
#define ET_CRC_SERVICE_TEST_INPUT_REQUEST_SIZE 8u
#define ET_CRC_SERVICE_TIMED_REQUEST_SIZE 16u
#define ET_CRC_SERVICE_TIMED_RESPONSE_SIZE 16u
#define ET_CRC_SERVICE_TEST_BURST_REQUEST_SIZE 40u
#define ET_CRC_SERVICE_TEST_BURST_RESPONSE_SIZE 16u

/* Maximum number of words carried by TEST_INPUT_BURST_32. */
#define ET_CRC_SERVICE_TEST_BURST_MAX_ITEMS ET_CRC_WRAP_MAX_BURST_ITEMS
/* Bounded Driver polling budget used by calculate commands. */
#define ET_CRC_SERVICE_CALCULATE_TIMEOUT_BUDGET 1000000u
/* Valid CONFIGURE flag bits and public mode/IRQ masks. */
#define ET_CRC_SERVICE_CONFIG_FLAGS_MASK 0x1fu
#define ET_CRC_SERVICE_MODE_BITS 0x07u
#define ET_CRC_SERVICE_IRQ_BITS 0x07u
/** CAPABILITIES flag: CALCULATE completes within one bounded firmware request. */
#define ET_CRC_SERVICE_CAPABILITY_FLAG_BOUNDED_SYNC (1u << 0)

/* CONFIGURE request offsets and packed Boolean flag bits. */
#define ET_CRC_SERVICE_CONFIG_MODE_OFFSET 0u
#define ET_CRC_SERVICE_CONFIG_FLAGS_OFFSET 1u
#define ET_CRC_SERVICE_CONFIG_XOR_OFFSET 2u
#define ET_CRC_SERVICE_CONFIG_FIFO_THRESHOLD_OFFSET 3u
#define ET_CRC_SERVICE_CONFIG_POLYNOMIAL_OFFSET 4u
#define ET_CRC_SERVICE_CONFIG_INITIAL_VALUE_OFFSET 8u
#define ET_CRC_SERVICE_CONFIG_REF_IN_FLAG (1u << 0)
#define ET_CRC_SERVICE_CONFIG_REF_OUT_FLAG (1u << 1)
#define ET_CRC_SERVICE_CONFIG_BYTE_SWAP_FLAG (1u << 2)
#define ET_CRC_SERVICE_CONFIG_AUTO_RELOAD_FLAG (1u << 3)
#define ET_CRC_SERVICE_CONFIG_RESULT_CHECK_FLAG (1u << 4)

/* CALCULATE, test-input and timed request offsets. */
#define ET_CRC_SERVICE_CALCULATE_SOURCE_OFFSET 0u
#define ET_CRC_SERVICE_CALCULATE_LENGTH_OFFSET 8u
#define ET_CRC_SERVICE_TEST_INPUT_WIDTH_OFFSET 0u
#define ET_CRC_SERVICE_TEST_INPUT_RESERVED_OFFSET 1u
#define ET_CRC_SERVICE_TEST_INPUT_RESERVED_SIZE 3u
#define ET_CRC_SERVICE_TEST_INPUT_VALUE_OFFSET 4u
#define ET_CRC_SERVICE_TIMED_SOURCE_OFFSET 0u
#define ET_CRC_SERVICE_TIMED_LENGTH_OFFSET 8u
#define ET_CRC_SERVICE_TIMED_REQUEST_RESERVED_OFFSET 12u
#define ET_CRC_SERVICE_BURST_COUNT_REQUEST_OFFSET 0u
#define ET_CRC_SERVICE_BURST_CHECKPOINT_REQUEST_OFFSET 1u
#define ET_CRC_SERVICE_BURST_RESERVED_OFFSET 2u
#define ET_CRC_SERVICE_BURST_RESERVED_SIZE 2u

/* Common one-word bodies and word-array encoding. */
#define ET_CRC_SERVICE_U32_BODY_SIZE ((uint16_t)sizeof(uint32_t))
#define ET_CRC_SERVICE_WORD_OFFSET(index) ((uint16_t)((index) * sizeof(uint32_t)))
#define ET_CRC_SERVICE_TEST_BURST_VALUES_OFFSET ET_CRC_SERVICE_U32_BODY_SIZE

/* CAPABILITIES_GET response offsets. */
#define ET_CRC_SERVICE_CAP_API_VERSION_OFFSET 0u
#define ET_CRC_SERVICE_CAP_STRUCT_SIZE_OFFSET 2u
#define ET_CRC_SERVICE_CAP_FEATURES_OFFSET ET_CRC_SERVICE_WORD_OFFSET(1u)
#define ET_CRC_SERVICE_CAP_MODE_MASK_OFFSET 8u
#define ET_CRC_SERVICE_CAP_IRQ_MASK_OFFSET 9u
#define ET_CRC_SERVICE_CAP_FIFO_THRESHOLD_OFFSET 10u
#define ET_CRC_SERVICE_CAP_FLAGS_OFFSET 11u
#define ET_CRC_SERVICE_CAP_MAX_CALCULATE_OFFSET ET_CRC_SERVICE_WORD_OFFSET(3u)

/* CALCULATE and IRQ_SNAPSHOT_GET response word offsets. */
#define ET_CRC_SERVICE_CALCULATE_RESULT_OFFSET ET_CRC_SERVICE_WORD_OFFSET(0u)
#define ET_CRC_SERVICE_CALCULATE_REMAINING_OFFSET ET_CRC_SERVICE_WORD_OFFSET(1u)
#define ET_CRC_SERVICE_IRQ_RAW_OFFSET ET_CRC_SERVICE_WORD_OFFSET(0u)
#define ET_CRC_SERVICE_IRQ_STATUS_OFFSET ET_CRC_SERVICE_WORD_OFFSET(1u)
#define ET_CRC_SERVICE_IRQ_EVENT_COUNT_OFFSET ET_CRC_SERVICE_WORD_OFFSET(2u)
#define ET_CRC_SERVICE_IRQ_LAST_EVENT_OFFSET ET_CRC_SERVICE_WORD_OFFSET(3u)
#define ET_CRC_SERVICE_IRQ_LAST_RAW_OFFSET ET_CRC_SERVICE_WORD_OFFSET(4u)

/* TIMED and TEST_INPUT_BURST response offsets. */
#define ET_CRC_SERVICE_TIMED_RESULT_OFFSET ET_CRC_SERVICE_WORD_OFFSET(0u)
#define ET_CRC_SERVICE_TIMED_CYCLES_OFFSET ET_CRC_SERVICE_WORD_OFFSET(1u)
#define ET_CRC_SERVICE_TIMED_VALUE_OFFSET ET_CRC_SERVICE_WORD_OFFSET(2u)
#define ET_CRC_SERVICE_TIMED_RESERVED_OFFSET ET_CRC_SERVICE_WORD_OFFSET(3u)
#define ET_CRC_SERVICE_BURST_COUNT_RESPONSE_OFFSET 0u
#define ET_CRC_SERVICE_BURST_CHECKPOINT_RESPONSE_OFFSET 1u
#define ET_CRC_SERVICE_BURST_CHECKPOINT_OFFSET ET_CRC_SERVICE_WORD_OFFSET(1u)
#define ET_CRC_SERVICE_BURST_FINAL_OFFSET ET_CRC_SERVICE_WORD_OFFSET(2u)
#define ET_CRC_SERVICE_BURST_OVERFLOW_OFFSET ET_CRC_SERVICE_WORD_OFFSET(3u)

/* FIFO_STATUS_GET returns one byte followed by zeroed reserved bytes. */
#define ET_CRC_SERVICE_FIFO_OVERFLOW_OFFSET 0u

/* Capability bits returned by CAPABILITIES_GET. */
#define ET_CRC_SERVICE_FEATURE_MODULE_ENABLE (1u << 0)
#define ET_CRC_SERVICE_FEATURE_POLYNOMIAL (1u << 1)
#define ET_CRC_SERVICE_FEATURE_INITIAL_SEED (1u << 2)
#define ET_CRC_SERVICE_FEATURE_BYTE_SWAP (1u << 3)
#define ET_CRC_SERVICE_FEATURE_REF_IN (1u << 4)
#define ET_CRC_SERVICE_FEATURE_REF_OUT (1u << 5)
#define ET_CRC_SERVICE_FEATURE_XOR_OUT (1u << 6)
#define ET_CRC_SERVICE_FEATURE_AUTO_LENGTH_RELOAD (1u << 7)
#define ET_CRC_SERVICE_FEATURE_RESULT_CHECK (1u << 8)
#define ET_CRC_SERVICE_FEATURE_LENGTH (1u << 9)
#define ET_CRC_SERVICE_FEATURE_RESULT (1u << 10)
#define ET_CRC_SERVICE_FEATURE_FIFO_THRESHOLD (1u << 11)
#define ET_CRC_SERVICE_FEATURE_FIFO_OVERFLOW (1u << 12)
#define ET_CRC_SERVICE_FEATURE_IRQ_ENABLE (1u << 13)
#define ET_CRC_SERVICE_FEATURE_IRQ_MASK (1u << 14)
#define ET_CRC_SERVICE_FEATURE_IRQ_FORCE (1u << 15)
#define ET_CRC_SERVICE_FEATURE_IRQ_CLEAR (1u << 16)
#define ET_CRC_SERVICE_FEATURE_IRQ_RAW_STATUS (1u << 17)
#define ET_CRC_SERVICE_FEATURE_CALCULATE (1u << 18)
#define ET_CRC_SERVICE_FEATURE_TEST_INPUT_WRITE (1u << 19)
#define ET_CRC_SERVICE_FEATURE_TEST_CALCULATE_TIMED (1u << 20)
#define ET_CRC_SERVICE_FEATURE_TEST_INPUT_BURST (1u << 21)

#define ET_CRC_SERVICE_BASE_FEATURES                                                               \
    (ET_CRC_SERVICE_FEATURE_MODULE_ENABLE | ET_CRC_SERVICE_FEATURE_POLYNOMIAL |                    \
     ET_CRC_SERVICE_FEATURE_INITIAL_SEED | ET_CRC_SERVICE_FEATURE_BYTE_SWAP |                      \
     ET_CRC_SERVICE_FEATURE_REF_IN | ET_CRC_SERVICE_FEATURE_REF_OUT |                              \
     ET_CRC_SERVICE_FEATURE_XOR_OUT | ET_CRC_SERVICE_FEATURE_AUTO_LENGTH_RELOAD |                  \
     ET_CRC_SERVICE_FEATURE_RESULT_CHECK | ET_CRC_SERVICE_FEATURE_LENGTH |                         \
     ET_CRC_SERVICE_FEATURE_RESULT | ET_CRC_SERVICE_FEATURE_FIFO_THRESHOLD |                       \
     ET_CRC_SERVICE_FEATURE_FIFO_OVERFLOW | ET_CRC_SERVICE_FEATURE_IRQ_ENABLE |                    \
     ET_CRC_SERVICE_FEATURE_IRQ_MASK | ET_CRC_SERVICE_FEATURE_IRQ_FORCE |                          \
     ET_CRC_SERVICE_FEATURE_IRQ_CLEAR | ET_CRC_SERVICE_FEATURE_IRQ_RAW_STATUS |                    \
     ET_CRC_SERVICE_FEATURE_CALCULATE)

#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)
#define ET_CRC_SERVICE_TEST_FEATURES                                                               \
    (ET_CRC_SERVICE_FEATURE_TEST_INPUT_WRITE | ET_CRC_SERVICE_FEATURE_TEST_CALCULATE_TIMED |       \
     ET_CRC_SERVICE_FEATURE_TEST_INPUT_BURST)
#else
#define ET_CRC_SERVICE_TEST_FEATURES 0u
#endif

#define ET_CRC_SERVICE_IMPLEMENTED_FEATURES                                                        \
    (ET_CRC_SERVICE_BASE_FEATURES | ET_CRC_SERVICE_TEST_FEATURES)

/** CRC command identifiers. Existing values are wire-stable. */
typedef enum
{
    ET_CRC_COMMAND_CAPABILITIES_GET = 0x0001u,     /**< Read runtime capability facts. */
    ET_CRC_COMMAND_ENABLE = 0x0002u,               /**< Enable the CRC module. */
    ET_CRC_COMMAND_DISABLE = 0x0003u,              /**< Disable CRC and release IRQ state. */
    ET_CRC_COMMAND_CONFIGURE = 0x0004u,            /**< Apply one complete CRC configuration. */
    ET_CRC_COMMAND_CALCULATE = 0x0005u,            /**< Calculate a bounded memory range. */
    ET_CRC_COMMAND_DATA_LENGTH_SET = 0x0006u,      /**< Program the expected input length. */
    ET_CRC_COMMAND_DATA_LENGTH_GET = 0x0007u,      /**< Read remaining input count. */
    ET_CRC_COMMAND_RESULT_GET = 0x0008u,           /**< Read the current CRC result. */
    ET_CRC_COMMAND_CHECK_VALUE_SET = 0x0009u,      /**< Program the result check value. */
    ET_CRC_COMMAND_FIFO_STATUS_GET = 0x000au,      /**< Read the FIFO overflow fact. */
    ET_CRC_COMMAND_IRQ_ENABLE = 0x000bu,           /**< Bind and enable CRC interrupt sources. */
    ET_CRC_COMMAND_IRQ_DISABLE = 0x000cu,          /**< Disable selected interrupt sources. */
    ET_CRC_COMMAND_IRQ_MASK = 0x000du,             /**< Mask selected interrupt sources. */
    ET_CRC_COMMAND_IRQ_UNMASK = 0x000eu,           /**< Unmask selected interrupt sources. */
    ET_CRC_COMMAND_IRQ_FORCE = 0x000fu,            /**< Force selected interrupt sources. */
    ET_CRC_COMMAND_IRQ_CLEAR = 0x0010u,            /**< Clear selected pending sources. */
    ET_CRC_COMMAND_IRQ_SNAPSHOT_GET = 0x0011u,     /**< Read hardware and callback evidence. */
    ET_CRC_COMMAND_TEST_INPUT_WRITE = 0x0012u,     /**< Write one typed CRC input item. */
    ET_CRC_COMMAND_TEST_CALCULATE_TIMED = 0x0013u, /**< Return CRC32 DWT cycle evidence. */
    ET_CRC_COMMAND_TEST_INPUT_BURST_32 = 0x0014u   /**< Execute one target-local word burst. */
} et_crc_command_t;

/**
 * Runtime state owned by one CRC service instance.
 *
 * Only module lifecycle and IRQ evidence are retained. Test vectors, expected
 * values, performance limits and complete case state remain owned by the PC.
 */
typedef struct
{
    et_crc_id_t crc_id;   /**< Stable logical CRC instance ID. */
    uint8_t enabled;      /**< Module enable command completed. */
    uint8_t configured;   /**< A complete configuration is active. */
    uint8_t mode;         /**< Active logical CRC width. */
    uint8_t irq_bound;    /**< CRC callback is bound to IRQ Manager. */
    uint8_t irq_priority; /**< Board-selected NVIC priority. */
    uint8_t reserved8[3];
    uint32_t irq_enabled_sources;       /**< Logical sources owned by this service. */
    volatile uint32_t irq_event_count;  /**< Saturating callback entry count. */
    volatile uint32_t irq_last_event;   /**< Last enabled source observed by callback. */
    volatile uint32_t irq_last_raw;     /**< Last raw hardware IRQ snapshot. */
    et_irq_manager_t *irq_manager;      /**< Shared IRQ binding infrastructure. */
    et_irq_route_t irq_route;           /**< Chip-mapped physical CRC IRQ route. */
    et_service_descriptor_t descriptor; /**< Router descriptor for this instance. */
} et_crc_service_t;

/**
 * @brief Initialize one CRC command service without touching CRC hardware.
 * @param service Service storage supplied by the application.
 * @param crc_id Stable logical CRC instance identifier.
 * @param irq_manager Common IRQ Manager used for dynamic callback binding.
 * @param irq_priority Board-selected NVIC priority for CRC test interrupts.
 * @return 0 on success, -1 when mandatory storage or dependencies are invalid.
 */
int et_crc_service_init(et_crc_service_t *service, et_crc_id_t crc_id,
                        et_irq_manager_t *irq_manager, uint8_t irq_priority);

/**
 * @brief Return the immutable router descriptor of one initialized service.
 * @param service Initialized CRC service instance.
 * @return Descriptor address, or NULL when service is NULL.
 */
const et_service_descriptor_t *et_crc_service_descriptor(const et_crc_service_t *service);

/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
/** Create one CRC Service through the chip-neutral group registry contract. */
int et_crc_service_create(void *storage, uint16_t instance_id,
                          const et_service_factory_context_t *context,
                          const et_service_descriptor_t **descriptor);
/* ET_PLATFORM_SERVICE_FACTORY_END */

#endif

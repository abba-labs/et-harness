#ifndef ET_SPI_SERVICE_H
#define ET_SPI_SERVICE_H
/** @file et_spi_service.h @brief SPI Wire actions and fixed ISR evidence storage. */
#include "et_service_router.h"
#include "et_irq_manager.h"
#include "et_spi_wrap.h"
/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
#include "et_service_factory.h"
/* ET_PLATFORM_SERVICE_FACTORY_END */

/** Public SPI Service identity; no chip identity is encoded in this value. */
#define ET_SPI_SERVICE_ID 0x010Bu
/** Body starts with one logical instance byte, followed by little-endian u32 words. */
#define ET_SPI_REQUEST_PREFIX_SIZE 1u
#define ET_SPI_WIRE_WORD_BYTES 4u
/** Largest fixed request/response is the sixteen-word public configuration. */
#define ET_SPI_MAX_WIRE_WORDS 16u

/** Named u32 positions in the public configuration and software event payloads. */
enum
{
    ET_SPI_CONFIG_ROLE = 0u,
    ET_SPI_CONFIG_FRAME_FORMAT = 1u,
    ET_SPI_CONFIG_CLOCK_MODE = 2u,
    ET_SPI_CONFIG_TRANSFER_MODE = 3u,
    ET_SPI_CONFIG_CS_POLICY = 4u,
    ET_SPI_CONFIG_FRAME_BITS = 5u,
    ET_SPI_CONFIG_FRAME_COUNT = 6u,
    ET_SPI_CONFIG_DIVIDER = 7u,
    ET_SPI_CONFIG_TARGET_OUTPUT_ENABLED = 8u,
    ET_SPI_CONFIG_LOOPBACK = 9u,
    ET_SPI_CONFIG_RX_SAMPLE_DELAY = 10u,
    ET_SPI_CONFIG_CONTROL_BITS = 11u,
    ET_SPI_CONFIG_SEQUENTIAL = 12u,
    ET_SPI_CONFIG_TRANSMIT = 13u,
    ET_SPI_CONFIG_HANDSHAKE = 14u,
    ET_SPI_CONFIG_RESERVED = 15u,
};
enum
{
    ET_SPI_EVENT_RAW_STATUS = 0u,
    ET_SPI_EVENT_MASKED_STATUS = 1u,
    ET_SPI_EVENT_LATCHED_EVENTS = 2u,
    ET_SPI_EVENT_EVENT_COUNT = 3u,
    ET_SPI_EVENT_UNEXPECTED_COUNT = 4u,
    ET_SPI_EVENT_OVERFLOW_COUNT = 5u,
    ET_SPI_EVENT_GENERATION = 6u,
    ET_SPI_EVENT_FAULT_FLAGS = 7u,
};
/** Request field positions: third FIFO threshold and third/fourth DMA arguments. */
enum
{
    ET_SPI_START_THRESHOLD = 2u,
    ET_SPI_DMA_TX_THRESHOLD = 2u,
    ET_SPI_DMA_RX_THRESHOLD = 3u
};
/** Fixed command envelopes, in enum order; values are u32 field counts. */
#define ET_SPI_REQUEST_WORD_COUNTS                                                                 \
    {0u, 16u, 0u, 1u, 0u, 1u, 1u, 1u, 1u, 3u, 0u, 0u,                                              \
     1u, 0u,  1u, 0u, 4u, 0u, 2u, 1u, 1u, 0u, 0u, 0u}
#define ET_SPI_RESPONSE_WORD_COUNTS                                                                \
    {7u, 0u, 16u, 0u, 0u, 0u, 0u, 0u, 0u, 0u, 14u, 2u,                                             \
     1u, 2u, 0u,  1u, 0u, 2u, 0u, 0u, 0u, 0u, 8u,  0u}
/** Event fault bits describe software capture failures, never hardware verdicts. */
#define ET_SPI_CAPTURE_FAULT_IO (1u << 0)
#define ET_SPI_CAPTURE_FAULT_OVERFLOW (1u << 1)
#define ET_SPI_CAPTURE_FAULT_UNEXPECTED (1u << 2)

/** Command values are local to SPI and frozen with the public IP Wire table. */
typedef enum
{
    ET_SPI_COMMAND_LIMITS_GET = 0u,
    ET_SPI_COMMAND_CONFIGURE = 1u,
    ET_SPI_COMMAND_CONFIG_GET = 2u,
    ET_SPI_COMMAND_ENABLE_SET = 3u,
    ET_SPI_COMMAND_FIFO_RESET = 4u,
    ET_SPI_COMMAND_DIVIDER_SET = 5u,
    ET_SPI_COMMAND_FRAME_COUNT_SET = 6u,
    ET_SPI_COMMAND_CS_SET = 7u,
    ET_SPI_COMMAND_LOOPBACK_SET = 8u,
    ET_SPI_COMMAND_FIFO_THRESHOLDS_SET = 9u,
    ET_SPI_COMMAND_SNAPSHOT_GET = 10u,
    ET_SPI_COMMAND_ERROR_STATUS_READ = 11u,
    ET_SPI_COMMAND_WRITE_FRAME = 12u,
    ET_SPI_COMMAND_READ_FRAME = 13u,
    ET_SPI_COMMAND_TEST_FIFO_WRITE_ONCE = 14u,
    ET_SPI_COMMAND_TEST_FIFO_READ_ONCE = 15u,
    ET_SPI_COMMAND_DMA_CONFIGURE = 16u,
    ET_SPI_COMMAND_DMA_ENDPOINT_GET = 17u,
    ET_SPI_COMMAND_IRQ_MASK_SET = 18u,
    ET_SPI_COMMAND_IRQ_CLEAR = 19u,
    ET_SPI_COMMAND_IRQ_CAPTURE_START = 20u,
    ET_SPI_COMMAND_IRQ_CAPTURE_STOP = 21u,
    ET_SPI_COMMAND_IRQ_EVENT_GET = 22u,
    ET_SPI_COMMAND_IRQ_EVENT_RESET = 23u,
    ET_SPI_COMMAND_COUNT
} et_spi_command_t;

/** Fixed evidence; ISR writes and command context reads under the IRQ critical section. */
typedef struct
{
    uint32_t raw_status, masked_status, latched_events, event_count;
    uint32_t unexpected_count, overflow_count, generation, fault_flags;
} et_spi_irq_event_t;

typedef struct
{
    et_spi_id_t spi_id;
    et_service_descriptor_t descriptor;
    et_irq_manager_t *irq_manager;
    et_irq_route_t route;
    volatile et_spi_irq_event_t event;
    uint32_t watched_sources;
    uint8_t irq_priority;
    uint8_t bound;
} et_spi_service_t;

int et_spi_service_init(et_spi_service_t *service, et_spi_id_t spi_id,
                        et_irq_manager_t *irq_manager, uint8_t irq_priority);
const et_service_descriptor_t *et_spi_service_descriptor(const et_spi_service_t *service);

/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
int et_spi_service_create(void *storage, uint16_t instance_id,
                          const et_service_factory_context_t *context,
                          const et_service_descriptor_t **descriptor);
/* ET_PLATFORM_SERVICE_FACTORY_END */
#endif

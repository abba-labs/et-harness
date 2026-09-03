#include "et_service_manifest.h"

/**
 * @file et_service_manifest.c
 * @brief Static composition of board-selected IP Service instances.
 *
 * Adding an IP changes this manifest, its own Service/Wrap, the board macros,
 * and the build manifest. The common startup and registration algorithm stay unchanged.
 */

#include <stdint.h>

#include "et_aes_service.h"
#include "et_board_config_contract.h"
#include "et_cordic_service.h"
#include "et_cpu_service.h"
#include "et_crc_service.h"
#include "et_crg_wrap.h"
#include "et_dma_service.h"
#include "et_fmac_service.h"
#include "et_ipcm_service.h"
#include "et_spinlock_service.h"
#include "et_stimer_service.h"
#include "et_uart_service.h"
#include "et_wdg_service.h"

#define ET_ARRAY_COUNT(array_) (sizeof(array_) / sizeof((array_)[0]))
#define ET_SERVICE_GROUP(instances_, storage_, priority_, create_)                                 \
    {.instance_ids = (instances_),                                                                 \
     .instance_count = ET_ARRAY_COUNT(instances_),                                                 \
     .storage = (storage_),                                                                        \
     .storage_count = ET_ARRAY_COUNT(storage_),                                                    \
     .storage_stride = sizeof((storage_)[0]),                                                      \
     .irq_priority = (priority_),                                                                  \
     .create = (create_)}

/* Board macros provide logical instance identities without exposing chip facts here. */
static const uint16_t test_uart_instances[] = {ET_TEST_UART_INSTANCE_IDS};
static const uint16_t test_dma_instances[] = {ET_TEST_DMA_INSTANCE_IDS};
static const uint16_t test_crc_instances[] = {ET_TEST_CRC_INSTANCE_IDS};
static const uint16_t test_aes_instances[] = {ET_TEST_AES_INSTANCE_IDS};
static const uint16_t test_fmac_instances[] = {ET_TEST_FMAC_INSTANCE_IDS};
static const uint16_t test_cordic_instances[] = {ET_TEST_CORDIC_INSTANCE_IDS};
static const uint16_t test_cpu_instances[] = {ET_TEST_CPU_INSTANCE_IDS};
static const uint16_t test_wdg_instances[] = {ET_TEST_WDG_INSTANCE_IDS};
static const uint16_t test_stimer_instances[] = {ET_TEST_STIMER_INSTANCE_IDS};
static const uint16_t test_spinlock_instances[] = {ET_TEST_SPINLOCK_INSTANCE_IDS};
static const uint16_t test_ipcm_instances[] = {ET_TEST_IPCM_INSTANCE_IDS};

/* Static storage keeps startup deterministic and avoids allocator ownership. */
static et_uart_service_t test_uart_services[ET_ARRAY_COUNT(test_uart_instances)];
static et_dma_service_t test_dma_services[ET_ARRAY_COUNT(test_dma_instances)];
static et_crc_service_t test_crc_services[ET_ARRAY_COUNT(test_crc_instances)];
static et_aes_service_t test_aes_services[ET_ARRAY_COUNT(test_aes_instances)];
static et_fmac_service_t test_fmac_services[ET_ARRAY_COUNT(test_fmac_instances)];
static et_cordic_service_t test_cordic_services[ET_ARRAY_COUNT(test_cordic_instances)];
static et_cpu_service_t test_cpu_services[ET_ARRAY_COUNT(test_cpu_instances)];
static et_wdg_service_t test_wdg_services[ET_ARRAY_COUNT(test_wdg_instances)];
static et_stimer_service_t test_stimer_services[ET_ARRAY_COUNT(test_stimer_instances)];
static et_spinlock_service_t test_spinlock_services[ET_ARRAY_COUNT(test_spinlock_instances)];
static et_ipcm_service_t test_ipcm_services[ET_ARRAY_COUNT(test_ipcm_instances)];

/* One row is the complete Application-level registration declaration for one IP. */
static const et_service_group_t service_groups[] = {
    ET_SERVICE_GROUP(test_uart_instances, test_uart_services, ET_TEST_UART_CAPTURE_IRQ_PRIORITY,
                     et_uart_service_create),
    ET_SERVICE_GROUP(test_dma_instances, test_dma_services, ET_SERVICE_IRQ_PRIORITY_UNUSED,
                     et_dma_service_create),
    ET_SERVICE_GROUP(test_crc_instances, test_crc_services, ET_TEST_CRC_IRQ_PRIORITY,
                     et_crc_service_create),
    ET_SERVICE_GROUP(test_aes_instances, test_aes_services, ET_TEST_AES_IRQ_PRIORITY,
                     et_aes_service_create),
    ET_SERVICE_GROUP(test_fmac_instances, test_fmac_services, ET_TEST_FMAC_IRQ_PRIORITY,
                     et_fmac_service_create),
    ET_SERVICE_GROUP(test_cordic_instances, test_cordic_services, ET_TEST_CORDIC_IRQ_PRIORITY,
                     et_cordic_service_create),
    ET_SERVICE_GROUP(test_cpu_instances, test_cpu_services, ET_SERVICE_IRQ_PRIORITY_UNUSED,
                     et_cpu_service_create),
    ET_SERVICE_GROUP(test_wdg_instances, test_wdg_services, ET_TEST_WDG_IRQ_PRIORITY,
                     et_wdg_service_create),
    ET_SERVICE_GROUP(test_stimer_instances, test_stimer_services, ET_TEST_STIMER_IRQ_PRIORITY,
                     et_stimer_service_create),
    ET_SERVICE_GROUP(test_spinlock_instances, test_spinlock_services,
                     ET_SERVICE_IRQ_PRIORITY_UNUSED, et_spinlock_service_create),
    ET_SERVICE_GROUP(test_ipcm_instances, test_ipcm_services, ET_TEST_IPCM_IRQ_PRIORITY,
                     et_ipcm_service_create),
};

/**
 * @brief Prepare board-selected hardware prerequisites required before Service registration.
 *
 * @note This function enables and resets each board-selected test UART through the CRG Wrap. It
 *       does not initialize UART Service state or register any command descriptor.
 *
 * @return 0 when every required UART clock/reset operation succeeds.
 * @return -1 when any board-selected UART prerequisite cannot be prepared.
 */
int et_service_manifest_prepare(void)
{
    size_t index;

    for (index = 0u; index < ET_ARRAY_COUNT(test_uart_instances); ++index)
    {
        if ((et_crg_wrap_set_clock(ET_CRG_WRAP_PERIPHERAL_UART, test_uart_instances[index], 1u) !=
             ET_WRAP_STATUS_OK) ||
            (et_crg_wrap_reset(ET_CRG_WRAP_PERIPHERAL_UART, test_uart_instances[index]) !=
             ET_WRAP_STATUS_OK))
        {
            return -1;
        }
    }

    return 0;
}

/**
 * @brief Return the immutable Application Service-group manifest.
 *
 * @param[out] group_count Number of Service groups published by the returned manifest.
 *
 * @note The returned table and its Service storage are statically allocated for deterministic
 *       startup. This accessor does not initialize Services or touch peripheral hardware.
 *
 * @return Pointer to the immutable Service-group table when group_count is valid.
 * @return NULL when group_count is NULL.
 */
const et_service_group_t *et_service_manifest_get(size_t *group_count)
{
    if (group_count == NULL)
    {
        return NULL;
    }

    *group_count = ET_ARRAY_COUNT(service_groups);

    return service_groups;
}

/** @file et_sysctrl_wrap.c @brief Execute direct SYSCTRL DMAMUX operations. */
#include "et_sysctrl_wrap.h"

#include <stddef.h>

#include "et6x_sysctrl.h"
#include "et_chip_wrap_config.h"

typedef struct
{
    uint8_t controller_id;
    AHBDMA_Type *instance;
    uint8_t interface_count;
} et_sysctrl_dma_mapping_t;

static const et_sysctrl_dma_mapping_t dma_mappings[] = ET_CHIP_SYSCTRL_DMA_MAP_TABLE;

/**
 * @brief Resolve one stable DMA controller/interface pair to the selected SYSCTRL Driver mapping.
 *
 * @param[in] controller_id Stable logical DMA controller identifier.
 * @param[in] interface_id Stable logical DMAMUX interface identifier.
 *
 * @note This helper reads compile-time Chip Config mapping data only and does not change DMAMUX
 *       hardware state or reserve an interface.
 *
 * @return Pointer to the matching chip mapping, or NULL when the controller/interface is unsupported.
 */
static const et_sysctrl_dma_mapping_t *find_controller_mapping(uint8_t controller_id,
                                                               uint8_t interface_id)
{
    size_t index;

    for (index = 0u; index < (sizeof(dma_mappings) / sizeof(dma_mappings[0])); ++index)
    {
        if ((dma_mappings[index].controller_id == controller_id) &&
            (interface_id < dma_mappings[index].interface_count))
        {
            return &dma_mappings[index];
        }
    }

    return NULL;
}

/**
 * @brief Route one logical DMA request through a mapped SYSCTRL DMAMUX interface.
 *
 * @param[in] controller_id Stable logical DMA controller identifier.
 * @param[in] interface_id Stable logical DMAMUX interface identifier.
 * @param[in] request_id Stable request selector translated to the selected Driver type.
 *
 * @note This function changes SYSCTRL DMAMUX hardware. It does not start a DMA transfer or infer an
 *       interface/request default; the complete route is supplied by the caller.
 *
 * @return ET_WRAP_STATUS_OK when the mapped request route is configured.
 * @return ET_WRAP_STATUS_NOT_SUPPORTED when the logical controller/interface is unavailable.
 */
et_wrap_status_t et_sysctrl_wrap_configure_dma_request(uint8_t controller_id, uint8_t interface_id,
                                                       uint8_t request_id)
{
    const et_sysctrl_dma_mapping_t *mapping;

    mapping = find_controller_mapping(controller_id, interface_id);

    if (mapping == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    SYSCTRL_configDMAMux(mapping->instance, interface_id, (SYSCTRL_DMAReqIdx)request_id);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Release one mapped SYSCTRL DMAMUX interface from its current DMA request route.
 *
 * @param[in] controller_id Stable logical DMA controller identifier.
 * @param[in] interface_id Stable logical DMAMUX interface identifier.
 *
 * @note This function changes SYSCTRL DMAMUX hardware by freeing the selected interface. It does not
 *       stop a DMA channel or clear DMA evidence owned by another layer.
 *
 * @return ET_WRAP_STATUS_OK when the mapped interface is released.
 * @return ET_WRAP_STATUS_NOT_SUPPORTED when the logical controller/interface is unavailable.
 */
et_wrap_status_t et_sysctrl_wrap_release_dma_request(uint8_t controller_id, uint8_t interface_id)
{
    const et_sysctrl_dma_mapping_t *mapping;

    mapping = find_controller_mapping(controller_id, interface_id);

    if (mapping == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    SYSCTRL_freeDMAMuxInterface(mapping->instance, interface_id);

    return ET_WRAP_STATUS_OK;
}

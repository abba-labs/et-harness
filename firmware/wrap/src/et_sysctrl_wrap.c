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

typedef struct
{
    uint8_t instance_id;
    SYSCTRL_SYSCNTClockSource internal_source;
    SYSCTRL_SYSCNTClockSource external_source;
} et_sysctrl_syscnt_mapping_t;

static const et_sysctrl_syscnt_mapping_t syscnt_mappings[] = ET_CHIP_SYSCTRL_SYSCNT_MAP_TABLE;

/**
 * @brief Resolve the counter's system routing identity.
 * @param[in] instance_id Logical counter instance.
 * @return Matching static mapping, or NULL when absent.
 * @note Only reads Chip Config; no register or clock access.
 */
static const et_sysctrl_syscnt_mapping_t *find_syscnt_mapping(uint8_t instance_id)
{
    size_t index;

    for (index = 0u; index < sizeof(syscnt_mappings) / sizeof(syscnt_mappings[0]); ++index)
    {
        if (syscnt_mappings[index].instance_id == instance_id)
        {
            return &syscnt_mappings[index];
        }
    }

    return NULL;
}

/**
 * @brief Select one mapped system counter clock source.
 * @param[in] instance_id Logical counter instance.
 * @param[in] source Public INTERNAL or EXTERNAL identity.
 * @return Stable argument, support or completion status.
 * @note Changes only SYSCTRL selection; PC owns counter stop and subsequent restart.
 */
et_wrap_status_t et_sysctrl_wrap_set_syscnt_source(uint8_t instance_id, uint8_t source)
{
    const et_sysctrl_syscnt_mapping_t *mapping = find_syscnt_mapping(instance_id);

    if (source > ET_SYSCTRL_SYSCNT_EXTERNAL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (mapping == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    SYSC_unlockCriticalRegs();
    SYSCTRL_selectSYSCNTClockSource(
        source == ET_SYSCTRL_SYSCNT_INTERNAL ? mapping->internal_source : mapping->external_source);
    SYSC_lockCriticalRegs();

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Set the mapped system debug-halt route.
 * @param[in] instance_id Logical counter instance.
 * @param[in] enabled Boolean route state.
 * @return Stable argument, support or Driver status.
 * @note Does not halt the CPU or change the counter's own HDBG policy.
 */
et_wrap_status_t et_sysctrl_wrap_set_syscnt_halt(uint8_t instance_id, uint8_t enabled)
{
    DRV_Status result;

    if (enabled > 1u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (find_syscnt_mapping(instance_id) == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    SYSC_unlockCriticalRegs();
    result = SYSCTRL_testSetSYSCNTHaltRoute(enabled);
    SYSC_lockCriticalRegs();

    return result == DRV_OK ? ET_WRAP_STATUS_OK : ET_WRAP_STATUS_STATE_ERROR;
}

/**
 * @brief Return real system routing readback in public identities.
 * @param[in] instance_id Logical counter instance.
 * @param[out] routing Public source and halt route readback.
 * @return Stable argument, support or Driver status.
 * @note Does not read counter state or assume the selected source's frequency.
 */
et_wrap_status_t et_sysctrl_wrap_get_syscnt_routing(uint8_t instance_id,
                                                    et_sysctrl_syscnt_routing_t *routing)
{
    const et_sysctrl_syscnt_mapping_t *mapping = find_syscnt_mapping(instance_id);
    SYSCTRL_TestSyscntRouting actual;

    if (routing == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (mapping == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    if (SYSCTRL_testGetSYSCNTRouting(&actual) != DRV_OK)
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    if ((actual.source != mapping->internal_source) && (actual.source != mapping->external_source))
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    routing->source = actual.source == mapping->internal_source ? ET_SYSCTRL_SYSCNT_INTERNAL
                                                                : ET_SYSCTRL_SYSCNT_EXTERNAL;
    routing->halt_enabled = actual.halt_enabled;

    return ET_WRAP_STATUS_OK;
}

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

/** @file et_cpu_wrap.c @brief Implement the stable CPU-owner NMI bridge. */

#include "et_cpu_wrap.h"

#include <stddef.h>

#include "et6x_cpu.h"
#include "et_chip_wrap_config.h"

typedef struct
{
    et_cpu_id_t cpu_id;
    CPU_Type *driver_instance;
} et_cpu_nmi_mapping_t;

static const et_cpu_nmi_mapping_t cpu_nmi_mappings[] = ET_CHIP_CPU_NMI_MAP_TABLE;

/**
 * @brief Resolve one logical CPU to its chip Driver instance.
 *
 * @param[in] cpu_id Stable CPU identity from the public Service contract.
 * @note This lookup only consults the chip mapping table and never accesses hardware.
 * @return Matching Driver mapping, or NULL when the chip does not publish it.
 */
static const et_cpu_nmi_mapping_t *find_mapping(et_cpu_id_t cpu_id)
{
    size_t index;

    for (index = 0u; index < (sizeof(cpu_nmi_mappings) / sizeof(cpu_nmi_mappings[0])); ++index)
    {
        if (cpu_nmi_mappings[index].cpu_id == cpu_id)
        {
            return &cpu_nmi_mappings[index];
        }
    }

    return NULL;
}

/**
 * @brief Configure one CPU NMI mask through the CPU Driver only.
 *
 * @param[in] cpu_id Stable CPU identity.
 * @param[in] nmi_mask Normalized source mask accepted by the selected Driver.
 * @note The Wrap translates the stable identity and delegates exactly one CPU-driver action;
 *       it does not configure WDG, IRQ, or another IP.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_cpu_wrap_nmi_configure(et_cpu_id_t cpu_id, uint32_t nmi_mask)
{
    const et_cpu_nmi_mapping_t *mapping = find_mapping(cpu_id);

    if (mapping == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return (CPU_testConfigureNmi(mapping->driver_instance, nmi_mask) == DRV_OK)
               ? ET_WRAP_STATUS_OK
               : ET_WRAP_STATUS_INVALID_ARGUMENT;
}

/**
 * @brief Read one CPU's supported NMI source mask through the CPU Driver.
 *
 * @param[in] cpu_id Stable CPU identity.
 * @param[out] source_mask Destination for the normalized supported-source mask.
 * @note The source mask is returned by the CPU Driver and is not synthesized in this Wrap.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_cpu_wrap_nmi_source_mask_get(et_cpu_id_t cpu_id, uint32_t *source_mask)
{
    const et_cpu_nmi_mapping_t *mapping = find_mapping(cpu_id);

    if ((mapping == NULL) || (source_mask == NULL))
    {
        return (mapping == NULL) ? ET_WRAP_STATUS_NOT_SUPPORTED : ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return (CPU_testGetNmiSourceMask(mapping->driver_instance, source_mask) == DRV_OK)
               ? ET_WRAP_STATUS_OK
               : ET_WRAP_STATUS_IO_ERROR;
}

/**
 * @brief Read one CPU NMI route snapshot through the CPU Driver only.
 *
 * @param[in] cpu_id Stable CPU identity.
 * @param[out] snapshot Destination for normalized route facts.
 * @note The snapshot is copied from the CPU Driver extension without reading registers here.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_cpu_wrap_nmi_snapshot_get(et_cpu_id_t cpu_id,
                                              et_cpu_wrap_nmi_snapshot_t *snapshot)
{
    const et_cpu_nmi_mapping_t *mapping = find_mapping(cpu_id);
    CPU_TestNmiSnapshot driver_snapshot;

    if ((mapping == NULL) || (snapshot == NULL))
    {
        return (mapping == NULL) ? ET_WRAP_STATUS_NOT_SUPPORTED : ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (CPU_testGetNmiSnapshot(mapping->driver_instance, &driver_snapshot) != DRV_OK)
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    snapshot->source_raw = driver_snapshot.source_raw;
    snapshot->source_masked = driver_snapshot.source_masked;
    snapshot->nmi_mask = driver_snapshot.nmi_mask;
    snapshot->nmi_status = driver_snapshot.nmi_status;

    return ET_WRAP_STATUS_OK;
}

#ifndef ET_CPU_WRAP_H
#define ET_CPU_WRAP_H

/** @file et_cpu_wrap.h @brief Stable CPU-owner NMI bridge. */

#include <stdint.h>

#include "et_wrap_status.h"

/** Logical CPU instance identity supplied by the Application manifest. */
typedef uint16_t et_cpu_id_t;

/** Normalized CPU NMI route snapshot; no CMSIS register names are exposed. */
typedef struct
{
    uint32_t source_raw;
    uint32_t source_masked;
    uint32_t nmi_mask;
    uint32_t nmi_status;
} et_cpu_wrap_nmi_snapshot_t;

/** Configure the selected CPU's NMI source mask through the CPU Driver. */
et_wrap_status_t et_cpu_wrap_nmi_configure(et_cpu_id_t cpu_id, uint32_t nmi_mask);
/** Read the selected CPU's supported NMI source-mask bits. */
et_wrap_status_t et_cpu_wrap_nmi_source_mask_get(et_cpu_id_t cpu_id, uint32_t *source_mask);
/** Read the selected CPU's NMI route and status facts without clearing them. */
et_wrap_status_t et_cpu_wrap_nmi_snapshot_get(et_cpu_id_t cpu_id,
                                              et_cpu_wrap_nmi_snapshot_t *snapshot);

#endif

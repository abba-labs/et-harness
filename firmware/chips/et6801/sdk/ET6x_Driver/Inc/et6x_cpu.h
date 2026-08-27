#ifndef __ET6X_CPU_H
#define __ET6X_CPU_H

/** @file et6x_cpu.h @brief ET6801 CPU-owner test Driver extension. */

#include "et6x.h"

#ifdef __cplusplus
extern "C"
{
#endif

#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)

/******************** TEST DRIVER EXTENSION BEGIN ********************/

/**
 * @brief Snapshot the CPU NMI route and M7 NMI report fields needed by the test platform.
 *
 * The fields are represented as normalized values so the CPU Wrap does not expose CMSIS register
 * members or ET6801 bit positions to the Service and PC layers.
 */
typedef struct
{
    uint32_t source_raw;
    uint32_t source_masked;
    uint32_t nmi_mask;
    uint32_t nmi_status;
} CPU_TestNmiSnapshot;

/** Configure the CPU M7 NMI source mask using the documented CPU access key. */
DRV_Status CPU_testConfigureNmi(CPU_Type *CPUx, uint32_t nmi_mask);
/** Read the CPU NMI route and M7 NMI report fields without clearing them. */
DRV_Status CPU_testGetNmiSnapshot(CPU_Type *CPUx, CPU_TestNmiSnapshot *snapshot);
/** Return the selected CPU's supported normalized NMI source-mask bits. */
DRV_Status CPU_testGetNmiSourceMask(CPU_Type *CPUx, uint32_t *source_mask);

/********************* TEST DRIVER EXTENSION END *********************/

#endif

#ifdef __cplusplus
}
#endif

#endif /* __ET6X_CPU_H */

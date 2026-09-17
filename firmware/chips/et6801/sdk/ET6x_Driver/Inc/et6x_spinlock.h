/*
 * Copyright (c) 2022, Chengdu ET Microelectronics Co., Ltd.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 *
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the, distribution.
 * 3. All advertising materials mentioning features or use of this software
 *    must display the following acknowledgement:
 *    This product includes software developed by the "ETMCU software". and
 *    its contributors.
 * 4. Neither the name of the Group nor the names of its contributors may
 *    be used to endorse or promote products derived from this software
 *    without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
 * WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
 * IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
 * INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
 * NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
 * PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
 * WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY
 * OF SUCH DAMAGE.
 */

#ifndef __ET6x_SPINLOCK_H
#define __ET6x_SPINLOCK_H

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include "et6x.h"

/** @addtogroup ET6001_Driver
 * @{
 */

/** @addtogroup SPINLOCK
 * @{
 */

/* spinlock init mode */
#define SPINLOCK_FAST_MODE (1U)
#define SPINLOCK_NORMAL_MODE (2U)

/* spinlock resource ID minimum and maximum */
#define SPINLOCK_RESID_MIN (0U)
#define SPINLOCK_RESID_MAX (63U)

/* spinlock resource ID index */
#define RES_ID_0 0U
#define RES_ID_1 1U
#define RES_ID_2 2U
#define RES_ID_3 3U
#define RES_ID_4 4U
#define RES_ID_5 5U
#define RES_ID_6 6U
#define RES_ID_7 7U
#define RES_ID_8 8U
#define RES_ID_9 9U
#define RES_ID_10 10U
#define RES_ID_11 11U
#define RES_ID_12 12U
#define RES_ID_13 13U
#define RES_ID_14 14U
#define RES_ID_15 15U
#define RES_ID_16 16U
#define RES_ID_17 17U
#define RES_ID_18 18U
#define RES_ID_19 19U
#define RES_ID_20 20U
#define RES_ID_21 21U
#define RES_ID_22 22U
#define RES_ID_23 23U
#define RES_ID_24 24U
#define RES_ID_25 25U
#define RES_ID_26 26U
#define RES_ID_27 27U
#define RES_ID_28 28U
#define RES_ID_29 29U
#define RES_ID_30 30U
#define RES_ID_31 31U
#define RES_ID_32 32U
#define RES_ID_33 33U
#define RES_ID_34 34U
#define RES_ID_35 35U
#define RES_ID_36 36U
#define RES_ID_37 37U
#define RES_ID_38 38U
#define RES_ID_39 39U
#define RES_ID_40 40U
#define RES_ID_41 41U
#define RES_ID_42 42U
#define RES_ID_43 43U
#define RES_ID_44 44U
#define RES_ID_45 45U
#define RES_ID_46 46U
#define RES_ID_47 47U
#define RES_ID_48 48U
#define RES_ID_49 49U
#define RES_ID_50 50U
#define RES_ID_51 51U
#define RES_ID_52 52U
#define RES_ID_53 53U
#define RES_ID_54 54U
#define RES_ID_55 55U
#define RES_ID_56 56U
#define RES_ID_57 57U
#define RES_ID_58 58U
#define RES_ID_59 59U
#define RES_ID_60 60U
#define RES_ID_61 61U
#define RES_ID_62 62U
#define RES_ID_63 63U

/* spinlock process ID minimum and maximum */
#define SPINLOCK_PROCESSID_MIN (0U)
#define SPINLOCK_PROCESSID_MAX (15U)

/* spinlock process ID index */
#define PROCESS_ID_0 0U
#define PROCESS_ID_1 1U
#define PROCESS_ID_2 2U
#define PROCESS_ID_3 3U
#define PROCESS_ID_4 4U
#define PROCESS_ID_5 5U
#define PROCESS_ID_6 6U
#define PROCESS_ID_7 7U
#define PROCESS_ID_8 8U
#define PROCESS_ID_9 9U
#define PROCESS_ID_10 10U
#define PROCESS_ID_11 11U
#define PROCESS_ID_12 12U
#define PROCESS_ID_13 13U
#define PROCESS_ID_14 14U
#define PROCESS_ID_15 15U

    void SPINLOCK_init(uint32_t mode);
    void SPINLOCK_deInit(void);
    void SPINLOCK_acquire(uint32_t resID, uint32_t processID);
    DRV_Status SPINLOCK_acquireTry(uint32_t resID, uint32_t processID);
    void SPINLOCK_release(uint32_t resID, uint32_t processID);
    void SPINLOCK_fastAcquire(uint32_t resID);
    DRV_Status SPINLOCK_fastAcquireTry(uint32_t resID);
    void SPINLOCK_fastRelease(uint32_t resID);
    bool SPINLOCK_isResourceAcquired(uint32_t resID);
    void SPINLOCK_batchReleaseAll(void);
    void SPINLOCK_globalReleaseAll(void);

#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)

    /******************** TEST DRIVER EXTENSION BEGIN ********************/

    typedef enum
    {
        SPINLOCK_TEST_CLEAR_BATCH = 0U,
        SPINLOCK_TEST_CLEAR_GLOBAL = 1U
    } SPINLOCK_TestClearScope;

    typedef struct
    {
        uint32_t flagsLow;
        uint32_t flagsHigh;
    } SPINLOCK_TestFlagSnapshot;

    typedef struct
    {
        uint32_t locked;
        uint32_t ownerValid;
        uint32_t masterId;
        uint32_t processIdValid;
        uint32_t processId;
    } SPINLOCK_TestResourceSnapshot;

    typedef enum
    {
        SPINLOCK_TEST_PEER_JOB_TRY_HOLD = 0U,
        SPINLOCK_TEST_PEER_JOB_BLOCKING_HOLD = 1U,
        SPINLOCK_TEST_PEER_JOB_RELEASE_ONCE = 2U,
        SPINLOCK_TEST_PEER_JOB_HOLD = 3U,
        SPINLOCK_TEST_PEER_JOB_STRESS = 4U
    } SPINLOCK_TestPeerJobType;

    typedef enum
    {
        SPINLOCK_TEST_PEER_JOB_IDLE = 0U,
        SPINLOCK_TEST_PEER_JOB_STARTED = 1U,
        SPINLOCK_TEST_PEER_JOB_WAITING = 2U,
        SPINLOCK_TEST_PEER_JOB_HOLDING = 3U,
        SPINLOCK_TEST_PEER_JOB_DONE = 4U,
        SPINLOCK_TEST_PEER_JOB_ABORTED = 5U,
        SPINLOCK_TEST_PEER_JOB_ERROR = 6U
    } SPINLOCK_TestPeerJobState;

    typedef enum
    {
        SPINLOCK_TEST_PEER_RESULT_NONE = 0U,
        SPINLOCK_TEST_PEER_RESULT_ACQUIRED = 1U,
        SPINLOCK_TEST_PEER_RESULT_BUSY = 2U,
        SPINLOCK_TEST_PEER_RESULT_RELEASED = 3U,
        SPINLOCK_TEST_PEER_RESULT_COMPLETED = 4U,
        SPINLOCK_TEST_PEER_RESULT_ABORTED = 5U,
        SPINLOCK_TEST_PEER_RESULT_ERROR = 6U
    } SPINLOCK_TestPeerResult;

    typedef enum
    {
        SPINLOCK_TEST_PEER_CONTROL_NONE = 0U,
        SPINLOCK_TEST_PEER_CONTROL_RELEASE = 1U,
        SPINLOCK_TEST_PEER_CONTROL_ABORT = 2U
    } SPINLOCK_TestPeerControl;

    typedef struct
    {
        uint32_t jobType;
        uint32_t mode;
        uint32_t resourceId;
        uint32_t processId;
        uint32_t loopCount;
    } SPINLOCK_TestPeerJobConfig;

    typedef struct
    {
        uint32_t state;
        uint32_t result;
        uint32_t enterCount;
        uint32_t completedCount;
        uint32_t masterId;
    } SPINLOCK_TestPeerJobSnapshot;

    typedef struct
    {
        uint32_t sharedCounter;
        uint32_t violationCount;
    } SPINLOCK_TestSharedSnapshot;

    /**
 * @brief Configure module enable and mode without releasing any resource.
 * @param enable Nonzero enables the module; zero disables it.
 * @param mode SPINLOCK_FAST_MODE or SPINLOCK_NORMAL_MODE.
 * @return DRV_OK on success or DRV_PARAM_ERR for an invalid mode.
 */
    DRV_Status SPINLOCK_testConfigure(uint32_t enable, uint32_t mode);

    /**
 * @brief Read module enable and mode without changing lock state.
 * @param pEnable Destination for the normalized enable state.
 * @param pMode Destination for SPINLOCK_FAST_MODE or SPINLOCK_NORMAL_MODE.
 * @return DRV_OK on success or DRV_PARAM_ERR for a null destination.
 */
    DRV_Status SPINLOCK_testGetConfig(uint32_t *pEnable, uint32_t *pMode);

    /**
 * @brief Read both side-effect-free resource flag banks.
 * @param pSnapshot Destination for low and high resource flags.
 * @return DRV_OK on success or DRV_PARAM_ERR for a null destination.
 */
    DRV_Status SPINLOCK_testGetFlagSnapshot(SPINLOCK_TestFlagSnapshot *pSnapshot);

    /**
 * @brief Read one resource safely, consulting flags before owner information.
 * @param resID Resource ID in the SDK-declared range.
 * @param pSnapshot Destination for normalized lock and owner facts.
 * @return DRV_OK on success or DRV_PARAM_ERR for invalid arguments.
 * @note The owner register is never read while the resource is free because
 *       that read can acquire a resource in one-step mode.
 */
    DRV_Status SPINLOCK_testGetResourceSnapshot(uint32_t resID,
                                                SPINLOCK_TestResourceSnapshot *pSnapshot);

    /**
 * @brief Return the hardware Master ID used by the current execution entity.
 * @param pMasterId Destination for the selected SDK Core ID.
 * @return DRV_OK on success or DRV_PARAM_ERR for a null destination.
 */
    DRV_Status SPINLOCK_testGetCurrentMasterId(uint32_t *pMasterId);

    /**
 * @brief Probe protected clear behavior with valid or deliberately invalid authorization.
 * @param scope Batch or global clear register selection.
 * @param authorized Nonzero uses the valid SDK key; zero uses an invalid key.
 * @return DRV_OK on success or DRV_PARAM_ERR for an invalid scope.
 */
    DRV_Status SPINLOCK_testClearProbe(SPINLOCK_TestClearScope scope, uint32_t authorized);

    /** Return whether the independently deployed peer image is ready. */
    DRV_Status SPINLOCK_testPeerReady(uint32_t *pReady);

    /** Copy the embedded peer image into Core1 ITCM and start the peer core. */
    DRV_Status SPINLOCK_testBootPeer(const uint8_t *image, uint32_t image_size);

    /** Return the peer execution entity's hardware Master ID. */
    DRV_Status SPINLOCK_testGetPeerMasterId(uint32_t *pMasterId);

    /** Submit one asynchronous peer job through the chip-owned shared mailbox. */
    DRV_Status SPINLOCK_testPeerJobStart(const SPINLOCK_TestPeerJobConfig *pConfig);

    /** Read the current asynchronous peer job state and counters. */
    DRV_Status SPINLOCK_testPeerJobGetSnapshot(SPINLOCK_TestPeerJobSnapshot *pSnapshot);

    /** Request release or abort for the active peer job. */
    DRV_Status SPINLOCK_testPeerJobControl(SPINLOCK_TestPeerControl control);

    /** Reset shared stress counters before starting both execution entities. */
    DRV_Status SPINLOCK_testSharedStressReset(void);

    /** Run the local execution entity's bounded shared-counter stress loop. */
    DRV_Status SPINLOCK_testLocalStressRun(uint32_t resourceId, uint32_t loopCount,
                                           uint32_t *pCompletedCount);

    /** Read shared stress counter and mutual-exclusion violation facts. */
    DRV_Status SPINLOCK_testSharedStressGetSnapshot(SPINLOCK_TestSharedSnapshot *pSnapshot);

    /** Run the Core1 peer command loop after the chip startup code releases Core1. */
    void SPINLOCK_testPeerRunForever(void);

    /********************* TEST DRIVER EXTENSION END *********************/

#endif

    /**
 * @}
 */

    /**
 * @}
 */

#ifdef __cplusplus
}
#endif

#endif /* __ET6x_SPINLOCK_H */

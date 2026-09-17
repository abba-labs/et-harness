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

/* Includes ------------------------------------------------------------------*/
#include "et6x_spinlock.h"
#include "et6x_dualcore.h"
#include "et6x_sysctrl.h"
#include <string.h>

/* Private typedef -----------------------------------------------------------*/
/* Private define ------------------------------------------------------------*/
/*! Parameter validity check for SPINLOCK initialization mode . */
#define IS_SPINLOCK_INIT_MODE(_MODE_)                                                              \
    ((_MODE_) == SPINLOCK_FAST_MODE || (_MODE_) == SPINLOCK_NORMAL_MODE)

/*! Parameter validity check for SPINLOCK resource ID . */
#define IS_SPINLOCK_RESID(_RESID_) ((_RESID_) <= SPINLOCK_RESID_MAX)

/*! Parameter validity check for SPINLOCK process ID . */
#define IS_SPINLOCK_PROCESSID(_PROCESSID_) ((_PROCESSID_) <= SPINLOCK_PROCESSID_MAX)

/* the number of try to lock spinlock resource */
#define SPINLOCK_TRY_COUNT_MAX (1000U)

/* SPINLOCK control bit mask */
#define SL_LOCK_ONE_STEP_EN                                                                        \
    (SPINLOCK_SL_LOCK_EN_SL_LOCK_EN_Msk | SPINLOCK_SL_LOCK_EN_SL_LOCK_EN_WRITE_Msk |               \
     SPINLOCK_SL_LOCK_EN_SL_TWO_STEP_MODE_EN_WRITE_Msk)
#define SL_LOCK_TWO_STEP_EN                                                                        \
    (SPINLOCK_SL_LOCK_EN_SL_LOCK_EN_Msk | SPINLOCK_SL_LOCK_EN_SL_TWO_STEP_MODE_EN_Msk |            \
     SPINLOCK_SL_LOCK_EN_SL_LOCK_EN_WRITE_Msk | SPINLOCK_SL_LOCK_EN_SL_TWO_STEP_MODE_EN_WRITE_Msk)
#define SL_LOCK_DISABLE (SPINLOCK_SL_LOCK_EN_SL_LOCK_EN_WRITE_Msk)

/* unlock corresponding CPU resourse, used only when SPIN LOCK initial stage*/
#define SL_BATCH_LOCK_CLR_KEY (0x67891230U)

/* unlock all SPIN LOCK resourse, used only when SPIN LOCK initial stage*/
#define SL_GLB_LOCK_CLR_KEY (0xCDEF1230)

/**
 * @brief Init SPINLOCK module
 *
 * @param mode: SPINLOCK module work mode
 */
void SPINLOCK_init(uint32_t mode)
{
    assert_param(IS_SPINLOCK_INIT_MODE(mode));

    if (mode == SPINLOCK_FAST_MODE)
    {
        WRITE_REG(SPINLOCK->SL_LOCK_EN, SL_LOCK_ONE_STEP_EN);
    }
    else
    {
        WRITE_REG(SPINLOCK->SL_LOCK_EN, SL_LOCK_TWO_STEP_EN);
    }

    SPINLOCK_globalReleaseAll();
}

/**
 * @brief Deinit SPINLOCK
 *
 */
void SPINLOCK_deInit(void)
{
    SPINLOCK_globalReleaseAll();
    WRITE_REG(SPINLOCK->SL_LOCK_EN, SL_LOCK_DISABLE);
}

/**
 * @brief Acquire a SPINLOCK with specified resource ID and process ID in a 2-step
 *
 * @param resID: the spinlock resource ID
 * @param processID: the process or thread ID
 */
void SPINLOCK_acquire(uint32_t resID, uint32_t processID)
{
    assert_param(IS_SPINLOCK_RESID(resID));
    assert_param(IS_SPINLOCK_PROCESSID(processID));

    /* add judgement to avoid using <SPINLOCK_Acquire> in fast mode SPINLOCK peripheral */
    if (READ_BIT(SPINLOCK->SL_LOCK_EN, SPINLOCK_SL_LOCK_EN_SL_TWO_STEP_MODE_EN_Msk) == 0)
    {
        return;
    }

    do
    {
        WRITE_REG(
            SPINLOCK->SL_LOCK_INFO_ARRAY[resID].SL_LOCK_INFO,
            (SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_FLAG_Msk |
             ((DUALCORE_getCurrentCoreId()
               << SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_MASTER_ID_Pos) &
              SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_MASTER_ID_Msk) |
             ((processID << SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_PROCESS_ID_Pos) &
              SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_PROCESS_ID_Msk)));
    } while (
        (READ_REG(SPINLOCK->SL_LOCK_INFO_ARRAY[resID].SL_LOCK_INFO) !=
         (SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_FLAG_Msk |
          ((DUALCORE_getCurrentCoreId()
            << SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_MASTER_ID_Pos) &
           SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_MASTER_ID_Msk) |
          ((processID << SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_PROCESS_ID_Pos) &
           SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_PROCESS_ID_Msk) |
          SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_PROCESS_ID_INIT_Msk)));
}

/**
 * @brief Try to acquire a SPINLOCK with specified resource ID and process ID in a 2-step
 *
 * @param resID: the spinlock resource ID
 * @param processID: the process or thread ID
 * @return DRV_Status
 *         [DRV_ERROR]: work mode does not match
 *         [DRV_TIMEOUT]: resource is not released during timeout time
 *         [DRV_OK]: aquire resource success
 */
DRV_Status SPINLOCK_acquireTry(uint32_t resID, uint32_t processID)
{
    uint32_t count = 0U;

    assert_param(IS_SPINLOCK_RESID(resID));
    assert_param(IS_SPINLOCK_PROCESSID(processID));

    /* add judgement to avoid using <SPINLOCK_Acquire_Try> in fast mode SPINLOCK peripheral */

    if (READ_BIT(SPINLOCK->SL_LOCK_EN, SPINLOCK_SL_LOCK_EN_SL_TWO_STEP_MODE_EN_Msk) == 0)
    {
        return DRV_ERROR;
    }

    do
    {
        WRITE_REG(SPINLOCK->SL_LOCK_INFO_ARRAY[resID].SL_LOCK_INFO,
                  SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_FLAG_Msk |
                      ((DUALCORE_getCurrentCoreId()
                        << SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_MASTER_ID_Pos) &
                       SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_MASTER_ID_Msk) |
                      ((processID
                        << SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_PROCESS_ID_Pos) &
                       SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_PROCESS_ID_Msk));
        count++;
    } while (
        (READ_REG(SPINLOCK->SL_LOCK_INFO_ARRAY[resID].SL_LOCK_INFO) !=
         (SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_FLAG_Msk |
          ((DUALCORE_getCurrentCoreId()
            << SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_MASTER_ID_Pos) &
           SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_MASTER_ID_Msk) |
          ((processID << SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_PROCESS_ID_Pos) &
           SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_PROCESS_ID_Msk) |
          SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_PROCESS_ID_INIT_Msk)) &&
        count < SPINLOCK_TRY_COUNT_MAX);

    if (count >= SPINLOCK_TRY_COUNT_MAX)
    {
        return DRV_TIMEOUT;
    }

    return DRV_OK;
}

/**
 * @brief Release a SPINLOCK with specified resource ID and process ID
 *
 * @param resID: the spinlock resource ID
 * @param processID: the process or thread ID
 */
void SPINLOCK_release(uint32_t resID, uint32_t processID)
{
    assert_param(IS_SPINLOCK_RESID(resID));
    assert_param(IS_SPINLOCK_PROCESSID(processID));

    WRITE_REG(
        SPINLOCK->SL_LOCK_INFO_ARRAY[resID].SL_LOCK_INFO,
        ((DUALCORE_getCurrentCoreId()
          << SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_MASTER_ID_Pos) &
         SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_MASTER_ID_Msk) |
            ((processID << SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_PROCESS_ID_Pos) &
             SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_PROCESS_ID_Msk));
}

/**
 * @brief  Acquire a SPINLOCK with specified resource ID in a 1-step,
 *
 * @param resID: the spinlock resource ID
 */
void SPINLOCK_fastAcquire(uint32_t resID)
{
    assert_param(IS_SPINLOCK_RESID(resID));

    /* add judgement to avoid using <SPINLOCK_FastAcquire> in normal mode SPINLOCK peripheral */
    if (READ_BIT(SPINLOCK->SL_LOCK_EN, SPINLOCK_SL_LOCK_EN_SL_TWO_STEP_MODE_EN_Msk) != 0)
    {
        return;
    }

    while (READ_REG(SPINLOCK->SL_LOCK_INFO_ARRAY[resID].SL_LOCK_INFO) !=
           (SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_FLAG_Msk |
            ((DUALCORE_getCurrentCoreId()
              << SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_MASTER_ID_Pos) &
             SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_MASTER_ID_Msk)))
    {
        /* spin */
    }
}

/**
 * @brief  Try to acquire a SPINLOCK with specified resource ID in a 1-step,
 *
 * @param resID: the spinlock resource ID
 * @return DRV_Status
 *         [DRV_ERROR]: work mode does not match
 *         [DRV_TIMEOUT]: resource is not released during timeout time
 *         [DRV_OK]: aquire resource success
 */
DRV_Status SPINLOCK_fastAcquireTry(uint32_t resID)
{
    uint32_t count = 0U;

    assert_param(IS_SPINLOCK_RESID(resID));

    /* add judgement to avoid using <SPINLOCK_FastAcquire_Try> in normal mode SPINLOCK peripheral */
    if (READ_BIT(SPINLOCK->SL_LOCK_EN, SPINLOCK_SL_LOCK_EN_SL_TWO_STEP_MODE_EN_Msk) != 0)
    {
        return DRV_ERROR;
    }

    while ((READ_REG(SPINLOCK->SL_LOCK_INFO_ARRAY[resID].SL_LOCK_INFO) !=
            (SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_FLAG_Msk |
             ((DUALCORE_getCurrentCoreId()
               << SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_MASTER_ID_Pos) &
              SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_MASTER_ID_Msk))) &&
           count < SPINLOCK_TRY_COUNT_MAX)
    {
        count++;
    }
    if (count >= SPINLOCK_TRY_COUNT_MAX)
    {
        return DRV_TIMEOUT;
    }

    return DRV_OK;
}

/**
 * @brief Release a SPINLOCK with specified resource ID
 *
 * @param resID: the spinlock resource ID
 */
void SPINLOCK_fastRelease(uint32_t resID)
{
    assert_param(IS_SPINLOCK_RESID(resID));

    WRITE_REG(SPINLOCK->SL_LOCK_INFO_ARRAY[resID].SL_LOCK_INFO, 0);
}

/**
 * @brief Get the status of SPINLOCK specified by resource ID
 *
 * @param resID: the spinlock resource ID
 * @return true: resource is not free
 * @return false: resource is free
 */
bool SPINLOCK_isResourceAcquired(uint32_t resID)
{
    assert_param(IS_SPINLOCK_RESID(resID));

    if (resID < 32U)
    {
        return (READ_BIT(SPINLOCK->SL_LOCK_FLAG_RPT1, BIT_MASK(resID))) != 0U;
    }
    else if (resID < 64U)
    {
        return (READ_BIT(SPINLOCK->SL_LOCK_FLAG_RPT2, BIT_MASK(resID - 32))) != 0U;
    }
    else
    {
        return false;
    }
}

/**
 * @brief Release all batch resourse of current core.
 *
 * This operation applied when system initial
 * stage or reset from a exception.
 */
void SPINLOCK_batchReleaseAll(void)
{
    WRITE_REG(SPINLOCK->SL_BATCH_LOCK_CLR, SL_BATCH_LOCK_CLR_KEY);
}

/**
 * @brief Release all resourse of all core.
 *
 * This operation applied when system initial
 * stage or reset from a exception.
 *
 */
void SPINLOCK_globalReleaseAll(void)
{
    WRITE_REG(SPINLOCK->SL_GLOBAL_LOCK_CLR, SL_GLB_LOCK_CLR_KEY);
}

#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)

/******************** TEST DRIVER EXTENSION BEGIN ********************/

/* An invalid probe must not accidentally equal either hardware authorization key. */
#define SPINLOCK_TEST_INVALID_CLEAR_KEY (0U)

/* AXI SRAM1 is shared by both ET6801 cores and is outside the common resource pool. */
#define SPINLOCK_TEST_PEER_MAILBOX_ADDRESS ((uintptr_t)AXI_SRAM1_BASE)
#define SPINLOCK_TEST_PEER_MAILBOX_MAGIC (0x45544331U)
#define SPINLOCK_TEST_PEER_READY (1U)
#define SPINLOCK_TEST_PEER_ACTIVE_OWNER_NONE (0U)
#define SPINLOCK_TEST_PEER_COMMAND_FIRST_SEQUENCE (1U)
#define SPINLOCK_TEST_PEER_HEARTBEAT_DELAY_CYCLES (10000U)

/* 从核镜像拉起后的就绪等待上限，约50ms量级。 */
#define SPINLOCK_TEST_PEER_BOOT_POLL_LIMIT (500000U)

typedef struct
{
    uint32_t magic;
    uint32_t peerReady;
    uint32_t coreIndex;
    uint32_t heartbeat;
    uint32_t commandSequence;
    uint32_t acknowledgeSequence;
    uint32_t jobType;
    uint32_t jobState;
    uint32_t mode;
    uint32_t resourceId;
    uint32_t processId;
    uint32_t loopCount;
    uint32_t control;
    uint32_t result;
    uint32_t enterCount;
    uint32_t completedCount;
    uint32_t peerMasterId;
    uint32_t sharedCounter;
    uint32_t criticalOwner;
    uint32_t violationCount;
} SPINLOCK_TestPeerMailbox;

#define SPINLOCK_TEST_PEER_MAILBOX                                                                 \
    ((volatile SPINLOCK_TestPeerMailbox *)SPINLOCK_TEST_PEER_MAILBOX_ADDRESS)

static uint32_t SPINLOCK_testPeerIsActive(uint32_t state)
{
    return ((state == SPINLOCK_TEST_PEER_JOB_STARTED) ||
            (state == SPINLOCK_TEST_PEER_JOB_WAITING) || (state == SPINLOCK_TEST_PEER_JOB_HOLDING))
               ? 1U
               : 0U;
}

static DRV_Status SPINLOCK_testAcquireByMode(uint32_t mode, uint32_t resourceId, uint32_t processId)
{
    if (mode == SPINLOCK_FAST_MODE)
    {
        return SPINLOCK_fastAcquireTry(resourceId);
    }

    if (mode == SPINLOCK_NORMAL_MODE)
    {
        return SPINLOCK_acquireTry(resourceId, processId);
    }

    return DRV_PARAM_ERR;
}

static void SPINLOCK_testReleaseByMode(uint32_t mode, uint32_t resourceId, uint32_t processId)
{
    if (mode == SPINLOCK_FAST_MODE)
    {
        SPINLOCK_fastRelease(resourceId);
    }
    else
    {
        SPINLOCK_release(resourceId, processId);
    }
}

static void SPINLOCK_testCriticalCounterIncrement(volatile SPINLOCK_TestPeerMailbox *pMailbox,
                                                  uint32_t owner)
{
    __DMB();

    if (pMailbox->criticalOwner != SPINLOCK_TEST_PEER_ACTIVE_OWNER_NONE)
    {
        ++pMailbox->violationCount;
    }

    pMailbox->criticalOwner = owner;
    __DMB();
    ++pMailbox->sharedCounter;
    __DMB();
    pMailbox->criticalOwner = SPINLOCK_TEST_PEER_ACTIVE_OWNER_NONE;
    __DMB();
}

/**
 * @brief Configure module state without invoking the SDK initialization clear.
 */
DRV_Status SPINLOCK_testConfigure(uint32_t enable, uint32_t mode)
{
    uint32_t value;

    if (!IS_SPINLOCK_INIT_MODE(mode))
    {
        return DRV_PARAM_ERR;
    }

    if (enable == 0U)
    {
        value = SL_LOCK_DISABLE;
    }
    else if (mode == SPINLOCK_FAST_MODE)
    {
        value = SL_LOCK_ONE_STEP_EN;
    }
    else
    {
        value = SL_LOCK_TWO_STEP_EN;
    }

    WRITE_REG(SPINLOCK->SL_LOCK_EN, value);

    return DRV_OK;
}

/**
 * @brief Read normalized module configuration without changing hardware state.
 */
DRV_Status SPINLOCK_testGetConfig(uint32_t *pEnable, uint32_t *pMode)
{
    uint32_t value;

    if ((pEnable == NULL) || (pMode == NULL))
    {
        return DRV_PARAM_ERR;
    }

    value = READ_REG(SPINLOCK->SL_LOCK_EN);
    *pEnable = ((value & SPINLOCK_SL_LOCK_EN_SL_LOCK_EN_Msk) != 0U) ? 1U : 0U;
    *pMode = ((value & SPINLOCK_SL_LOCK_EN_SL_TWO_STEP_MODE_EN_Msk) != 0U) ? SPINLOCK_NORMAL_MODE
                                                                           : SPINLOCK_FAST_MODE;

    return DRV_OK;
}

/**
 * @brief Read both side-effect-free resource flag banks.
 */
DRV_Status SPINLOCK_testGetFlagSnapshot(SPINLOCK_TestFlagSnapshot *pSnapshot)
{
    if (pSnapshot == NULL)
    {
        return DRV_PARAM_ERR;
    }

    pSnapshot->flagsLow = READ_REG(SPINLOCK->SL_LOCK_FLAG_RPT1);
    pSnapshot->flagsHigh = READ_REG(SPINLOCK->SL_LOCK_FLAG_RPT2);

    return DRV_OK;
}

/**
 * @brief Read one resource without acquiring an idle one as an observation side effect.
 */
DRV_Status SPINLOCK_testGetResourceSnapshot(uint32_t resID,
                                            SPINLOCK_TestResourceSnapshot *pSnapshot)
{
    uint32_t info;

    if ((!IS_SPINLOCK_RESID(resID)) || (pSnapshot == NULL))
    {
        return DRV_PARAM_ERR;
    }

    pSnapshot->locked = SPINLOCK_isResourceAcquired(resID) ? 1U : 0U;
    pSnapshot->ownerValid = 0U;
    pSnapshot->masterId = 0U;
    pSnapshot->processIdValid = 0U;
    pSnapshot->processId = 0U;

    if (pSnapshot->locked == 0U)
    {
        return DRV_OK;
    }

    info = READ_REG(SPINLOCK->SL_LOCK_INFO_ARRAY[resID].SL_LOCK_INFO);
    pSnapshot->ownerValid = 1U;
    pSnapshot->masterId =
        (info & SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_MASTER_ID_Msk) >>
        SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_MASTER_ID_Pos;
    pSnapshot->processIdValid =
        ((info & SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_PROCESS_ID_INIT_Msk) != 0U)
            ? 1U
            : 0U;
    pSnapshot->processId =
        (info & SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_PROCESS_ID_Msk) >>
        SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_PROCESS_ID_Pos;

    return DRV_OK;
}

/**
 * @brief Return the SDK Core ID written into the hardware owner field.
 */
DRV_Status SPINLOCK_testGetCurrentMasterId(uint32_t *pMasterId)
{
    if (pMasterId == NULL)
    {
        return DRV_PARAM_ERR;
    }

    *pMasterId = DUALCORE_getCurrentCoreId();

    return DRV_OK;
}

/**
 * @brief Probe the hardware clear-key protection without exposing chip keys publicly.
 */
DRV_Status SPINLOCK_testClearProbe(SPINLOCK_TestClearScope scope, uint32_t authorized)
{
    uint32_t key;

    if (scope == SPINLOCK_TEST_CLEAR_BATCH)
    {
        key = (authorized != 0U) ? SL_BATCH_LOCK_CLR_KEY : SPINLOCK_TEST_INVALID_CLEAR_KEY;
        WRITE_REG(SPINLOCK->SL_BATCH_LOCK_CLR, key);
    }
    else if (scope == SPINLOCK_TEST_CLEAR_GLOBAL)
    {
        key = (authorized != 0U) ? SL_GLB_LOCK_CLR_KEY : SPINLOCK_TEST_INVALID_CLEAR_KEY;
        WRITE_REG(SPINLOCK->SL_GLOBAL_LOCK_CLR, key);
    }
    else
    {
        return DRV_PARAM_ERR;
    }

    return DRV_OK;
}

DRV_Status SPINLOCK_testPeerReady(uint32_t *pReady)
{
    volatile SPINLOCK_TestPeerMailbox *mailbox = SPINLOCK_TEST_PEER_MAILBOX;

    if (pReady == NULL)
    {
        return DRV_PARAM_ERR;
    }

    __DMB();
    *pReady = ((mailbox->magic == SPINLOCK_TEST_PEER_MAILBOX_MAGIC) &&
               (mailbox->peerReady == SPINLOCK_TEST_PEER_READY))
                  ? 1U
                  : 0U;

    return DRV_OK;
}

/* 把内嵌的Core1镜像搬到其ITCM全局别名并拉起从核，直到共享邮箱报告就绪。 */
DRV_Status SPINLOCK_testBootPeer(const uint8_t *image, uint32_t image_size)
{
    uint32_t ready = 0U;
    uint32_t timeout;

    if (image == NULL)
    {
        return DRV_PARAM_ERR;
    }

    /* 幂等：从核已经就绪时不再重复搬运与复位。 */
    if ((SPINLOCK_testPeerReady(&ready) == DRV_OK) && (ready != 0U))
    {
        return DRV_OK;
    }

    /* 先挂起Core1，避免搬运镜像时从核取指。 */
    SYSC_unlockCriticalRegs();
    SET_BIT(SYSC->CPU_WAIT, SYSC_CPU_WAIT_SYSC_CPU1_WAIT_Msk);

    /* 正式SDK未暴露ITCM别名常量，这里按同一映射写入Core1 ITCM。 */
    memcpy((void *)ICTM_CORE1_TO_DMA_OFFSET, image, image_size);

    DUALCORE_startCore1(0U);

    /* 等待从核写入就绪邮箱；超时由调用方按DRV_TIMEOUT处理。 */
    for (timeout = 0U; timeout < SPINLOCK_TEST_PEER_BOOT_POLL_LIMIT; ++timeout)
    {
        if ((SPINLOCK_testPeerReady(&ready) == DRV_OK) && (ready != 0U))
        {
            return DRV_OK;
        }
    }

    return DRV_TIMEOUT;
}

DRV_Status SPINLOCK_testGetPeerMasterId(uint32_t *pMasterId){
    uint32_t ready;

    if (pMasterId == NULL)
    {
        return DRV_PARAM_ERR;
    }

    if ((SPINLOCK_testPeerReady(&ready) != DRV_OK) || (ready == 0U))
    {
        return DRV_ERROR;
    }

    __DMB();
    *pMasterId = SPINLOCK_TEST_PEER_MAILBOX->peerMasterId;

    return DRV_OK;
}

DRV_Status SPINLOCK_testPeerJobStart(const SPINLOCK_TestPeerJobConfig *pConfig)
{
    volatile SPINLOCK_TestPeerMailbox *mailbox = SPINLOCK_TEST_PEER_MAILBOX;
    uint32_t ready;

    if ((pConfig == NULL) || (pConfig->jobType > SPINLOCK_TEST_PEER_JOB_STRESS) ||
        (!IS_SPINLOCK_INIT_MODE(pConfig->mode)) || (!IS_SPINLOCK_RESID(pConfig->resourceId)) ||
        (!IS_SPINLOCK_PROCESSID(pConfig->processId)))
    {
        return DRV_PARAM_ERR;
    }

    if ((SPINLOCK_testPeerReady(&ready) != DRV_OK) || (ready == 0U))
    {
        return DRV_ERROR;
    }

    __DMB();

    if (SPINLOCK_testPeerIsActive(mailbox->jobState) != 0U)
    {
        return DRV_BUSY;
    }

    mailbox->jobType = pConfig->jobType;
    mailbox->mode = pConfig->mode;
    mailbox->resourceId = pConfig->resourceId;
    mailbox->processId = pConfig->processId;
    mailbox->loopCount = pConfig->loopCount;
    mailbox->control = SPINLOCK_TEST_PEER_CONTROL_NONE;
    mailbox->result = SPINLOCK_TEST_PEER_RESULT_NONE;
    mailbox->enterCount = 0U;
    mailbox->completedCount = 0U;
    mailbox->jobState = SPINLOCK_TEST_PEER_JOB_STARTED;
    __DMB();

    if (mailbox->commandSequence == UINT32_MAX)
    {
        mailbox->commandSequence = SPINLOCK_TEST_PEER_COMMAND_FIRST_SEQUENCE;
    }
    else
    {
        ++mailbox->commandSequence;
    }

    __DSB();

    return DRV_OK;
}

DRV_Status SPINLOCK_testPeerJobGetSnapshot(SPINLOCK_TestPeerJobSnapshot *pSnapshot)
{
    volatile SPINLOCK_TestPeerMailbox *mailbox = SPINLOCK_TEST_PEER_MAILBOX;
    uint32_t ready;

    if (pSnapshot == NULL)
    {
        return DRV_PARAM_ERR;
    }

    if ((SPINLOCK_testPeerReady(&ready) != DRV_OK) || (ready == 0U))
    {
        return DRV_ERROR;
    }

    __DMB();
    pSnapshot->state = mailbox->jobState;
    pSnapshot->result = mailbox->result;
    pSnapshot->enterCount = mailbox->enterCount;
    pSnapshot->completedCount = mailbox->completedCount;
    pSnapshot->masterId = mailbox->peerMasterId;

    return DRV_OK;
}

DRV_Status SPINLOCK_testPeerJobControl(SPINLOCK_TestPeerControl control)
{
    volatile SPINLOCK_TestPeerMailbox *mailbox = SPINLOCK_TEST_PEER_MAILBOX;
    uint32_t ready;

    if ((control != SPINLOCK_TEST_PEER_CONTROL_RELEASE) &&
        (control != SPINLOCK_TEST_PEER_CONTROL_ABORT))
    {
        return DRV_PARAM_ERR;
    }

    if ((SPINLOCK_testPeerReady(&ready) != DRV_OK) || (ready == 0U))
    {
        return DRV_ERROR;
    }

    __DMB();

    if (SPINLOCK_testPeerIsActive(mailbox->jobState) == 0U)
    {
        return DRV_ERROR;
    }

    mailbox->control = (uint32_t)control;
    __DSB();

    return DRV_OK;
}

DRV_Status SPINLOCK_testSharedStressReset(void)
{
    volatile SPINLOCK_TestPeerMailbox *mailbox = SPINLOCK_TEST_PEER_MAILBOX;
    uint32_t ready;

    if ((SPINLOCK_testPeerReady(&ready) != DRV_OK) || (ready == 0U) ||
        (SPINLOCK_testPeerIsActive(mailbox->jobState) != 0U))
    {
        return DRV_ERROR;
    }

    mailbox->sharedCounter = 0U;
    mailbox->criticalOwner = SPINLOCK_TEST_PEER_ACTIVE_OWNER_NONE;
    mailbox->violationCount = 0U;
    __DSB();

    return DRV_OK;
}

DRV_Status SPINLOCK_testLocalStressRun(uint32_t resourceId, uint32_t loopCount,
                                       uint32_t *pCompletedCount)
{
    volatile SPINLOCK_TestPeerMailbox *mailbox = SPINLOCK_TEST_PEER_MAILBOX;
    uint32_t masterId = DUALCORE_getCurrentCoreId();
    uint32_t completed = 0U;

    if ((!IS_SPINLOCK_RESID(resourceId)) || (loopCount == 0U) || (pCompletedCount == NULL))
    {
        return DRV_PARAM_ERR;
    }

    while (completed < loopCount)
    {
        SPINLOCK_fastAcquire(resourceId);
        SPINLOCK_testCriticalCounterIncrement(mailbox, masterId);
        SPINLOCK_fastRelease(resourceId);
        ++completed;
    }

    *pCompletedCount = completed;

    return DRV_OK;
}

DRV_Status SPINLOCK_testSharedStressGetSnapshot(SPINLOCK_TestSharedSnapshot *pSnapshot)
{
    if (pSnapshot == NULL)
    {
        return DRV_PARAM_ERR;
    }

    __DMB();
    pSnapshot->sharedCounter = SPINLOCK_TEST_PEER_MAILBOX->sharedCounter;
    pSnapshot->violationCount = SPINLOCK_TEST_PEER_MAILBOX->violationCount;

    return DRV_OK;
}

static void SPINLOCK_testPeerWaitForControl(volatile SPINLOCK_TestPeerMailbox *pMailbox,
                                            uint32_t mode, uint32_t resourceId, uint32_t processId)
{
    while ((pMailbox->control != SPINLOCK_TEST_PEER_CONTROL_RELEASE) &&
           (pMailbox->control != SPINLOCK_TEST_PEER_CONTROL_ABORT))
    {
        ++pMailbox->heartbeat;
        __DMB();
    }

    SPINLOCK_testReleaseByMode(mode, resourceId, processId);
    pMailbox->result = (pMailbox->control == SPINLOCK_TEST_PEER_CONTROL_ABORT)
                           ? SPINLOCK_TEST_PEER_RESULT_ABORTED
                           : SPINLOCK_TEST_PEER_RESULT_RELEASED;
    pMailbox->jobState = (pMailbox->control == SPINLOCK_TEST_PEER_CONTROL_ABORT)
                             ? SPINLOCK_TEST_PEER_JOB_ABORTED
                             : SPINLOCK_TEST_PEER_JOB_DONE;
    __DSB();
}

static void SPINLOCK_testPeerExecuteAcquire(volatile SPINLOCK_TestPeerMailbox *pMailbox,
                                            uint32_t waitUntilAcquired)
{
    DRV_Status status;

    pMailbox->jobState =
        (waitUntilAcquired != 0U) ? SPINLOCK_TEST_PEER_JOB_WAITING : SPINLOCK_TEST_PEER_JOB_STARTED;
    __DMB();

    do
    {
        status =
            SPINLOCK_testAcquireByMode(pMailbox->mode, pMailbox->resourceId, pMailbox->processId);

        if ((status != DRV_OK) && (pMailbox->control == SPINLOCK_TEST_PEER_CONTROL_ABORT))
        {
            pMailbox->result = SPINLOCK_TEST_PEER_RESULT_ABORTED;
            pMailbox->jobState = SPINLOCK_TEST_PEER_JOB_ABORTED;
            __DSB();

            return;
        }
    } while ((status != DRV_OK) && (waitUntilAcquired != 0U));

    if (status != DRV_OK)
    {
        pMailbox->result = SPINLOCK_TEST_PEER_RESULT_BUSY;
        pMailbox->jobState = SPINLOCK_TEST_PEER_JOB_DONE;
        __DSB();

        return;
    }

    ++pMailbox->enterCount;
    pMailbox->result = SPINLOCK_TEST_PEER_RESULT_ACQUIRED;
    pMailbox->jobState = SPINLOCK_TEST_PEER_JOB_HOLDING;
    __DSB();
    SPINLOCK_testPeerWaitForControl(pMailbox, pMailbox->mode, pMailbox->resourceId,
                                    pMailbox->processId);
}

static void SPINLOCK_testPeerExecuteStress(volatile SPINLOCK_TestPeerMailbox *pMailbox)
{
    uint32_t masterId = DUALCORE_getCurrentCoreId();

    pMailbox->jobState = SPINLOCK_TEST_PEER_JOB_STARTED;
    __DMB();

    while (pMailbox->completedCount < pMailbox->loopCount)
    {
        if (pMailbox->control == SPINLOCK_TEST_PEER_CONTROL_ABORT)
        {
            pMailbox->result = SPINLOCK_TEST_PEER_RESULT_ABORTED;
            pMailbox->jobState = SPINLOCK_TEST_PEER_JOB_ABORTED;
            __DSB();

            return;
        }

        SPINLOCK_fastAcquire(pMailbox->resourceId);
        SPINLOCK_testCriticalCounterIncrement(pMailbox, masterId);
        SPINLOCK_fastRelease(pMailbox->resourceId);
        ++pMailbox->completedCount;
    }

    pMailbox->result = SPINLOCK_TEST_PEER_RESULT_COMPLETED;
    pMailbox->jobState = SPINLOCK_TEST_PEER_JOB_DONE;
    __DSB();
}

void SPINLOCK_testPeerRunForever(void)
{
    volatile SPINLOCK_TestPeerMailbox *mailbox = SPINLOCK_TEST_PEER_MAILBOX;
    uint32_t handledSequence;
    volatile uint32_t delayCount;

    mailbox->peerReady = 0U;
    mailbox->coreIndex = DUALCORE_getCurrentCoreId();
    mailbox->heartbeat = 0U;
    mailbox->commandSequence = 0U;
    mailbox->acknowledgeSequence = 0U;
    mailbox->jobState = SPINLOCK_TEST_PEER_JOB_IDLE;
    mailbox->peerMasterId = DUALCORE_getCurrentCoreId();
    mailbox->magic = SPINLOCK_TEST_PEER_MAILBOX_MAGIC;
    __DMB();
    mailbox->peerReady = SPINLOCK_TEST_PEER_READY;
    __DSB();
    handledSequence = mailbox->commandSequence;

    for (;;)
    {
        if (mailbox->commandSequence != handledSequence)
        {
            handledSequence = mailbox->commandSequence;
            mailbox->acknowledgeSequence = handledSequence;
            mailbox->control = SPINLOCK_TEST_PEER_CONTROL_NONE;
            __DMB();

            switch (mailbox->jobType)
            {
                case SPINLOCK_TEST_PEER_JOB_TRY_HOLD:
                {
                    SPINLOCK_testPeerExecuteAcquire(mailbox, 0U);
                    break;
                }

                case SPINLOCK_TEST_PEER_JOB_BLOCKING_HOLD:
                case SPINLOCK_TEST_PEER_JOB_HOLD:
                {
                    SPINLOCK_testPeerExecuteAcquire(mailbox, 1U);
                    break;
                }

                case SPINLOCK_TEST_PEER_JOB_RELEASE_ONCE:
                {
                    SPINLOCK_testReleaseByMode(mailbox->mode, mailbox->resourceId,
                                               mailbox->processId);
                    mailbox->result = SPINLOCK_TEST_PEER_RESULT_RELEASED;
                    mailbox->jobState = SPINLOCK_TEST_PEER_JOB_DONE;
                    __DSB();
                    break;
                }

                case SPINLOCK_TEST_PEER_JOB_STRESS:
                {
                    SPINLOCK_testPeerExecuteStress(mailbox);
                    break;
                }

                default:
                {
                    mailbox->result = SPINLOCK_TEST_PEER_RESULT_ERROR;
                    mailbox->jobState = SPINLOCK_TEST_PEER_JOB_ERROR;
                    __DSB();
                    break;
                }
            }
        }

        for (delayCount = 0U; delayCount < SPINLOCK_TEST_PEER_HEARTBEAT_DELAY_CYCLES; ++delayCount)
        {
            __NOP();
        }

        ++mailbox->heartbeat;
        __DMB();
    }
}

/********************* TEST DRIVER EXTENSION END *********************/

#endif

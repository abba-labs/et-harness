#ifndef ET_MANUAL_TEST_INTERNAL_H
#define ET_MANUAL_TEST_INTERNAL_H

#include <stdint.h>

void et_manual_log_text(const char *text);
void et_manual_log_u32(const char *name, uint32_t value);
void et_manual_log_result(const char *case_id, int result);

int et_manual_uart_p1_008_framing_error_detection(void);
int et_manual_uart_p1_012_busy_detect_irq(void);
int et_manual_uart_p3_009_direct_fifo_access(void);
int et_manual_crc_p1_011_fifo_threshold(void);
int et_manual_crc_p1_012_fifo_overflow_recovery(void);
int et_manual_aes_p1_009_output_conflict(void);
int et_manual_cordic_p1_003_scale7_arctan_precision(void);
int et_manual_cordic_p2_001_dma_mode_equivalence(void);
int et_manual_crg_register_reset_matrix(void);
int et_manual_fmac_p1_006_float_overflow_clear(void);
int et_manual_fmac_p1_010_negative_status_clear(void);
int et_manual_stimer_p1_001_prescaler_ratio(void);
int et_manual_stimer_p2_003_debugger_halt_behavior(void);
int et_manual_wdg_p1_004_module_reset_and_recovery(void);
int et_manual_wdg_p2_001_clock_divider_rate(void);
int et_manual_dualcore_smoke(void);

#endif

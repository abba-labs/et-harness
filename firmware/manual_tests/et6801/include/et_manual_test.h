#ifndef ET_MANUAL_TEST_H
#define ET_MANUAL_TEST_H

/**
 * @file et_manual_test.h
 * @brief Entry point for the ET6801 standalone manual diagnostic image.
 */

/**
 * @brief Initialize the diagnostic environment, run every selected case and print results.
 *
 * @return 0 when every manual diagnostic passes.
 * @return 1 when one or more diagnostics expose a mismatch or unsupported hardware fact.
 */
int et_manual_test_run(void);

#endif

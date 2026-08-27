#ifndef ET_WRAP_STATUS_H
#define ET_WRAP_STATUS_H

/** @file et_wrap_status.h @brief Stable status vocabulary shared by all Wraps. */

typedef enum
{
    ET_WRAP_STATUS_OK = 0,                /**< Operation completed. */
    ET_WRAP_STATUS_INVALID_ARGUMENT = -1, /**< Invalid ID, value, size or pointer. */
    ET_WRAP_STATUS_NOT_SUPPORTED = -2,    /**< Feature is absent on selected chip. */
    ET_WRAP_STATUS_BUSY = -3,             /**< Hardware cannot accept operation now. */
    ET_WRAP_STATUS_IO_ERROR = -4,         /**< Driver or hardware operation failed. */
    ET_WRAP_STATUS_NO_RESOURCE = -5,      /**< Bounded static capacity is exhausted. */
    ET_WRAP_STATUS_TIMEOUT = -6,          /**< Bounded operation did not complete. */
    ET_WRAP_STATUS_STATE_ERROR = -7       /**< Lifecycle precondition was not met. */
} et_wrap_status_t;

#endif

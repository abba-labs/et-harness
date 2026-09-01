#ifndef ET_RING_BUFFER_H
#define ET_RING_BUFFER_H

/**
 * @file et_ring_buffer.h
 * @brief Allocation-free single-producer/single-consumer byte ring.
 *
 * One slot remains unused so read_index == write_index always means empty.
 */

#include <stddef.h>
#include <stdint.h>

typedef struct
{
    uint8_t *storage;            /**< Caller-owned byte storage. */
    size_t capacity;             /**< Physical storage size including spare slot. */
    volatile size_t read_index;  /**< Next byte consumed by the reader. */
    volatile size_t write_index; /**< Next slot produced by the writer. */
} et_ring_buffer_t;

/** Initialize a ring over caller-owned storage; capacity must exceed one. */
int et_ring_buffer_init(et_ring_buffer_t *buffer, uint8_t *storage, size_t capacity);
/** Discard all buffered bytes without altering storage. */
void et_ring_buffer_clear(et_ring_buffer_t *buffer);
/** Return the current readable byte count. */
size_t et_ring_buffer_size(const et_ring_buffer_t *buffer);
/** Return the current writable byte count. */
size_t et_ring_buffer_space(const et_ring_buffer_t *buffer);
/** Write up to length bytes and return the number accepted. */
size_t et_ring_buffer_write(et_ring_buffer_t *buffer, const uint8_t *data, size_t length);
/** Read and consume up to capacity bytes. */
size_t et_ring_buffer_read(et_ring_buffer_t *buffer, uint8_t *data, size_t capacity);
/** Copy up to capacity bytes without advancing read_index. */
size_t et_ring_buffer_peek(const et_ring_buffer_t *buffer, uint8_t *data, size_t capacity);
/** Consume up to length bytes without copying them. */
size_t et_ring_buffer_discard(et_ring_buffer_t *buffer, size_t length);

#endif

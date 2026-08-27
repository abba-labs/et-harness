#include "et_ring_buffer.h"

/**
 * @file et_ring_buffer.c
 * @brief Bounded byte ring used between UART interrupt and protocol context.
 */

#define ET_RING_BUFFER_MIN_CAPACITY 2u

/**
 * @brief Bind caller-owned storage and reset a bounded byte ring to empty.
 *
 * @param[out] buffer Ring-buffer state to initialize.
 * @param[in,out] storage Caller-owned byte storage retained by the ring.
 * @param[in] capacity Number of bytes available in storage.
 *
 * @note The ring never allocates memory and reserves one storage slot to distinguish full from
 *       empty. Initialization does not read or write any hardware state.
 *
 * @return 0 when the storage contract is valid.
 * @return -1 when required pointers are NULL or capacity is too small for the ring invariant.
 */
int et_ring_buffer_init(et_ring_buffer_t *buffer, uint8_t *storage, size_t capacity)
{
    if ((buffer == NULL) || (storage == NULL) || (capacity < ET_RING_BUFFER_MIN_CAPACITY))
    {
        return -1;
    }

    buffer->storage = storage;
    buffer->capacity = capacity;
    buffer->read_index = 0u;
    buffer->write_index = 0u;

    return 0;
}

/**
 * @brief Discard every buffered byte while retaining the caller-owned storage binding.
 *
 * @param[in,out] buffer Ring buffer to reset to empty.
 *
 * @note Only ring indices are reset; storage contents are intentionally left unchanged and no
 *       hardware or allocator ownership is involved.
 */
void et_ring_buffer_clear(et_ring_buffer_t *buffer)
{
    if (buffer != NULL)
    {
        buffer->read_index = 0u;
        buffer->write_index = 0u;
    }
}

/**
 * @brief Return the number of bytes currently readable from one coherent index snapshot.
 *
 * @param[in] buffer Ring buffer whose readable occupancy is requested.
 *
 * @note The function reads indices only and does not consume data. The caller is responsible for
 *       the producer/consumer synchronization model used around index updates.
 *
 * @return Number of readable bytes, or zero when buffer is NULL.
 */
size_t et_ring_buffer_size(const et_ring_buffer_t *buffer)
{
    size_t read_index;
    size_t write_index;

    if (buffer == NULL)
    {
        return 0u;
    }

    read_index = buffer->read_index;
    write_index = buffer->write_index;

    if (write_index >= read_index)
    {
        return write_index - read_index;
    }

    return buffer->capacity - read_index + write_index;
}

/**
 * @brief Return the number of bytes that can be written without overwriting unread data.
 *
 * @param[in] buffer Ring buffer whose writable space is requested.
 *
 * @note One slot is always reserved so equal read/write indices represent only the empty state.
 *       This query does not change either ring index.
 *
 * @return Writable byte count, or zero when buffer is invalid.
 */
size_t et_ring_buffer_space(const et_ring_buffer_t *buffer)
{
    size_t size;

    if ((buffer == NULL) || (buffer->capacity < ET_RING_BUFFER_MIN_CAPACITY))
    {
        return 0u;
    }

    size = et_ring_buffer_size(buffer);

    /* Reserve one slot so equal indices always have one unambiguous meaning. */
    return buffer->capacity - size - 1u;
}

/**
 * @brief Append as many caller-supplied bytes as fit without overwriting unread data.
 *
 * @param[in,out] buffer Destination ring buffer.
 * @param[in] data Source bytes to append.
 * @param[in] length Number of source bytes requested for writing.
 *
 * @note The write is intentionally partial when the ring becomes full. Only write_index advances;
 *       unread bytes and read_index remain untouched.
 *
 * @return Number of bytes accepted by the ring, or zero when required pointers are invalid.
 */
size_t et_ring_buffer_write(et_ring_buffer_t *buffer, const uint8_t *data, size_t length)
{
    size_t written = 0u;
    size_t next;

    if ((buffer == NULL) || (data == NULL))
    {
        return 0u;
    }

    while (written < length)
    {
        next = (buffer->write_index + 1u) % buffer->capacity;

        if (next == buffer->read_index)
        {
            break;
        }

        buffer->storage[buffer->write_index] = data[written];
        buffer->write_index = next;
        ++written;
    }

    return written;
}

/**
 * @brief Consume buffered bytes in FIFO order into caller-owned storage.
 *
 * @param[in,out] buffer Source ring buffer whose read index advances.
 * @param[out] data Destination buffer for consumed bytes.
 * @param[in] capacity Maximum number of bytes that may be copied.
 *
 * @note Reading stops at either capacity or the current write index. Consumed bytes are not erased
 *       from backing storage; advancing read_index transfers ownership to the producer.
 *
 * @return Number of bytes consumed, or zero when required pointers are invalid or the ring is empty.
 */
size_t et_ring_buffer_read(et_ring_buffer_t *buffer, uint8_t *data, size_t capacity)
{
    size_t read = 0u;

    if ((buffer == NULL) || (data == NULL))
    {
        return 0u;
    }

    while ((read < capacity) && (buffer->read_index != buffer->write_index))
    {
        data[read] = buffer->storage[buffer->read_index];
        buffer->read_index = (buffer->read_index + 1u) % buffer->capacity;
        ++read;
    }

    return read;
}

/**
 * @brief Copy buffered bytes in FIFO order without consuming them.
 *
 * @param[in] buffer Source ring buffer.
 * @param[out] data Destination buffer for copied bytes.
 * @param[in] capacity Maximum number of bytes that may be copied.
 *
 * @note The function snapshots write_index and walks a local read cursor; the ring's read_index is
 *       never advanced, which lets a caller commit only bytes later accepted by hardware.
 *
 * @return Number of bytes copied, or zero when required pointers are invalid or the ring is empty.
 */
size_t et_ring_buffer_peek(const et_ring_buffer_t *buffer, uint8_t *data, size_t capacity)
{
    size_t copied = 0u;
    size_t index;
    size_t write_index;

    if ((buffer == NULL) || (data == NULL))
    {
        return 0u;
    }

    index = buffer->read_index;
    write_index = buffer->write_index;

    while ((copied < capacity) && (index != write_index))
    {
        data[copied++] = buffer->storage[index];
        index = (index + 1u) % buffer->capacity;
    }

    return copied;
}

/**
 * @brief Consume up to a requested number of buffered bytes without copying them.
 *
 * @param[in,out] buffer Ring buffer whose read index advances.
 * @param[in] length Maximum number of bytes to discard.
 *
 * @note The operation never advances beyond the current write index and does not modify backing
 *       storage contents.
 *
 * @return Number of bytes actually discarded, or zero when buffer is NULL or empty.
 */
size_t et_ring_buffer_discard(et_ring_buffer_t *buffer, size_t length)
{
    size_t discarded = 0u;

    if (buffer == NULL)
    {
        return 0u;
    }

    while ((discarded < length) && (buffer->read_index != buffer->write_index))
    {
        buffer->read_index = (buffer->read_index + 1u) % buffer->capacity;
        ++discarded;
    }

    return discarded;
}

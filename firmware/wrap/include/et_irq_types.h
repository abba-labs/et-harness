#ifndef ET_IRQ_TYPES_H
#define ET_IRQ_TYPES_H

/** @file et_irq_types.h @brief Chip-independent IRQ route vocabulary. */

#include <stdint.h>

/** Physical vector-line identity used only below Service protocol boundary. */
typedef uint16_t et_irq_line_t;

/** Physical line plus IP-local event facts delivered to a Service callback. */
typedef struct
{
    et_irq_line_t irq_line; /**< Chip-specific physical vector line. */
    uint16_t reserved;      /**< Must be zero. */
    uint32_t route_events;  /**< Stable IP-local event mask for this route. */
} et_irq_route_t;

#endif

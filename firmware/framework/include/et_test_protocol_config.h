#ifndef ET_TEST_PROTOCOL_CONFIG_H
#define ET_TEST_PROTOCOL_CONFIG_H

/*
 * Protocol capacities are overridable build-time policy, not chip facts.
 * Physical UART and pin choices are validated separately.
 */
#ifndef ET_TEST_PROTOCOL_MAX_PAYLOAD
#define ET_TEST_PROTOCOL_MAX_PAYLOAD 4096u
#endif

#ifndef ET_TEST_PROTOCOL_RX_CHUNK_SIZE
#define ET_TEST_PROTOCOL_RX_CHUNK_SIZE 64u
#endif

#ifndef ET_FRAMEWORK_MAX_IRQ_BINDINGS
#define ET_FRAMEWORK_MAX_IRQ_BINDINGS 64u
#endif

#ifndef ET_FRAMEWORK_MAX_DMA_BINDINGS
#define ET_FRAMEWORK_MAX_DMA_BINDINGS 32u
#endif

#ifndef ET_FRAMEWORK_MAX_SERVICES
#define ET_FRAMEWORK_MAX_SERVICES 64u
#endif

#if (ET_TEST_PROTOCOL_MAX_PAYLOAD < 32u)
#error "ET_TEST_PROTOCOL_MAX_PAYLOAD is too small for common responses"
#endif

#if (ET_TEST_PROTOCOL_MAX_PAYLOAD > 65535u)
#error "ET_TEST_PROTOCOL_MAX_PAYLOAD must fit the ET-Frame uint16 length"
#endif

#if (ET_TEST_PROTOCOL_RX_CHUNK_SIZE == 0u)
#error "ET_TEST_PROTOCOL_RX_CHUNK_SIZE must be nonzero"
#endif

#endif

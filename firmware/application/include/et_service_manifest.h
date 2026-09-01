#ifndef ET_SERVICE_MANIFEST_H
#define ET_SERVICE_MANIFEST_H

/**
 * @file et_service_manifest.h
 * @brief Application-owned manifest of board-selected IP Service groups.
 */

#include <stddef.h>

#include "et_service_factory.h"

/** Prepare board-selected Service instances before Runtime startup. */
int et_service_manifest_prepare(void);

/**
 * Return the immutable Service group table composed for this firmware image.
 * The returned table and all referenced storage have static lifetime.
 */
const et_service_group_t *et_service_manifest_get(size_t *group_count);

#endif

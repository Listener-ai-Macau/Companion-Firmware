#ifndef COMP_REQ_607_CANONICAL_RUNNER_H
#define COMP_REQ_607_CANONICAL_RUNNER_H

#include <stdbool.h>
#include <stdint.h>

/* Default-off lower-only replay of the already generated canonical frame
 * stream. It is intentionally separate from the production display queue. */
void comp_req_607_canonical_runner_init(void);
bool comp_req_607_canonical_runner_service(void);
bool comp_req_607_canonical_runner_is_complete(void);
bool comp_req_607_canonical_runner_faulted(void);

#endif

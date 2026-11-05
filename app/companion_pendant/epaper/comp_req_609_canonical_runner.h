#ifndef COMP_REQ_609_CANONICAL_RUNNER_H
#define COMP_REQ_609_CANONICAL_RUNNER_H

#include <stdbool.h>

void comp_req_609_canonical_runner_init(void);
bool comp_req_609_canonical_runner_service(void);
bool comp_req_609_canonical_runner_is_complete(void);
bool comp_req_609_canonical_runner_faulted(void);

#endif

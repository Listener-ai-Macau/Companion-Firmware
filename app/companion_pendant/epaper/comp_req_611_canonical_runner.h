#ifndef COMP_REQ_611_CANONICAL_RUNNER_H
#define COMP_REQ_611_CANONICAL_RUNNER_H

#include <stdbool.h>
#include <stdint.h>

void comp_req_611_canonical_runner_init(void);
bool comp_req_611_canonical_runner_service(void);
bool comp_req_611_canonical_runner_is_complete(void);
bool comp_req_611_canonical_runner_faulted(void);
void comp_req_611_canonical_runner_request_stop(void);
bool comp_req_611_canonical_runner_accept_host_byte(uint8_t byte);

#endif

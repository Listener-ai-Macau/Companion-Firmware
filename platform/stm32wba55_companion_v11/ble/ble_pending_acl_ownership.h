#ifndef COMP_V11_BLE_PENDING_ACL_OWNERSHIP_H
#define COMP_V11_BLE_PENDING_ACL_OWNERSHIP_H
#include <stdbool.h>
#include <stdint.h>

/* Compatibility for the pinned ST host library, not a pool scan or an LL
 * completion shim. LECTRL_Process removes a host ACL before submitting it.
 * A genuine UNKNOWN_CONNECTION_ID (2) leaves that host ACL unowned, even
 * though the physical LL descriptors have their separate cleanup path.
 *
 * Capture only the explicit Remove argument inside this Process frame.
 * Release only after SendAclDataToLL has returned: at the next Remove, or
 * after the real Process returns. This also keeps the host buffer alive
 * through cleanup after a partially accepted fragmented PDU. Do not inspect
 * or free the already-consumed physical LL packet. Other statuses and the
 * immediate-send path retain their original contracts.
 *
 * The build must pin the host archive and prove both call redirections.
 * SDK updates require requalification, not silently guessed internal ABI.
 */
extern void __real_LECTRL_Process(void);
extern void __real_ACL_List_Remove(void *list,void *entry);
extern void ACL_Release(void *entry);
static struct {
    void *entry;
    uint32_t released;
    bool processing;
    bool rejected_unknown_connection;
} pending_acl_owner;
_Static_assert(sizeof(pending_acl_owner)==12u,"bounded pending ownership state");

static void pending_acl_settle(void)
{
    if(pending_acl_owner.entry && pending_acl_owner.rejected_unknown_connection) {
        ACL_Release(pending_acl_owner.entry);
        if(pending_acl_owner.released!=UINT32_MAX)++pending_acl_owner.released;
    }
    pending_acl_owner.entry=0;
    pending_acl_owner.rejected_unknown_connection=false;
}

void __wrap_ACL_List_Remove(void *list,void *entry)
{
    /* Only the pinned pending-loop call, not a nested completion/list use.
     * The final ELF audit checks this exact return offset and redirection. */
    const uintptr_t caller=(uintptr_t)__builtin_return_address(0)&~(uintptr_t)1u;
    const uintptr_t process=(uintptr_t)&__real_LECTRL_Process&~(uintptr_t)1u;
    const bool pending=pending_acl_owner.processing && caller==process+0x52u;
    if(pending)pending_acl_settle();
    __real_ACL_List_Remove(list,entry);
    if(pending)pending_acl_owner.entry=entry;
}

void __wrap_LECTRL_Process(void)
{
    pending_acl_owner.processing=true;
    __real_LECTRL_Process();
    pending_acl_owner.processing=false;
    pending_acl_settle();
}

static void comp_v11_ble_pending_acl_send_result(uint8_t status)
{
    if(status==2u && pending_acl_owner.processing && pending_acl_owner.entry)
        pending_acl_owner.rejected_unknown_connection=true;
}

uint32_t comp_v11_ble_pending_acl_released(void)
{
    return pending_acl_owner.released;
}
#endif

#ifndef OTA_TEST_SVC_CTL_H
#define OTA_TEST_SVC_CTL_H
typedef enum {SVCCTL_EvtNotAck,SVCCTL_EvtAckFlowEnable,SVCCTL_EvtAckFlowDisable} SVCCTL_EvtAckStatus_t;
void SVCCTL_RegisterSvcHandler(SVCCTL_EvtAckStatus_t (*handler)(void *));
#endif

void SVCCTL_ResumeUserEventFlow(void);

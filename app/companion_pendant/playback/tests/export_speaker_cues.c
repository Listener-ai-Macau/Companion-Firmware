/* Audition the actual firmware PCM generator; no OS playback or hardware claim. */
#include "speaker_playback.h"
#include <stdio.h>
static FILE *output;
static bool amplifier(void *context,bool enabled) { (void)context; (void)enabled; return true; }
static void activity(void *context,bool active) { (void)context; (void)active; }
static bool submit(void *context,const int16_t *stereo,size_t frames)
{
    (void)context;
    for (size_t i=0;i<frames;++i) {
        uint16_t sample=(uint16_t)stereo[i*2];
        if (fputc((int)(sample&255u),output)==EOF || fputc((int)(sample>>8),output)==EOF) return false;
    }
    return true;
}
int main(void)
{
    const char *names[]={"confirm.pcm","record-start.pcm","record-stop.pcm","error.pcm",
        "pet-greeting.pcm","pet-content.pcm","pet-playful.pcm","pet-shy.pcm"};
    for (unsigned i=0;i<sizeof(names)/sizeof(names[0]);++i) {
        comp_speaker_t speaker; comp_speaker_config_t config={amplifier,submit,activity,NULL};
        if (fopen_s(&output,names[i],"wb")!=0) return 1;
        comp_speaker_init(&speaker,&config);
        if (comp_speaker_set_pet_voice(&speaker,true)!=COMP_SPEAKER_OK) return 4;
        if (comp_speaker_set_volume(&speaker,25)!=COMP_SPEAKER_OK ||
            comp_speaker_play_cue(&speaker,(comp_speaker_cue_t)i)!=COMP_SPEAKER_OK) return 2;
        unsigned cycles=0;
        while (comp_speaker_active(&speaker) && ++cycles<2000u) {
            (void)comp_speaker_service(&speaker);
            if (speaker.tx_pending) comp_speaker_tx_complete(&speaker,true);
        }
        if (fclose(output)!=0 || cycles>=2000u || speaker.last_error!=COMP_SPEAKER_OK) return 3;
    }
    return 0;
}

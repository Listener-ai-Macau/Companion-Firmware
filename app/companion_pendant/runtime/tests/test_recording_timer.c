#include <stdio.h>
#include <string.h>
#include "../companion_renderer.c"
#include "../../recording/wba_recording_level.h"
#define CHECK(x) do { if(!(x)) { printf("FAIL %d: %s\n",__LINE__,#x); return 1; } } while(0)
static void draw(comp_runtime_frame_t *f, unsigned t, uint8_t *out) { memset(out,255,5000); f->recording_elapsed_seconds=t; if(!status(f,out)) { puts("FAIL status"); } }
int main(void) {
  comp_runtime_frame_t f={0}; uint8_t a[5000],b[5000],expected[5000]; comp_screen_framebuffer_t fb;
  f.recording=DENZIC_AUDIO_RECORDING_STATE_RECORDING;
  draw(&f,5999,a);draw(&f,6000,b);CHECK(memcmp(a,b,16*25)!=0);
  draw(&f,7200,a);draw(&f,7201,b);CHECK(memcmp(a,b,16*25)!=0);
  memset(expected,255,5000);CHECK(comp_screen_framebuffer_init(&fb,expected,5000,200,200));comp_screen_framebuffer_draw_text(&fb,94,5,"02:00:00",1,true);
  for(unsigned y=5;y<12;y++)for(unsigned x=94;x<142;x++) CHECK((expected[y*25+x/8]&(0x80u>>(x%8)))==(a[y*25+x/8]&(0x80u>>(x%8))));
  CHECK(comp_wba_recording_level_bars(0)==1 && comp_wba_recording_level_bars(15)==1);
  CHECK(comp_wba_recording_level_bars(16)==2 && comp_wba_recording_level_bars(64)==3);
  CHECK(comp_wba_recording_level_bars(256)==4 && comp_wba_recording_level_bars(1024)==5);
  f.recording_input_level=0;draw(&f,7200,a);
  for(unsigned level=1;level<=5;level++) {
    f.recording_input_level=(uint8_t)level;draw(&f,7200,b);CHECK(memcmp(a,b,16*25)!=0);
    for(unsigned y=0;y<16;y++)for(unsigned x=0;x<200;x++) if(x<44||x>73||y<4||y>12)
      CHECK((a[y*25+x/8]&(0x80u>>(x%8)))==(b[y*25+x/8]&(0x80u>>(x%8))));
  }
  f.recording_paused=true;f.recording_input_level=5;draw(&f,7200,a);
  f.recording_input_level=0;draw(&f,7200,b);CHECK(!memcmp(a,b,5000));f.recording_paused=false;
  f.kind=COMP_RUNTIME_FRAME_HOLD;f.hold_bucket=3;draw(&f,7200,a);
  f.hold_bucket=0;draw(&f,7200,b);CHECK(!memcmp(a,b,5000));f.kind=COMP_RUNTIME_FRAME_STATUS;
  f.recording_input_level=0;
  draw(&f,359999,a);draw(&f,360000,b);CHECK(memcmp(a,b,16*25)!=0);
  f.recording=DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY;f.record_stop_reason=COMP_RECORD_STOP_NONE;draw(&f,0,a);
  f.record_stop_reason=COMP_RECORD_STOP_STORAGE_FULL;draw(&f,0,b);CHECK(memcmp(a,b,16*25)!=0);
  memset(expected,255,5000);CHECK(comp_screen_framebuffer_init(&fb,expected,5000,200,200));comp_screen_framebuffer_draw_text(&fb,94,5,"FULL",1,true);
  for(unsigned y=5;y<12;y++)for(unsigned x=94;x<118;x++) CHECK((expected[y*25+x/8]&(0x80u>>(x%8)))==(b[y*25+x/8]&(0x80u>>(x%8))));
  puts("PASS: long recording timer advances and full-stop status is visibly different from a normal stop");return 0;
}


#include <stdbool.h>
#include <stdint.h>
bool comp_runtime_resources_read(void *context, const char *id, uint8_t frame[5000]) { (void)context; (void)id; (void)frame; return false; }

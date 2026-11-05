# WBA asynchronous screen presenter

`screen_presenter_wba` connects an immutable `comp_runtime_frame_t` snapshot to
the existing source/component/menu renderer through a callback. It owns no art,
gesture, menu, or expression policy. The renderer produces one complete browser
coordinate 200x200 1-bpp frame in a caller-owned staging buffer.

The presenter applies the accepted WB product mapping (vertical row flip only),
finds the exact changed-byte bounding window, and reuses `refresh_policy` to
choose a partial transaction, Mode-2 0xFF family/fast boundary, or explicit
Mode-1 surface/menu-view boundary. The product sets the partial limit to
UINT8_MAX, disabling periodic full cleanup. The first frame
uses the accepted inverse-target old plane. A committed framebuffer and policy
baseline change only after the SSD1681 driver reports successful completion.
Transport failures invalidate both baselines. Identical pixels complete without
touching the panel only when no explicit family/surface/menu-view boundary is due.

`comp_screen_presenter_wba_service` only observes the panel state. The board
owner must call `comp_ssd1681_wba_poll` once per foreground cycle before calling
the presenter service. This avoids two owners advancing one transaction. The
two frame buffers must remain allocated for the presenter lifetime; no heap is
used.

The row mapping is inherited from accepted WB behavior and is not yet physical
V1.1 evidence. Panel polarity, mapping, waveform quality, and the required reset
rework remain real-hardware acceptance items. PCB evidence establishes that the
as-designed `EPD_RES` net ends only at `JP2.10`, so a missing reset callback
continues to produce a visible failed completion rather than a fabricated pin.

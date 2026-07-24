# Companion Listening Chrome Direction

Date: 2026-07-24

## Official guidance

- Amazon Alexa Auto keeps listening, thinking, and responding as distinct persistent states and warns against duplicate voice chrome: https://developer.amazon.com/en-US/docs/alexa/alexa-auto/invoking-alexa.html
- Amazon's light-ring guidance uses directional listening feedback and separate state-specific motion: https://developer.amazon.com/en-US/alexa/branding/alexa-guidelines/brand-guidelines/light-ring
- Microsoft voice-input guidance requires clear feedback that the system is listening: https://learn.microsoft.com/en-us/windows/mixed-reality/design/voice-input
- Apple's program terms require a reasonably conspicuous recording indicator: https://developer.apple.com/programs/information/Apple_Developer_Program_Information_8_12_15.pdf
- Apple's discrete level indicator is suitable for audio-level presentation: https://developer.apple.com/documentation/appkit/nslevelindicator
- Android's official Visualizer API models audio visualization from consecutive waveform or FFT samples: https://developer.android.com/reference/android/media/audiofx/Visualizer.html

## Product decision

The official sources define state clarity, directionality, recording disclosure, and sampled level feedback; they do not prescribe Companion's geometry. For this 200x200 1-bit e-paper target, use one compact grouped accessory:

- one persistent recording dot;
- three equal discrete vertical level columns;
- one quantized sample enters at the outer column per committed approximately 480 ms frame;
- prior samples shift one column inward toward the face;
- column height encodes input level;
- no arcs, parentheses, smooth animation, duplicate microphone mark, or browser-only frame.

The browser uses a fixed deterministic sample sequence for review. The physical product may later replace only the sample source with the accepted platform audio-level event; composition, cadence, bounds, and framebuffer bytes stay identical.

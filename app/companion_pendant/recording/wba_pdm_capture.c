#include "wba_pdm_capture.h"

#include <limits.h>
#include <string.h>

#define COMP_WBA_PDM_DC_ALPHA_Q15 32375

/* Aggregate eight chronological +/-1 bits exactly. Sum2 weights are
 * [8,7,...,1], sum3 weights [36,28,21,15,10,6,3,1]. Pack signed byte sums
 * into one aligned word so the M33 needs one Flash load per PDM byte. */
static const uint32_t byte_sums[256] = {
    0x88DCF8u, 0x8ADEFAu, 0x8EE0FAu, 0x90E2FCu, 0x94E2FAu, 0x96E4FCu, 0x9AE6FCu, 0x9CE8FEu,
    0x9CE4FAu, 0x9EE6FCu, 0xA2E8FCu, 0xA4EAFEu, 0xA8EAFCu, 0xAAECFEu, 0xAEEEFEu, 0xB0F000u,
    0xA6E6FAu, 0xA8E8FCu, 0xACEAFCu, 0xAEECFEu, 0xB2ECFCu, 0xB4EEFEu, 0xB8F0FEu, 0xBAF200u,
    0xBAEEFCu, 0xBCF0FEu, 0xC0F2FEu, 0xC2F400u, 0xC6F4FEu, 0xC8F600u, 0xCCF800u, 0xCEFA02u,
    0xB2E8FAu, 0xB4EAFCu, 0xB8ECFCu, 0xBAEEFEu, 0xBEEEFCu, 0xC0F0FEu, 0xC4F2FEu, 0xC6F400u,
    0xC6F0FCu, 0xC8F2FEu, 0xCCF4FEu, 0xCEF600u, 0xD2F6FEu, 0xD4F800u, 0xD8FA00u, 0xDAFC02u,
    0xD0F2FCu, 0xD2F4FEu, 0xD6F6FEu, 0xD8F800u, 0xDCF8FEu, 0xDEFA00u, 0xE2FC00u, 0xE4FE02u,
    0xE4FAFEu, 0xE6FC00u, 0xEAFE00u, 0xEC0002u, 0xF00000u, 0xF20202u, 0xF60402u, 0xF80604u,
    0xC0EAFAu, 0xC2ECFCu, 0xC6EEFCu, 0xC8F0FEu, 0xCCF0FCu, 0xCEF2FEu, 0xD2F4FEu, 0xD4F600u,
    0xD4F2FCu, 0xD6F4FEu, 0xDAF6FEu, 0xDCF800u, 0xE0F8FEu, 0xE2FA00u, 0xE6FC00u, 0xE8FE02u,
    0xDEF4FCu, 0xE0F6FEu, 0xE4F8FEu, 0xE6FA00u, 0xEAFAFEu, 0xECFC00u, 0xF0FE00u, 0xF20002u,
    0xF2FCFEu, 0xF4FE00u, 0xF80000u, 0xFA0202u, 0xFE0200u, 0x000402u, 0x040602u, 0x060804u,
    0xEAF6FCu, 0xECF8FEu, 0xF0FAFEu, 0xF2FC00u, 0xF6FCFEu, 0xF8FE00u, 0xFC0000u, 0xFE0202u,
    0xFEFEFEu, 0x000000u, 0x040200u, 0x060402u, 0x0A0400u, 0x0C0602u, 0x100802u, 0x120A04u,
    0x0800FEu, 0x0A0200u, 0x0E0400u, 0x100602u, 0x140600u, 0x160802u, 0x1A0A02u, 0x1C0C04u,
    0x1C0800u, 0x1E0A02u, 0x220C02u, 0x240E04u, 0x280E02u, 0x2A1004u, 0x2E1204u, 0x301406u,
    0xD0ECFAu, 0xD2EEFCu, 0xD6F0FCu, 0xD8F2FEu, 0xDCF2FCu, 0xDEF4FEu, 0xE2F6FEu, 0xE4F800u,
    0xE4F4FCu, 0xE6F6FEu, 0xEAF8FEu, 0xECFA00u, 0xF0FAFEu, 0xF2FC00u, 0xF6FE00u, 0xF80002u,
    0xEEF6FCu, 0xF0F8FEu, 0xF4FAFEu, 0xF6FC00u, 0xFAFCFEu, 0xFCFE00u, 0x000000u, 0x020202u,
    0x02FEFEu, 0x040000u, 0x080200u, 0x0A0402u, 0x0E0400u, 0x100602u, 0x140802u, 0x160A04u,
    0xFAF8FCu, 0xFCFAFEu, 0x00FCFEu, 0x02FE00u, 0x06FEFEu, 0x080000u, 0x0C0200u, 0x0E0402u,
    0x0E00FEu, 0x100200u, 0x140400u, 0x160602u, 0x1A0600u, 0x1C0802u, 0x200A02u, 0x220C04u,
    0x1802FEu, 0x1A0400u, 0x1E0600u, 0x200802u, 0x240800u, 0x260A02u, 0x2A0C02u, 0x2C0E04u,
    0x2C0A00u, 0x2E0C02u, 0x320E02u, 0x341004u, 0x381002u, 0x3A1204u, 0x3E1404u, 0x401606u,
    0x08FAFCu, 0x0AFCFEu, 0x0EFEFEu, 0x100000u, 0x1400FEu, 0x160200u, 0x1A0400u, 0x1C0602u,
    0x1C02FEu, 0x1E0400u, 0x220600u, 0x240802u, 0x280800u, 0x2A0A02u, 0x2E0C02u, 0x300E04u,
    0x2604FEu, 0x280600u, 0x2C0800u, 0x2E0A02u, 0x320A00u, 0x340C02u, 0x380E02u, 0x3A1004u,
    0x3A0C00u, 0x3C0E02u, 0x401002u, 0x421204u, 0x461202u, 0x481404u, 0x4C1604u, 0x4E1806u,
    0x3206FEu, 0x340800u, 0x380A00u, 0x3A0C02u, 0x3E0C00u, 0x400E02u, 0x441002u, 0x461204u,
    0x460E00u, 0x481002u, 0x4C1202u, 0x4E1404u, 0x521402u, 0x541604u, 0x581804u, 0x5A1A06u,
    0x501000u, 0x521202u, 0x561402u, 0x581604u, 0x5C1602u, 0x5E1804u, 0x621A04u, 0x641C06u,
    0x641802u, 0x661A04u, 0x6A1C04u, 0x6C1E06u, 0x701E04u, 0x722006u, 0x762206u, 0x782408u,
};

/* First byte propagated through the following eight PDM clocks.
 * Signed fields are a:[7:0], (8a+b):[15:8], (36a+8b+c):[31:16].
 * Combining two chronological byte steps is exact modulo2^32, including
 * arbitrary wrapping history. The alternate microphone byte is untouched. */
static const uint32_t byte_sums_forward8[256] = {
    0xFD489CF8u, 0xFDA2AEFAu, 0xFDB6B0FAu, 0xFE10C2FCu, 0xFDCCB2FAu, 0xFE26C4FCu, 0xFE3AC6FCu, 0xFE94D8FEu,
    0xFDE4B4FAu, 0xFE3EC6FCu, 0xFE52C8FCu, 0xFEACDAFEu, 0xFE68CAFCu, 0xFEC2DCFEu, 0xFED6DEFEu, 0xFF30F000u,
    0xFDFEB6FAu, 0xFE58C8FCu, 0xFE6CCAFCu, 0xFEC6DCFEu, 0xFE82CCFCu, 0xFEDCDEFEu, 0xFEF0E0FEu, 0xFF4AF200u,
    0xFE9ACEFCu, 0xFEF4E0FEu, 0xFF08E2FEu, 0xFF62F400u, 0xFF1EE4FEu, 0xFF78F600u, 0xFF8CF800u, 0xFFE60A02u,
    0xFE1AB8FAu, 0xFE74CAFCu, 0xFE88CCFCu, 0xFEE2DEFEu, 0xFE9ECEFCu, 0xFEF8E0FEu, 0xFF0CE2FEu, 0xFF66F400u,
    0xFEB6D0FCu, 0xFF10E2FEu, 0xFF24E4FEu, 0xFF7EF600u, 0xFF3AE6FEu, 0xFF94F800u, 0xFFA8FA00u, 0x00020C02u,
    0xFED0D2FCu, 0xFF2AE4FEu, 0xFF3EE6FEu, 0xFF98F800u, 0xFF54E8FEu, 0xFFAEFA00u, 0xFFC2FC00u, 0x001C0E02u,
    0xFF6CEAFEu, 0xFFC6FC00u, 0xFFDAFE00u, 0x00341002u, 0xFFF00000u, 0x004A1202u, 0x005E1402u, 0x00B82604u,
    0xFE38BAFAu, 0xFE92CCFCu, 0xFEA6CEFCu, 0xFF00E0FEu, 0xFEBCD0FCu, 0xFF16E2FEu, 0xFF2AE4FEu, 0xFF84F600u,
    0xFED4D2FCu, 0xFF2EE4FEu, 0xFF42E6FEu, 0xFF9CF800u, 0xFF58E8FEu, 0xFFB2FA00u, 0xFFC6FC00u, 0x00200E02u,
    0xFEEED4FCu, 0xFF48E6FEu, 0xFF5CE8FEu, 0xFFB6FA00u, 0xFF72EAFEu, 0xFFCCFC00u, 0xFFE0FE00u, 0x003A1002u,
    0xFF8AECFEu, 0xFFE4FE00u, 0xFFF80000u, 0x00521202u, 0x000E0200u, 0x00681402u, 0x007C1602u, 0x00D62804u,
    0xFF0AD6FCu, 0xFF64E8FEu, 0xFF78EAFEu, 0xFFD2FC00u, 0xFF8EECFEu, 0xFFE8FE00u, 0xFFFC0000u, 0x00561202u,
    0xFFA6EEFEu, 0x00000000u, 0x00140200u, 0x006E1402u, 0x002A0400u, 0x00841602u, 0x00981802u, 0x00F22A04u,
    0xFFC0F0FEu, 0x001A0200u, 0x002E0400u, 0x00881602u, 0x00440600u, 0x009E1802u, 0x00B21A02u, 0x010C2C04u,
    0x005C0800u, 0x00B61A02u, 0x00CA1C02u, 0x01242E04u, 0x00E01E02u, 0x013A3004u, 0x014E3204u, 0x01A84406u,
    0xFE58BCFAu, 0xFEB2CEFCu, 0xFEC6D0FCu, 0xFF20E2FEu, 0xFEDCD2FCu, 0xFF36E4FEu, 0xFF4AE6FEu, 0xFFA4F800u,
    0xFEF4D4FCu, 0xFF4EE6FEu, 0xFF62E8FEu, 0xFFBCFA00u, 0xFF78EAFEu, 0xFFD2FC00u, 0xFFE6FE00u, 0x00401002u,
    0xFF0ED6FCu, 0xFF68E8FEu, 0xFF7CEAFEu, 0xFFD6FC00u, 0xFF92ECFEu, 0xFFECFE00u, 0x00000000u, 0x005A1202u,
    0xFFAAEEFEu, 0x00040000u, 0x00180200u, 0x00721402u, 0x002E0400u, 0x00881602u, 0x009C1802u, 0x00F62A04u,
    0xFF2AD8FCu, 0xFF84EAFEu, 0xFF98ECFEu, 0xFFF2FE00u, 0xFFAEEEFEu, 0x00080000u, 0x001C0200u, 0x00761402u,
    0xFFC6F0FEu, 0x00200200u, 0x00340400u, 0x008E1602u, 0x004A0600u, 0x00A41802u, 0x00B81A02u, 0x01122C04u,
    0xFFE0F2FEu, 0x003A0400u, 0x004E0600u, 0x00A81802u, 0x00640800u, 0x00BE1A02u, 0x00D21C02u, 0x012C2E04u,
    0x007C0A00u, 0x00D61C02u, 0x00EA1E02u, 0x01443004u, 0x01002002u, 0x015A3204u, 0x016E3404u, 0x01C84606u,
    0xFF48DAFCu, 0xFFA2ECFEu, 0xFFB6EEFEu, 0x00100000u, 0xFFCCF0FEu, 0x00260200u, 0x003A0400u, 0x00941602u,
    0xFFE4F2FEu, 0x003E0400u, 0x00520600u, 0x00AC1802u, 0x00680800u, 0x00C21A02u, 0x00D61C02u, 0x01302E04u,
    0xFFFEF4FEu, 0x00580600u, 0x006C0800u, 0x00C61A02u, 0x00820A00u, 0x00DC1C02u, 0x00F01E02u, 0x014A3004u,
    0x009A0C00u, 0x00F41E02u, 0x01082002u, 0x01623204u, 0x011E2202u, 0x01783404u, 0x018C3604u, 0x01E64806u,
    0x001AF6FEu, 0x00740800u, 0x00880A00u, 0x00E21C02u, 0x009E0C00u, 0x00F81E02u, 0x010C2002u, 0x01663204u,
    0x00B60E00u, 0x01102002u, 0x01242202u, 0x017E3404u, 0x013A2402u, 0x01943604u, 0x01A83804u, 0x02024A06u,
    0x00D01000u, 0x012A2202u, 0x013E2402u, 0x01983604u, 0x01542602u, 0x01AE3804u, 0x01C23A04u, 0x021C4C06u,
    0x016C2802u, 0x01C63A04u, 0x01DA3C04u, 0x02344E06u, 0x01F03E04u, 0x024A5006u, 0x025E5206u, 0x02B86408u,
};

static bool config_valid(const comp_wba_pdm_config_t *config)
{
    return config != NULL &&
           (config->layout == COMP_WBA_PDM_LAYOUT_LEFT_RIGHT_BYTES ||
            config->layout == COMP_WBA_PDM_LAYOUT_RIGHT_LEFT_BYTES) &&
           (config->bit_order == COMP_WBA_PDM_MSB_FIRST ||
            config->bit_order == COMP_WBA_PDM_LSB_FIRST) &&
           config->output <= COMP_WBA_PDM_OUTPUT_BEAMFORM &&
           (config->output != COMP_WBA_PDM_OUTPUT_BEAMFORM ||
            comp_wba_dual_mic_config_valid(&config->dual_mic)) &&
           (config->decimation == 64u || config->decimation == 96u ||
            config->decimation == 128u) &&
           config->gain_q15 > 0u &&
           config->gain_q15 <= COMP_WBA_PDM_GAIN_Q15_MAX &&
           config->emit_pcm_frame != NULL &&
           ((config->observe_pair_frame == NULL && config->pair_pcm_storage == NULL &&
             config->pair_pcm_capacity == 0u) ||
            (config->observe_pair_frame != NULL && config->pair_pcm_storage != NULL &&
             config->pair_pcm_capacity >= 2u * COMP_WBA_PDM_PCM_FRAME_SAMPLES));
}

static int64_t modulo_u32_to_i64(uint32_t value)
{
    if (value <= (uint32_t)INT32_MAX) {
        return (int64_t)value;
    }
    return -1 - (int64_t)(UINT32_MAX - value);
}

static int32_t clamp_i64_to_i32(int64_t value)
{
    if (value > INT32_MAX) return INT32_MAX;
    if (value < INT32_MIN) return INT32_MIN;
    return (int32_t)value;
}

static int32_t dc_block(comp_wba_pdm_channel_state_t *channel, int32_t sample)
{
    int64_t filtered;
    int32_t output;

    if (!channel->dc_initialized) {
        channel->dc_previous_input = sample;
        channel->dc_previous_output = 0;
        channel->dc_initialized = true;
        return 0;
    }
    filtered = (int64_t)sample - channel->dc_previous_input +
               (((int64_t)channel->dc_previous_output *
                 COMP_WBA_PDM_DC_ALPHA_Q15) >> 15u);
    output = clamp_i64_to_i32(filtered);
    channel->dc_previous_input = sample;
    channel->dc_previous_output = output;
    return output;
}

static uint8_t reverse_byte(uint8_t value)
{
    value = (uint8_t)(((value & 0x55u) << 1u) |
                      ((value & 0xAAu) >> 1u));
    value = (uint8_t)(((value & 0x33u) << 2u) |
                      ((value & 0xCCu) >> 2u));
    return (uint8_t)((value << 4u) | (value >> 4u));
}

static uint32_t add_signed(uint32_t value, int32_t delta)
{
    return value + (uint32_t)delta;
}

#if defined(_MSC_VER)
#define COMP_PDM_BYTE_INLINE static __forceinline
#elif defined(__GNUC__) || defined(__clang__)
#define COMP_PDM_BYTE_INLINE static inline __attribute__((always_inline))
#else
#define COMP_PDM_BYTE_INLINE static inline
#endif

/* Most bytes only advance the integrators. Keep that work in the byte loop;
 * the wider comb/gain/DC work is needed only at a PCM sample boundary. */
COMP_PDM_BYTE_INLINE void integrate_byte_run(
    comp_wba_pdm_channel_state_t *channel, const uint8_t *raw, size_t pairs,
    bool lsb_first, bool invert)
{
    uint32_t one = channel->integrator1;
    uint32_t two = channel->integrator2;
    uint32_t three = channel->integrator3;

    /* No comb/output callback can observe a partial PCM sample. Keep the
     * modulo-2^32 integrators in registers until this bounded run ends. The
     * other microphone occupies the alternate byte in the copied DMA span. */
    size_t i = 0u;
    if (!lsb_first && !invert) {
        for (; i + 1u < pairs; i += 2u) {
            uint32_t first_sums = byte_sums_forward8[raw[2u * i]];
            uint32_t last_sums = byte_sums[raw[2u * (i + 1u)]];
            three = add_signed(add_signed(three + 16u * two + 136u * one,
                                          (int16_t)(first_sums >> 16u)),
                               (int8_t)(last_sums >> 16u));
            two = add_signed(add_signed(two + 16u * one, (int8_t)(first_sums >> 8u)),
                             (int8_t)(last_sums >> 8u));
            one = add_signed(add_signed(one, (int8_t)first_sums), (int8_t)last_sums);
        }
    } else {
        for (; i + 1u < pairs; i += 2u) {
            uint8_t first = raw[2u * i], last = raw[2u * (i + 1u)];
            if (lsb_first) {first = reverse_byte(first); last = reverse_byte(last);}
            if (invert) {first ^= UINT8_MAX; last ^= UINT8_MAX;}
            uint32_t first_sums = byte_sums_forward8[first], last_sums = byte_sums[last];
            three = add_signed(add_signed(three + 16u * two + 136u * one,
                                          (int16_t)(first_sums >> 16u)),
                               (int8_t)(last_sums >> 16u));
            two = add_signed(add_signed(two + 16u * one, (int8_t)(first_sums >> 8u)),
                             (int8_t)(last_sums >> 8u));
            one = add_signed(add_signed(one, (int8_t)first_sums), (int8_t)last_sums);
        }
    }
    if (i < pairs) {
        uint8_t byte = raw[2u * i];
        if (lsb_first) byte = reverse_byte(byte);
        if (invert) byte ^= UINT8_MAX;
        uint32_t sums = byte_sums[byte];
        three = add_signed(three + 8u * two + 36u * one, (int8_t)(sums >> 16u));
        two = add_signed(two + 8u * one, (int8_t)(sums >> 8u));
        one = add_signed(one, (int8_t)sums);
    }
    channel->integrator1 = one;
    channel->integrator2 = two;
    channel->integrator3 = three;
    channel->decimation_phase += (uint16_t)(8u * pairs);
}

static int32_t finish_sample(const comp_wba_pdm_config_t *config,
                             comp_wba_pdm_channel_state_t *channel)
{
    uint32_t comb_input;
    uint32_t difference1;
    uint32_t difference2;
    uint32_t difference3;
    int64_t normalized;

    channel->decimation_phase = 0u;

    comb_input = channel->integrator3;
    difference1 = comb_input - channel->comb1;
    channel->comb1 = comb_input;
    difference2 = difference1 - channel->comb2;
    channel->comb2 = difference1;
    difference3 = difference2 - channel->comb3;
    channel->comb3 = difference2;

    /* Normal96x capture uses gain128*Q15_ONE. Since96^3=32768*27,
     * its exact quotient is (signed CIC*128)/27. Prove the signed product
     * fits32 bits before multiplying; retain the general path for arbitrary
     * wrapping history or any other gain. No changed rounding or clipping. */
    if(config->decimation==96u&&config->gain_q15==128u*COMP_WBA_PDM_GAIN_Q15_ONE&&
       difference3+UINT32_C(0x01000000)<UINT32_C(0x02000000))
        return dc_block(channel,((int32_t)difference3*128)/27);

    normalized = modulo_u32_to_i64(difference3) * config->gain_q15;
    /* Preserve truncation toward zero, including arbitrary comb history.
     * floor(m / (32768 * 27)) == floor((m >> 15) / 27). Valid 96x streams
     * fit the shifted magnitude in 32 bits even at maximum gain, avoiding
     * the general 64-bit quotient sequence for every sample on Cortex-M33. */
    bool negative = normalized < 0;
    uint64_t magnitude = negative ? (uint64_t)(-(normalized + 1)) + 1u : (uint64_t)normalized;
    if (config->decimation == 96u) {
        uint64_t scaled = magnitude >> 15u;
        if (scaled <= UINT32_MAX) {
            normalized = (int64_t)((uint32_t)scaled / 27u);
        } else {
            normalized = (int64_t)(scaled / UINT64_C(27));
        }
    } else {
        normalized = (int64_t)(magnitude >> (config->decimation == 64u ? 18u : 21u));
    }
    if (negative) normalized = -normalized;
    return dc_block(channel, clamp_i64_to_i32(normalized));
}

static int16_t clamp_pcm(int32_t sample)
{
    if (sample > INT16_MAX) {
        return INT16_MAX;
    }
    if (sample < INT16_MIN) {
        return INT16_MIN;
    }
    return (int16_t)sample;
}

static int16_t saturate_output(comp_wba_pdm_capture_t *capture,
                               int32_t sample)
{
    int16_t clamped = clamp_pcm(sample);

    if ((int32_t)clamped != sample) capture->stats.saturated_samples++;
    return clamped;
}

static uint32_t abs_i16(int16_t sample)
{
    return sample < 0 ? (uint32_t)(-(int32_t)sample) : (uint32_t)sample;
}

static void account_channel(comp_wba_pdm_capture_t *capture,
                            int16_t left,
                            int16_t right)
{
    /* Zero contributes neither energy nor a new peak. In selected-only
     * mono the inactive channel is always zero, so avoid its 64-bit update
     * without changing statistics if both channels are actually processed. */
    if (left != 0) {
        uint32_t left_abs = abs_i16(left);
        capture->stats.left_abs_energy += left_abs;
        if (left_abs > abs_i16(capture->stats.left_peak)) {
            capture->stats.left_peak = left;
        }
    }
    if (right != 0) {
        uint32_t right_abs = abs_i16(right);
        capture->stats.right_abs_energy += right_abs;
        if (right_abs > abs_i16(capture->stats.right_peak)) {
            capture->stats.right_peak = right;
        }
    }
}

static void emit_sample(comp_wba_pdm_capture_t *capture,
                        int32_t left_value,
                        int32_t right_value)
{
    int16_t left = clamp_pcm(left_value);
    int16_t right = clamp_pcm(right_value);
    int32_t selected;

    account_channel(capture, left, right);
    switch (capture->config.output) {
    case COMP_WBA_PDM_OUTPUT_LEFT:
        selected = left_value;
        break;
    case COMP_WBA_PDM_OUTPUT_RIGHT:
        selected = right_value;
        break;
    case COMP_WBA_PDM_OUTPUT_BEAMFORM:
        selected = comp_wba_dual_mic_process(&capture->dual_mic, left_value, right_value);
        break;
    default:
        selected = clamp_i64_to_i32(
            ((int64_t)left_value + (int64_t)right_value) / 2);
        break;
    }
    if (capture->config.observe_pair_frame != NULL) {
        capture->config.pair_pcm_storage[2u*capture->pcm_frame_count] = left;
        capture->config.pair_pcm_storage[2u*capture->pcm_frame_count+1u] = right;
    }
    capture->pcm_frame[capture->pcm_frame_count++] =
        saturate_output(capture, selected);
    capture->stats.pcm_samples_generated++;
    if (capture->pcm_frame_count == COMP_WBA_PDM_PCM_FRAME_SAMPLES) {
        bool accepted = capture->config.emit_pcm_frame(
            capture->config.context, capture->pcm_frame,
            COMP_WBA_PDM_PCM_FRAME_SAMPLES, COMP_WBA_PDM_PCM_SAMPLE_RATE_HZ);
        if (accepted) {
            capture->stats.pcm_frames_emitted++;
            if (capture->config.observe_pair_frame != NULL)
                capture->config.observe_pair_frame(capture->config.context,
                    capture->config.pair_pcm_storage, COMP_WBA_PDM_PCM_FRAME_SAMPLES,
                    COMP_WBA_PDM_PCM_SAMPLE_RATE_HZ);
        } else {
            capture->stats.pcm_frames_rejected++;
            capture->stats.pcm_samples_discarded +=
                COMP_WBA_PDM_PCM_FRAME_SAMPLES;
        }
        capture->pcm_frame_count = 0u;
    }
}

static void reset_filter_state(comp_wba_pdm_capture_t *capture,
                               bool discard_partial)
{
    if (discard_partial && capture->pcm_frame_count != 0u) {
        capture->stats.pcm_samples_discarded += capture->pcm_frame_count;
    }
    memset(capture->channels, 0, sizeof(capture->channels));
    capture->dual_mic.config = capture->config.dual_mic;
    comp_wba_dual_mic_reset(&capture->dual_mic);
    capture->pcm_frame_count = 0u;
}

void comp_wba_pdm_capture_init(comp_wba_pdm_capture_t *capture,
                               const comp_wba_pdm_config_t *config)
{
    if (capture == NULL) return;
    memset(capture, 0, sizeof(*capture));
    if (config != NULL) capture->config = *config;
    capture->configured = config_valid(config);
    reset_filter_state(capture, false);
}

bool comp_wba_pdm_capture_ready(const comp_wba_pdm_capture_t *capture)
{
    return capture != NULL && capture->configured;
}

void comp_wba_pdm_capture_reset_stream(comp_wba_pdm_capture_t *capture)
{
    if (capture == NULL) return;
    reset_filter_state(capture, true);
    capture->have_dma_sequence = false;
}

uint8_t comp_wba_pdm_capture_channel_mask(const comp_wba_pdm_capture_t *capture)
{
    if(!comp_wba_pdm_capture_ready(capture))return 0u;
    return capture->config.observe_pair_frame != NULL || !capture->config.selected_only || capture->config.output>=COMP_WBA_PDM_OUTPUT_MIX?3u:
        capture->config.output==COMP_WBA_PDM_OUTPUT_LEFT?1u:2u;
}

static bool consume_byte_pairs(comp_wba_pdm_capture_t *capture,
                                const uint8_t *raw, size_t raw_bytes,
                                bool priming)
{
    size_t pair_index;
    uint32_t pending_bits = 0u;
    const size_t left_offset = capture->config.layout == COMP_WBA_PDM_LAYOUT_LEFT_RIGHT_BYTES ? 0u : 1u;
    const size_t right_offset = left_offset ^ 1u;
    const bool lsb_first = capture->config.bit_order == COMP_WBA_PDM_LSB_FIRST;
    const bool invert_left = capture->config.invert_left;
    const bool invert_right = capture->config.invert_right;
    const uint8_t channels=comp_wba_pdm_capture_channel_mask(capture);
    const bool process_left=(channels&1u)!=0u, process_right=(channels&2u)!=0u;
    for (pair_index = 0u; pair_index < raw_bytes;) {
        size_t pairs = 1u;
        uint16_t phase = capture->channels[process_left?0u:1u].decimation_phase;
        if ((!process_left || !process_right || phase == capture->channels[1].decimation_phase) &&
            phase < capture->config.decimation) {
            /* Stop at the next PCM boundary, including when a bounded DMA
             * copy splits the sample. A mismatched phase retains one-pair
             * failure detection and the original discard/reset behavior. */
            pairs = ((size_t)capture->config.decimation - phase + 7u) / 8u;
            size_t available = (raw_bytes - pair_index) / 2u;
            if (pairs > available) pairs = available;
        }
        {
            if(process_left)integrate_byte_run(&capture->channels[0], raw + pair_index + left_offset,
                               pairs, lsb_first, invert_left);
            if(process_right)integrate_byte_run(&capture->channels[1], raw + pair_index + right_offset,
                               pairs, lsb_first, invert_right);
            pair_index += 2u * pairs;
            bool left_ready = process_left && capture->channels[0].decimation_phase >=
                              capture->config.decimation;
            bool right_ready = process_right && capture->channels[1].decimation_phase >=
                               capture->config.decimation;

            pending_bits += (uint32_t)(8u * pairs);
            if ((!process_left || left_ready) && (!process_right || right_ready)) {
                int32_t left_sample = process_left?finish_sample(
                    &capture->config, &capture->channels[0]):0;
                int32_t right_sample = process_right?finish_sample(
                    &capture->config, &capture->channels[1]):0;
                /* Credit before a callback can inspect stats. Flush partial
                 * spans and faulting pairs too, without a 64-bit add per byte. */
                capture->stats.pdm_bits_per_channel += pending_bits;
                pending_bits = 0u;
                if (priming) {
                    if (capture->config.output == COMP_WBA_PDM_OUTPUT_BEAMFORM)
                        (void)comp_wba_dual_mic_process(&capture->dual_mic, left_sample, right_sample);
                    capture->stats.pcm_samples_generated++;
                    capture->stats.pcm_samples_discarded++;
                } else {
                    emit_sample(capture, left_sample, right_sample);
                }
            } else if (left_ready != right_ready) {
                capture->stats.pdm_bits_per_channel += pending_bits;
                capture->stats.invalid_dma_blocks++;
                reset_filter_state(capture, true);
                return false;
            }
        }
    }
    capture->stats.pdm_bits_per_channel += pending_bits;
    return true;
}

static bool consume_dma_span(comp_wba_pdm_capture_t *capture,
                              const uint8_t *raw, size_t raw_bytes,
                              uint32_t dma_sequence, bool priming,
                              comp_wba_pdm_read_fn_t read, void *context)
{
    if (!comp_wba_pdm_capture_ready(capture) || (raw == NULL && read == NULL) ||
        raw_bytes == 0u || (raw_bytes & 1u) != 0u) {
        if (capture != NULL) capture->stats.invalid_dma_blocks++;
        return false;
    }
    size_t bytes_per_sample = (size_t)capture->config.decimation / 8u *
                              COMP_WBA_PDM_CHANNEL_COUNT;
    if ((read != NULL &&
         (raw_bytes != COMP_WBA_PDM_PCM_FRAME_SAMPLES * bytes_per_sample ||
          capture->pcm_frame_count != 0u ||
          capture->channels[0].decimation_phase != 0u ||
          capture->channels[1].decimation_phase != 0u)) ||
        (priming && (capture->have_dma_sequence || capture->pcm_frame_count != 0u ||
                     raw_bytes < 3u * bytes_per_sample || raw_bytes % bytes_per_sample != 0u))) {
        capture->stats.invalid_dma_blocks++;
        return false;
    }
    if (capture->have_dma_sequence && dma_sequence != capture->expected_dma_sequence) {
        uint32_t forward = dma_sequence - capture->expected_dma_sequence;
        if (forward < UINT32_C(0x80000000)) {
            capture->stats.missing_dma_blocks += forward;
        } else {
            capture->stats.reordered_dma_blocks++;
            return false;
        }
        reset_filter_state(capture, true);
    }
    capture->have_dma_sequence = true;
    capture->expected_dma_sequence = dma_sequence + 1u;
    capture->stats.last_dma_sequence = dma_sequence;
    capture->stats.dma_blocks++;
    capture->stats.raw_bytes += raw_bytes;
    size_t offset = 0u;
    while (offset < raw_bytes) {
        const uint8_t *chunk = raw != NULL ? raw + offset : NULL;
        size_t count = raw_bytes - offset;
        if (read != NULL && (!read(context, offset, &chunk, &count) ||
            chunk == NULL || count == 0u || (count & 1u) != 0u || count > raw_bytes - offset)) {
            capture->stats.invalid_dma_blocks++;
            reset_filter_state(capture, true);
            return false;
        }
        if (!consume_byte_pairs(capture, chunk, count, priming)) return false;
        offset += count;
    }
    if (priming) {
        /* The zero-history CIC ramp is now outside the recording. Anchor
         * the high-pass feedback at the settled boundary while preserving
         * the CIC and last input; resetting either recreates the impulse. */
        capture->channels[0].dc_previous_output = 0;
        capture->channels[1].dc_previous_output = 0;
    }
    return true;
}

bool comp_wba_pdm_capture_prime(comp_wba_pdm_capture_t *capture,
                                const uint8_t *raw,
                                size_t raw_bytes,
                                uint32_t dma_sequence)
{
    return consume_dma_span(capture, raw, raw_bytes, dma_sequence, true, NULL, NULL);
}

bool comp_wba_pdm_capture_ingest(comp_wba_pdm_capture_t *capture,
                                 const uint8_t *raw,
                                 size_t raw_bytes,
                                 uint32_t dma_sequence)
{
    return consume_dma_span(capture, raw, raw_bytes, dma_sequence, false, NULL, NULL);
}

bool comp_wba_pdm_capture_read_frame(comp_wba_pdm_capture_t *capture,
                                    comp_wba_pdm_read_fn_t read,
                                    void *context, size_t raw_bytes,
                                    uint32_t dma_sequence, bool priming)
{
    return consume_dma_span(capture, NULL, raw_bytes, dma_sequence, priming, read, context);
}

const comp_wba_pdm_stats_t *comp_wba_pdm_capture_stats(
    const comp_wba_pdm_capture_t *capture)
{
    return capture != NULL ? &capture->stats : NULL;
}

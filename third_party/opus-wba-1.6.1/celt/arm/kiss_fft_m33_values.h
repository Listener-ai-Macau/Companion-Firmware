/* Companion Cortex-M33 value operands for the existing Xiph EDSP math.
 * Same four multiply/accumulate operations, order and final shifts as
 * kiss_fft_armv5e.h. All source components are loaded before writing m,
 * including in-place m==a. No precision or algorithm change.
 */
#ifndef COMPANION_KISS_FFT_M33_VALUES_H
#define COMPANION_KISS_FFT_M33_VALUES_H
#if defined(__arm__) && defined(__thumb__) && defined(FIXED_POINT) && !defined(ENABLE_QEXT)
#undef C_MUL
#undef C_MUL4
#undef C_MULC
#define COMP_M33_MUL_PARTS(a,b) \
    int ar__=(a).r,ai__=(a).i; unsigned bp__; \
    __builtin_memcpy(&bp__,&(b),sizeof(bp__)); \
    int mr1__,mr2__,mi__; \
    __asm__("#C_MUL_REG_VALUES\n\t" \
        "smulwb %[mi], %[ai], %[bp]\n\t" \
        "smulwb %[mr1], %[ar], %[bp]\n\t" \
        "smulwt %[mr2], %[ai], %[bp]\n\t" \
        "smlawt %[mi], %[ar], %[bp], %[mi]\n\t" \
        : [mr1]"=&r"(mr1__),[mr2]"=&r"(mr2__),[mi]"=&r"(mi__) \
        : [ar]"r"(ar__),[ai]"r"(ai__),[bp]"r"(bp__))
#define C_MUL(m,a,b) do { COMP_M33_MUL_PARTS(a,b); \
    (m).r=SHL32(SUB32(mr1__,mr2__),1);(m).i=SHL32(mi__,1); } while(0)
#define C_MUL4(m,a,b) do { COMP_M33_MUL_PARTS(a,b); \
    (m).r=SHR32(SUB32(mr1__,mr2__),1);(m).i=SHR32(mi__,1); } while(0)
#define C_MULC(m,a,b) do { \
    int ar__=(a).r,ai__=(a).i;unsigned bp__; \
    __builtin_memcpy(&bp__,&(b),sizeof(bp__)); \
    int mr__,mi1__,mi2__; \
    __asm__("#C_MULC_REG_VALUES\n\t" \
        "smulwb %[mr], %[ar], %[bp]\n\t" \
        "smulwb %[mi1], %[ai], %[bp]\n\t" \
        "smulwt %[mi2], %[ar], %[bp]\n\t" \
        "smlawt %[mr], %[ai], %[bp], %[mr]\n\t" \
        : [mr]"=&r"(mr__),[mi1]"=&r"(mi1__),[mi2]"=&r"(mi2__) \
        : [ar]"r"(ar__),[ai]"r"(ai__),[bp]"r"(bp__)); \
    (m).r=SHL32(mr__,1);(m).i=SHL32(SUB32(mi1__,mi2__),1); } while(0)
#endif
#endif

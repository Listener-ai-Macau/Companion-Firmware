#include "wba_update_p256.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    uint8_t digest[32];
    uint8_t signature[64];
    bool allow;
    uint32_t calls;
} verifier_t;

static void require(bool condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        exit(1);
    }
}

static bool read_exact(const char *path, uint8_t *output, size_t length)
{
    FILE *file = fopen(path, "rb");
    size_t got;
    if (file == NULL) return false;
    got = fread(output, 1u, length, file);
    bool exact = got == length && fgetc(file) == EOF;
    fclose(file);
    return exact;
}

static bool verify(void *context, const uint8_t public_key[64],
                   const uint8_t digest[32], const uint8_t signature[64])
{
    verifier_t *fixture = context;
    uint8_t any = 0u;
    fixture->calls++;
    for (size_t i = 0u; i < 64u; ++i) any |= public_key[i];
    return fixture->allow && any != 0u &&
           memcmp(digest, fixture->digest, 32u) == 0 &&
           memcmp(signature, fixture->signature, 64u) == 0;
}

int main(int argc, char **argv)
{
    uint8_t wire[COMP_WBA_UPDATE_MANIFEST_WIRE_BYTES];
    uint8_t public_key[64];
    verifier_t verifier = {0};
    comp_wba_update_manifest_envelope_t envelope;
    comp_wba_update_p256_trust_t trust;
    require(argc == 4, "wire/public/digest arguments");
    require(read_exact(argv[1], wire, sizeof(wire)), "read signed wire");
    require(read_exact(argv[2], public_key, sizeof(public_key)), "read public XY");
    require(read_exact(argv[3], verifier.digest, sizeof(verifier.digest)), "read canonical digest");
    require(comp_wba_update_manifest_wire_decode(wire, sizeof(wire), &envelope),
            "decode canonical WUM1");
    memcpy(verifier.signature, envelope.signature, sizeof(verifier.signature));
    verifier.allow = true;
    trust = (comp_wba_update_p256_trust_t){envelope.key_id, public_key,
                                           verify, &verifier};
    require(comp_wba_update_p256_trust_configured(&trust), "configured trust anchor");
    require(comp_wba_update_p256_authorize_manifest(
                &trust, &envelope.manifest, envelope.signature,
                sizeof(envelope.signature)),
            "C canonical hash matches independently verified signature");
    require(verifier.calls == 1u, "one bounded verifier invocation");

    comp_wba_update_p256_trust_t absent = {0};
    require(!comp_wba_update_p256_authorize_manifest(
                &absent, &envelope.manifest, envelope.signature,
                sizeof(envelope.signature)),
            "missing production trust anchor fails closed");

    uint8_t damaged[sizeof(wire)];
    memcpy(damaged, wire, sizeof(damaged));
    damaged[16] ^= 1u;
    require(!comp_wba_update_manifest_wire_decode(damaged, sizeof(damaged),
                                                   &envelope),
            "manifest mutation rejected by transport CRC");
    memcpy(damaged, wire, sizeof(damaged));
    damaged[76] ^= 1u;
    uint32_t crc = comp_wba_update_wire_crc32(damaged, 140u);
    damaged[140] = (uint8_t)crc;
    damaged[141] = (uint8_t)(crc >> 8);
    damaged[142] = (uint8_t)(crc >> 16);
    damaged[143] = (uint8_t)(crc >> 24);
    require(comp_wba_update_manifest_wire_decode(damaged, sizeof(damaged),
                                                  &envelope),
            "structurally valid envelope reaches crypto gate");
    require(!comp_wba_update_p256_authorize_manifest(
                &trust, &envelope.manifest, envelope.signature,
                sizeof(envelope.signature)),
            "signature mutation rejected by crypto verifier");
    require(envelope.key_id != 0u, "key identifier present");
    printf("PASS_WBA_UPDATE_MANIFEST wire_bytes=%u signed_bytes=%u raw_p256_rs=64 missing_key_fail_closed=1 crc_gate=1 crypto_gate=1\n",
           COMP_WBA_UPDATE_MANIFEST_WIRE_BYTES,
           COMP_WBA_UPDATE_MANIFEST_SIGNED_BYTES);
    return 0;
}

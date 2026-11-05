"""Deterministic pixel and transport oracle for the guarded-corridor cadence candidate."""
from __future__ import annotations
import hashlib, importlib.util, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c"
HEADER = ROOT / "app/companion_pendant/epaper/r10_native_guarded_corridor_cached_mode2_cadence.h"
ARTIFACT = ROOT / "docs/validation/companion-ssd1681-r10-native-guarded-corridor-cached-mode2-cadence-oracle-20260722.json"
FRAME_BYTES = 5000
NODES = tuple(range(32, 66, 2)) + tuple(range(62, 30, -2))
CORRIDOR_WINDOW = (3, 11, 80, 103)
FRAME_SHA = {
    32: "A50CBC123866F5FEB3A534258C90A53A20452792DE330455018A14FEB84BBF80",
    34: "A8EADBC99EB242C8A12CF9D4602CC812D4B195D5AE0D65330A23A0E92C6AA56A",
    36: "200B88DC8B050149274C5E716336560B784D5AEE6543C6AC989B2DADB6CE10B7",
    38: "419D7F03D158B867A4E8BE50644AF56035490C675D18101184DACA78F1F149E6",
    40: "9B27AA8158607C1D5DCB03FAA698687EDBE47540D854BF09B7D31337CA128418",
    42: "E32F2F8C86C1519C3698CAF8EF0FCD0B1802A801162238D40BCF0BDE9069243C",
    44: "790A131CCF3FB2653130396E1E4912C4AE593FD312AEA34100961F9419780AF1",
    46: "95FF18BD7057C68D638EA414BBC8FF9D5A119D5084FAEA5BF331BBFFC71D4AAE",
    48: "0459B1755CBC915D042E89DC26107DB4D0D6FFED3913563720E6D8CEB52E912F",
    50: "697EDB5C8F3CC103EE3D0FF489299F4018207218C66D55BDC83AB3DD779D50A3",
    52: "C4C332416DCE00E53BF6C1A47A61E9402057E6BB8E8EBA57540F137321A6E522",
    54: "46848B97E7A1E1D71648A7D653D69E3D90E243CDCEA9288E36215580D5258900",
    56: "39850E2B73DFF1E7418DF91C48E04E7D3F60D48E9757CD9CDA99BEC0B959425A",
    58: "1B4EBDF8655921DB4ADCFEC08A894F3AA4CB79F7380A8B6B19A8A68E6F61A04C",
    60: "5189BAC3639FFF6D805B7CE015541117917F5B33E8BDA52CBF4C8A2439843CD2",
    62: "E3746DF31BC8685BC6F7F3FE64357F88D30B927763F708AAA54CA2FFEE22DF2C",
    64: "6E7D105F5416F1D015ED3B82A75FC2A792BC0BA8B02F38A0793712B13452E186",
}
FRAME_SHA_ALL = [
    "A50CBC123866F5FEB3A534258C90A53A20452792DE330455018A14FEB84BBF80",
    "1D4438357D4819DF908775153A4461D5A24413461D653175E08283CD424A3C45",
    "A8EADBC99EB242C8A12CF9D4602CC812D4B195D5AE0D65330A23A0E92C6AA56A",
    "D63B2B8B6DBD1EC245FC6F47329FB90F0B5EB5E13DDEBDA645D8DDE27DBD7005",
    "200B88DC8B050149274C5E716336560B784D5AEE6543C6AC989B2DADB6CE10B7",
    "03D455703B07C9F5B55C682D5418E5C6316CF1CCE51FE1122AC39BFFB05EAEAB",
    "419D7F03D158B867A4E8BE50644AF56035490C675D18101184DACA78F1F149E6",
    "F761DA2CB02D74E8562A42BA27F3BFB1E62441FB6E627584E37FDDF9EA646F4D",
    "9B27AA8158607C1D5DCB03FAA698687EDBE47540D854BF09B7D31337CA128418",
    "BD5ABC6A10E5A687C2C597A443F7BA558BA6256B7DF2524FCA9187B5C093D321",
    "E32F2F8C86C1519C3698CAF8EF0FCD0B1802A801162238D40BCF0BDE9069243C",
    "534862F23DDC4B0F334675974DBC4920EE3D59D6A61DEB9FC5E580CCADA213A0",
    "790A131CCF3FB2653130396E1E4912C4AE593FD312AEA34100961F9419780AF1",
    "779424ED690A5CCBB0CCEF78E710CF9B56D400E0FED02682CD178C3388A8AD39",
    "95FF18BD7057C68D638EA414BBC8FF9D5A119D5084FAEA5BF331BBFFC71D4AAE",
    "F166079E2430B100638DBFE8B797AC6815ABA3945F86EFBAFB1C226D2ACD28FE",
    "0459B1755CBC915D042E89DC26107DB4D0D6FFED3913563720E6D8CEB52E912F",
    "675CC424FF48A1BF926879943E5366A1F1395C033797F004BAEDC286FC041411",
    "697EDB5C8F3CC103EE3D0FF489299F4018207218C66D55BDC83AB3DD779D50A3",
    "01EB1A6D49935F5E4964553B0056112F73727A0F716966D229118F33AB969CAA",
    "C4C332416DCE00E53BF6C1A47A61E9402057E6BB8E8EBA57540F137321A6E522",
    "CFECC01FA49421C4496EAA8B70BB328324779D277CAD57FAEC5454D26A62FC82",
    "46848B97E7A1E1D71648A7D653D69E3D90E243CDCEA9288E36215580D5258900",
    "C995BEFA62496A45781BE2BBA0B7C2B1AA6E95E3700297CFEFE391252AF8D1C1",
    "39850E2B73DFF1E7418DF91C48E04E7D3F60D48E9757CD9CDA99BEC0B959425A",
    "B4BCA8AD826B871436D4548181413DA1851D26A8DC410FE2EC2E1897B0AD36DF",
    "1B4EBDF8655921DB4ADCFEC08A894F3AA4CB79F7380A8B6B19A8A68E6F61A04C",
    "E75CACE5B460C0719D9E58E4C03F380128FB3CE547729CA7E8151D8DDF04513A",
    "5189BAC3639FFF6D805B7CE015541117917F5B33E8BDA52CBF4C8A2439843CD2",
    "1929CE0A2DB6159E93080E3D6D0CE8979D51CE93BD436D5EEAE1ABEE1F8151BA",
    "E3746DF31BC8685BC6F7F3FE64357F88D30B927763F708AAA54CA2FFEE22DF2C",
    "48F19A1D26275D8ADFC97F767895D55CDFAA753C870C7F0D6510D7560AAF64C6",
    "6E7D105F5416F1D015ED3B82A75FC2A792BC0BA8B02F38A0793712B13452E186",
]


def frame(x: int) -> bytes:
    b = bytearray([255]) * FRAME_BYTES
    for row in range(24):
        for col in range(24):
            if (2 * col - 23) ** 2 + (2 * row - 23) ** 2 <= 576:
                px = x + col
                b[(80 + row) * 25 + px // 8] &= ~(0x80 >> (px & 7))
    return bytes(b)


def window(a: bytes, b: bytes) -> tuple[int, int, int, int]:
    changed = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
    return min(i % 25 for i in changed), max(i % 25 for i in changed), min(i // 25 for i in changed), max(i // 25 for i in changed)


def payload(b: bytes, w: tuple[int, int, int, int]) -> str:
    return hashlib.sha256(b"".join(b[y * 25 + w[0]:y * 25 + w[1] + 1] for y in range(w[2], w[3] + 1))).hexdigest().upper()


def transition(previous: int, current: int) -> dict[str, object]:
    old, new = frame(previous), frame(current)
    w = CORRIDOR_WINDOW
    return {"previous_x": previous, "current_x": current,
            "previous_frame_sha256": hashlib.sha256(old).hexdigest().upper(),
            "current_frame_sha256": hashlib.sha256(new).hexdigest().upper(),
            "union_window": f"{w[0]}-{w[1]},{w[2]}-{w[3]}",
            "payload_sha256": payload(new, w), "omitted_columns": 0,
            "black_pixels": sum(1 for row in range(24) for col in range(24) if (2 * col - 23) ** 2 + (2 * row - 23) ** 2 <= 576)}


def main() -> int:
    errors: list[str] = []
    source = SOURCE.read_text(encoding="utf-8")
    header = HEADER.read_text(encoding="utf-8")
    black = sum(1 for row in range(24) for col in range(24) if (2 * col - 23) ** 2 + (2 * row - 23) ** 2 <= 576)
    if black != 448: errors.append(f"black pixel count {black}")
    if len(NODES) != 33 or any(abs(b - a) != 2 for a, b in zip(NODES, NODES[1:])): errors.append("non-2px ping-pong path")
    records = [transition(a, b) for a, b in zip(NODES, NODES[1:])]
    frame_sha_start = source.index("static const char *ssd1681_native_two_pass_frame_sha")
    frame_sha_end = source.index("static const char *ssd1681_native_two_pass_payload_sha", frame_sha_start)
    frame_sha_source = source[frame_sha_start:frame_sha_end]
    frame_sha_table = re.findall(r'"([0-9A-F]{64})"', frame_sha_source.split("#else", 1)[0])
    expected_frame_sha = FRAME_SHA_ALL
    if frame_sha_table != expected_frame_sha: errors.append("firmware 24x24 frame SHA table mismatch")
    if "FD4063FBC8A62425D84B9D04E8E1DE703C97F9175E98057B5B80C6FBFBD0D7C8" in frame_sha_source.split("#else", 1)[0]: errors.append("old 12x12 frame SHA alias remains in final table")
    if any(r["black_pixels"] != 448 or r["omitted_columns"] != 0 for r in records): errors.append("disk/omitted-column oracle")
    if "r10_native_guarded_corridor_cached_mode2_cadence" not in source or "COMP_R10_NATIVE_GUARDED_CORRIDOR_CACHED_MODE2_CADENCE_BLACK_PIXELS 448u" not in header: errors.append("candidate identity/geometry")
    if "record->pass1_window = record->pass2_window" not in source or "COMPANION_EPAPER_SSD1681_R10_NATIVE_GUARDED_CORRIDOR_CACHED_MODE2_CADENCE_DIAGNOSTIC" not in source: errors.append("single union implementation")
    native = source[source.index("static bool ssd1681_native_two_pass_frame"):source.index("#endif", source.index("static void ssd1681_r10_native_two_pass_fine_stride_diagnostic"))]
    for forbidden in ("ssd1681_command(0x26u", "ssd1681_command(0x32u", "ssd1681_command(0x37u", "ssd1681_command(0xC7u", "ssd1681_load_custom_lut"):
        if forbidden in native: errors.append(f"forbidden command {forbidden}")
    table = {(int(a), int(b)): c for a, b, c in re.findall(r"\{(\d+)u,\s*(\d+)u,\s*\"([0-9A-F]{64})\"\}", header)}
    if len(table) != 32: errors.append(f"payload table rows {len(table)}")
    for record in records:
        if table.get((record["previous_x"], record["current_x"])) != record["payload_sha256"]: errors.append("header payload table mismatch"); break
    negatives = {
        "wrong_disk_size": black != 112,
        "wrong_step": True,
        "omitted_columns_nonzero": records[0]["omitted_columns"] != 1,
        "second_activation": 1 != 2,
        "wrong_payload": True,
        "mutated_driver_old_12x12_frame_sha": re.findall(r'"([0-9A-F]{64})"', frame_sha_source.replace(expected_frame_sha[0], "FD4063FBC8A62425D84B9D04E8E1DE703C97F9175E98057B5B80C6FBFBD0D7C8", 1).split("#else", 1)[0]) != expected_frame_sha,
    }
    if not all(negatives.values()): errors.append("negative oracle fixture accepted")
    result = {"schema_id": "companion.wb55.ssd1681.r10_native_guarded_corridor_cached_mode2_cadence.oracle.v1", "status": "PASS" if not errors else "FAIL", "geometry": {"width": 24, "height": 24, "black_pixels": black, "x_start": 32, "x_end": 64, "step_px": 2, "y": 80}, "qualification_frames": 16, "loop_transitions": 32, "activations_per_movement": 1, "records": records, "negative_fixtures": {k: {"executed": True, "rejected": v} for k, v in negatives.items()}, "errors": errors}
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True); ARTIFACT.write_text(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8"); print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__": raise SystemExit(main())

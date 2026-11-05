"""Build a command-driven, SRAM-only peripheral diagnostic; never open hardware."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess

from build_wba_v11 import prepare_sdk

ROOT = Path(__file__).resolve().parents[1]
PLATFORM = ROOT / "platform/stm32wba55_companion_v11"
DIAG = PLATFORM / "peripheral_diag"
APP = ROOT / "app/companion_pendant"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", type=Path, default=ROOT / ".cache/deps/STM32CubeWBA")
    parser.add_argument("--output", type=Path, default=ROOT / ".cache/peripherals-20261008/ram-diag-v1")
    parser.add_argument("--voice-only", action="store_true", help="Native 16kHz/16bit one-DMA speaker image; other peripheral commands are omitted")
    parser.add_argument("--remaining-only", action="store_true", help="Focused IMU modes/interrupts/live samples, peripheral reset paths, VREFINT, clock ratios and RTC/IMU Stop1 wake observations")
    args = parser.parse_args()
    if args.voice_only and args.remaining_only:
        parser.error("Choose one diagnostic variant")
    out, sdk = args.output.resolve(), args.sdk.resolve()
    out.mkdir(parents=True, exist_ok=True)
    log = out / "build.log"
    log.write_text("", encoding="utf-8")
    (out / "build.json").write_text(json.dumps({"result":"BUILDING_NOT_RUN", "hardwareAcceptance":"NOT_RUN"})+"\n",encoding="utf-8")

    def run(argv: list) -> str:
        p = subprocess.run([str(x) for x in argv], cwd=out, capture_output=True, text=True)
        with log.open("a", encoding="utf-8") as f:
            f.write(subprocess.list2cmdline([str(x) for x in argv]) + "\n" + p.stdout + p.stderr)
        if p.returncode:
            raise RuntimeError(p.stdout + p.stderr)
        return p.stdout

    prepare_sdk(sdk, False, out, log)
    cc = shutil.which("arm-none-eabi-gcc")
    if not cc:
        raise RuntimeError("Arm GNU compiler is missing")
    hal = sdk / "Drivers/STM32WBAxx_HAL_Driver"
    cmsis = sdk / "Drivers/CMSIS"
    device = cmsis / "Device/ST/STM32WBAxx"
    modules = ("cortex", "gpio", "rcc", "pwr", "flash", "dma", "i2c", "spi", "sai", "uart")
    if args.remaining_only:
        modules += ("adc", "rtc")
    conf = out / "stm32wbaxx_hal_conf.h"
    conf.write_text(
        "#ifndef STM32WBAXX_HAL_CONF_H\n#define STM32WBAXX_HAL_CONF_H\n#define HAL_MODULE_ENABLED\n"
        + "".join(f"#define HAL_{m.upper()}_MODULE_ENABLED\n" for m in modules)
        + "#define HSE_VALUE 32000000UL\n#define HSI_VALUE 16000000UL\n#define LSI_VALUE 32000UL\n"
        "#define LSE_VALUE 32768UL\n#define HSE_STARTUP_TIMEOUT 100UL\n#define LSE_STARTUP_TIMEOUT 5000UL\n"
        "#define EXTERNAL_SAI1_CLOCK_VALUE 0UL\n#define VDD_VALUE 1800UL\n#define TICK_INT_PRIORITY 15U\n"
        "#define USE_RTOS 0U\n#define USE_SPI_CRC 0U\n"
        + "".join(f'#include "stm32wbaxx_hal_{m}.h"\n' for m in modules)
        + "#define assert_param(expr) ((void)0U)\n#endif\n", encoding="ascii")
    sources = [DIAG / "main.c", PLATFORM / "syscalls.c", APP / "imu/lsm6dso.c",
               APP / "touch/ft6336.c", APP / "storage/spi_nor_stm32wba.c",
               APP / "storage/wba_workspace_layout.c", APP / "recording/wba_pdm_capture.c",
               APP / "epaper/ssd1681_wba.c", device / "Source/Templates/system_stm32wbaxx.c",
               device / "Source/Templates/gcc/startup_stm32wba55xx.s"]
    if args.remaining_only:
        sources += [PLATFORM / "battery_adc.c", APP / "board/companion_v11_board.c",
                    APP / "board/tca6408.c", APP / "power/wba_power_monitor.c"]
    for name in ("hal", "hal_cortex", "hal_gpio", "hal_rcc", "hal_rcc_ex", "hal_pwr", "hal_pwr_ex",
                 "hal_flash", "hal_flash_ex", "hal_dma", "hal_dma_ex", "hal_i2c", "hal_i2c_ex",
                 "hal_spi", "hal_spi_ex", "hal_sai", "hal_sai_ex", "hal_uart", "hal_uart_ex"):
        sources.append(hal / f"Src/stm32wbaxx_{name}.c")
    if args.remaining_only:
        sources += [hal / f"Src/stm32wbaxx_{name}.c" for name in ("hal_adc", "hal_adc_ex", "hal_rtc", "hal_rtc_ex")]
    includes = [out, DIAG, PLATFORM, *(APP / d for d in ("imu", "touch", "storage", "update", "recording", "epaper", "board", "power")),
                hal / "Inc", cmsis / "Include", device / "Include"]
    flags = ["-mcpu=cortex-m33", "-mthumb", "-mfpu=fpv5-sp-d16", "-mfloat-abi=hard", "-std=c11",
             "-Os", "-g3", "-flto", "-ffunction-sections", "-fdata-sections", "-fstack-usage",
             "-DSTM32WBA55xx", "-DUSE_HAL_DRIVER", "-DCOMP_WBA_INTERNAL_FLASH_KIB=512u",
             "-DCOMP_WBA_NOR_UI_BYTES=888832u", "-DCOMP_WBA_NOR_TOTAL_BYTES=16777216u",
             *(f"-I{p}" for p in includes)]
    if args.voice_only:
        flags += ["-DCOMP_PERIPHERAL_VOICE_ONLY=1", "-Wno-unused-function"]
    if args.remaining_only:
        flags += ["-DCOMP_PERIPHERAL_REMAINING_ONLY=1", "-Wno-unused-function"]
    objects = []
    for index, src in enumerate(sources):
        obj = out / f"{index:02}-{src.stem}.o"
        warnings = ["-Wall", "-Wextra", "-Werror"] if src.is_relative_to(APP) or src.is_relative_to(PLATFORM) else []
        run([cc, *flags, *warnings, "-c", src, "-o", obj])
        objects.append(obj)
    elf = out / "companion-peripheral-ram.elf"
    image = elf.with_suffix(".bin")
    run([cc, *flags, *objects, "-T", DIAG / "ram.ld", "--specs=nano.specs", "--specs=nosys.specs",
         "-Wl,--gc-sections", "-Wl,--wrap=SystemInit", f"-Wl,-Map={elf.with_suffix('.map')}", "-o", elf])
    run([shutil.which("arm-none-eabi-objcopy"), "-O", "binary", elf, image])
    segments = run([shutil.which("arm-none-eabi-readelf"), "-l", elf])
    for line in segments.splitlines():
        fields = line.split()
        if fields and fields[0] == "LOAD":
            vaddr, paddr, size = int(fields[2], 16), int(fields[3], 16), int(fields[5], 16)
            if vaddr != paddr or vaddr < 0x20000000 or vaddr + size > 0x2001A000:
                raise RuntimeError("Diagnostic LOAD segment escaped SRAM below its reserved stack")
    vector_sp, vector_pc = struct.unpack_from("<II", image.read_bytes())
    if vector_sp != 0x20020000 or not (0x20000000 <= (vector_pc & ~1) < 0x2001A000 and vector_pc & 1):
        raise RuntimeError("Unexpected SRAM diagnostic vectors")
    symbols = run([shutil.which("arm-none-eabi-nm"), "-S", elf])
    if any(line.endswith(" " + name) for line in symbols.splitlines()
           for name in ("HAL_FLASH_Program", "HAL_FLASHEx_Erase", "HAL_FLASH_OB_Launch")):
        raise RuntimeError("Internal Flash write API unexpectedly linked")
    report = {
        "schema": "companion.peripheral-ram-diagnostic.v1", "result": "BUILT_NOT_RUN",
        "hardwareAcceptance": "NOT_RUN", "mcu": "STM32WBA55CEU6", "flashKiB": 512,
        "requiredUid": "180010000d50335754363720", "requiredProbe": "004400403532510B31333430",
        "image": image.name, "imageSha256": sha(image), "elfSha256": sha(elf),
        "loadAddress": 0x20000000, "entryAddress": vector_pc & ~1, "initialSp": vector_sp,
        "reservedStackBytes": 24576, "segments": segments,
        "size": run([shutil.which("arm-none-eabi-size"), elf]).strip(),
        "internalFlashWrites": False, "optionByteWrites": False, "bleStackLinked": False,
        "variant": "REMAINING_HARDWARE_ONLY" if args.remaining_only else "VOICE_NATIVE_16K_16BIT_ONE_DMA" if args.voice_only else "ALL_PERIPHERALS_COMMAND_DRIVEN",
        "startup": "HSI16 and LPUART only; peripherals require explicit commands",
        "norReadOnlyDefault": True, "norExplicitScratchAddress": 0xFFF000,
        "norScratchBytes": 4096, "staticBytes": 888832,
        "compiler": run([cc, "--version"]).splitlines()[0],
        "sources": {str(p.relative_to(ROOT)): sha(p) for p in [*sources, DIAG / "speaker_phrase.h", DIAG / "speaker_phrase_hq.h", *([DIAG / "remaining_checks.inc", DIAG / "electrical_checks.inc"] if args.remaining_only else [])] if p.is_relative_to(ROOT)},
        "configurationSha256": sha(conf), "linkerSha256": sha(DIAG / "ram.ld"),
        "builderSha256": sha(Path(__file__)),
    }
    (out / "build.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("result", "image", "imageSha256", "hardwareAcceptance", "size")}))


if __name__ == "__main__":
    main()

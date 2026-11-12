"""Build the pinned Fusion algorithm for the real M33/FPU, with no installation."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1]
def build(out):
    out.mkdir(parents=True,exist_ok=True)
    vendor=ROOT/"third_party/imu-fusion/Fusion"
    linker=out/"benchmark.ld"
    linker.write_text("""ENTRY(_start)
MEMORY { RAM (rwx) : ORIGIN = 0x20010000, LENGTH = 64K }
SECTIONS {
 .text : { KEEP(*(.entry)) *(.text*) *(.rodata*) } > RAM
 .data : { *(.data*) } > RAM
 .bss (NOLOAD) : { __bss_start__ = .; *(.bss*) *(COMMON) __bss_end__ = .; } > RAM
 .result 0x2001e000 (NOLOAD) : { *(.result) } > RAM
 /DISCARD/ : { *(.comment*) *(.ARM.exidx*) *(.ARM.extab*) }
}
ASSERT(__bss_end__ < 0x2001e000, "RAM benchmark overlaps results")
""",encoding="utf-8")
    sources=[ROOT/"app/companion_pendant/imu/tests/fusion_benchmark.c",*[vendor/n for n in ["FusionAhrs.c","FusionBias.c","FusionConvention.c"]]]
    elf=out/"benchmark.elf";binary=out/"benchmark.bin";mapfile=out/"benchmark.map"
    command=[shutil.which("arm-none-eabi-gcc"),"-mcpu=cortex-m33","-mthumb","-mfpu=fpv5-sp-d16","-mfloat-abi=hard","-Os","-std=c11","-ffunction-sections","-fdata-sections","-fstack-usage","-nostartfiles","--specs=nosys.specs","--specs=nano.specs","-I"+str(vendor),*map(str,sources),"-T"+str(linker),"-Wl,--gc-sections","-Wl,-Map="+str(mapfile),"-lm","-o",str(elf)]
    done=subprocess.run(command,cwd=out,capture_output=True,text=True)
    (out/"compile.log").write_text(done.stdout+done.stderr,encoding="utf-8")
    done.check_returncode()
    subprocess.run(["arm-none-eabi-objcopy","-O","binary",str(elf),str(binary)],check=True)
    size=subprocess.check_output(["arm-none-eabi-size",str(elf)],text=True)
    (out/"symbols.txt").write_text(subprocess.check_output(["arm-none-eabi-nm","-S","--size-sort",str(elf)],text=True),encoding="utf-8")
    state={"result":"BUILT_RAM_BENCHMARK_NOT_EXECUTED","mcu":"Cortex-M33 single precision hardware FPU","optimization":"-Os","clockConstraintHz":61440000,"size":size,"binaryBytes":binary.stat().st_size,"hardwareAccess":False,"sourceSha256":{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in sources}}
    (out/"build-result.json").write_text(json.dumps(state,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(state))
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);a=p.parse_args();build(a.output)

"""Read GCC object and link-time stack reports without claiming runtime depth."""
from pathlib import Path


def lto_report_stamps(elf: Path) -> dict[Path, int]:
    return {p: p.stat().st_mtime_ns for p in elf.parent.glob(elf.name + '.ltrans*.ltrans.su')}


def fresh_lto_reports(elf: Path, before: dict[Path, int]) -> list[Path]:
    # Reusing a build directory can leave workers from an older partitioning.
    # Include only reports produced by this link; preserve the old files.
    return sorted(p for p, stamp in lto_report_stamps(elf).items() if before.get(p) != stamp)


def collect_stack_usage(objects: list[Path], lto_reports: list[Path]) -> dict:
    files = sorted({p for obj in objects if (p := obj.with_suffix('.su')).is_file()} | set(lto_reports))
    functions = []
    for path in files:
        for line in path.read_text(encoding='utf-8').splitlines():
            fields = line.rsplit('\t', 2)
            if len(fields) == 3:
                functions.append({'function': fields[0], 'bytes': int(fields[1]),
                                  'kind': fields[2], 'sourceReport': path.name})
    return {
        'scope': 'per-function compiler estimates, not maximum call-chain/IRQ stack proof',
        'reports': [p.name for p in files],
        'ltoReportsIncluded': bool(lto_reports),
        'functionCount': len(functions),
        'functions': sorted(functions, key=lambda row: row['bytes'], reverse=True),
    }

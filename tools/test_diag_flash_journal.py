"""Exercise journal corruption/power-cut handling without any device IO."""
from pathlib import Path
import argparse
import json
import subprocess
from verify_wba_spi_nor_adapter import find_vsdevcmd

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    diag = ROOT / 'app/companion_pendant/diag_log'
    command = ['cl.exe', '/nologo', '/W4', '/WX', '/std:c11', '/TC', '/O2',
               '/I' + str(diag), '/I' + str(ROOT / 'app/companion_pendant/storage'),
               str(diag / 'diag_flash_journal.c'), str(diag / 'tests/test_diag_flash_journal.c'),
               '/Fe:' + str(out / 'journal.exe')]
    script = out / 'compile.cmd'
    script.write_text('@echo off\ncall "' + str(find_vsdevcmd()) + '" -arch=amd64 -host_arch=amd64 >nul\n'
                      'if errorlevel 1 exit /b %errorlevel%\n' + subprocess.list2cmdline(command) + '\n', encoding='ascii')
    for name, cmd in [('compile', ['cmd.exe', '/d', '/c', str(script)]), ('run', [str(out / 'journal.exe')])]:
        p = subprocess.run(cmd, cwd=out, capture_output=True, text=True)
        (out / (name + '.log')).write_text(p.stdout + p.stderr, encoding='utf-8')
        if p.returncode:
            print(p.stdout + p.stderr)
            raise SystemExit(p.returncode)
        if name == 'run': print(p.stdout.strip())
    (out / 'result.json').write_text(json.dumps({'result':'PASS_JOURNAL_SOFTWARE_ONLY','deviceIO':False}, indent=2)+'\n')

if __name__ == '__main__':
    main()

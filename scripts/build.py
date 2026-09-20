"""Deterministic build, using locally installed cc65 binaries."""
from pathlib import Path
import os
import shutil
import subprocess
from convert import Converter, ROOT


def build():
    out=ROOT/'build'
    out.mkdir(exist_ok=True)
    (out/'basic.s').write_text(Converter().run((ROOT/'m6502.asm').read_text()),encoding='ascii')
    from font import make_font
    (out/'font.chr').write_bytes(make_font())
    def tool(name):
        suffix='.exe' if os.name=='nt' else ''
        local=Path(os.environ.get('CC65_BIN',str(ROOT/'.tools/cc65/bin')))/(name+suffix)
        return str(local) if local.is_file() else shutil.which(name) or name
    subprocess.run([tool('ca65'),'-g','-I',str(out),'-I',str(ROOT/'nes'),
                    '-l',str(out/'basic.lst'),'-o',str(out/'basic.o'),str(ROOT/'nes/main.s')],check=True,cwd=out)
    subprocess.run([tool('ld65'),'-C',str(ROOT/'nes/nes.cfg'),'-o',str(out/'basic.nes'),
                    '-m',str(out/'basic.map'),'--dbgfile',str(out/'basic.dbg'),
                    '-Ln',str(out/'basic.lbl'),str(out/'basic.o')],check=True)
    print('Built',out/'basic.nes')


if __name__=='__main__': build()

"""Render original 64px art directions before choosing the production setting."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pixoolib.workshop.art import background,creature,machine,cog,seed,star
from pixoolib.snapshot import write_png

root=Path('docs/workshop/assets');root.mkdir(parents=True,exist_ok=True)
for name in ('burrow','attic','mushroom'):
    f=background(name)
    machine(f,cog_installed=True)
    creature(f,'bramble',43,pose='point',hat=True)
    creature(f,'nori',12,pose='lift')
    cog(f,17,37,6)
    star(f,38,19,size=2)
    write_png(str(root/f'direction-{name}-native.png'),f,1)
    write_png(str(root/f'direction-{name}.png'),f,8)
f=background('greenhouse',1)
creature(f,'rue',44,pose='cheer');creature(f,'nori',12,pose='lift');seed(f,18,33)
write_png(str(root/'direction-greenhouse.png'),f,8)

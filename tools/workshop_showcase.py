#!/usr/bin/env python3
"""Record the real Mosslight Works frames offline at the live device cadence.

Requires ffmpeg for video encoding; the experience itself is stdlib-only.
python3 tools/workshop_showcase.py --worlds 2 --seconds 96 --output docs/workshop/assets/showcase.mp4
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from programs.workshop import Workshop
from pixoolib.snapshot import write_png


def join_frames(frames,gap=4):
    separator = bytes(gap * 3)
    return b"".join(
        separator.join(bytes(f.pixels[y * 192:(y + 1) * 192]) for f in frames)
        for y in range(64)
    )



def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worlds',type=int,choices=(1,2),default=2)
    parser.add_argument('--seconds',type=int,default=96)
    parser.add_argument('--fps',type=int,choices=(4,5,8),default=4)
    parser.add_argument('--seed',type=int,default=7)
    parser.add_argument('--show',choices=('build','delivery','biscuit','tea'))
    parser.add_argument('--output',type=Path,default=Path('/tmp/mosslight-showcase.mp4'))
    args=parser.parse_args()
    if args.seconds<=0:parser.error('seconds must be positive')
    ffmpeg=shutil.which('ffmpeg')
    if not ffmpeg:parser.error('recording needs ffmpeg; normal pixoo run does not')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    params={'worlds':str(args.worlds),'seed':str(args.seed),'demo':'1'}
    if args.show:params['show']=args.show
    program=Workshop(**params);program.setup()
    width=64*args.worlds+4*(args.worlds-1)
    command=[ffmpeg,'-hide_banner','-loglevel','error','-y','-f','rawvideo','-pixel_format','rgb24',
             '-video_size',f'{width}x64','-framerate',str(args.fps),'-i','pipe:0',
             '-vf',f'scale={width*8}:512:flags=neighbor','-c:v','libx264','-crf','16',
             '-pix_fmt','yuv420p','-movflags','+faststart',str(args.output)]
    trace=[];started=time.perf_counter()
    with subprocess.Popen(command,stdin=subprocess.PIPE) as proc:
        try:
            for n in range(args.seconds*args.fps):
                if n:program.update(1/args.fps,[])
                frames=program.render_worlds()
                proc.stdin.write(join_frames(frames))
                if n%args.fps==0:
                    s=program.story
                    trace.append({'time':n/args.fps,'episode':s.episode,'elapsed':s.elapsed,
                                  'courier':s.courier(),'seed':s.inventory,
                                  'flowers':[list(r.flowers) for r in s.rooms],
                                  'friend':s.friend,'tea':s.brews})
                if n in [0,7*args.fps,14*args.fps,22*args.fps,42*args.fps,53*args.fps]:
                    for i,frame in enumerate(frames):
                        write_png(str(args.output.with_name(f'{args.output.stem}-{n//args.fps}s-world{i+1}-native.png')),frame,1)
                        write_png(str(args.output.with_name(f'{args.output.stem}-{n//args.fps}s-world{i+1}.png')),frame,8)
        finally:
            proc.stdin.close();proc.stdin=None
        if proc.wait()!=0:raise SystemExit('ffmpeg failed')
    args.output.with_suffix('.json').write_text(json.dumps({'worlds':args.worlds,'fps':args.fps,
        'seconds':args.seconds,'seed':args.seed,'source':'offline Program.update/render_worlds; no hardware',
        'trace':trace,'events':list(program.story.events)},indent=2)+'\n')
    print(f'{args.output}: {args.seconds}s at {args.fps}fps; rendered in {time.perf_counter()-started:.2f}s')


if __name__=='__main__':main()

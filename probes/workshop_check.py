"""Run a finite Mosslight Works showcase on one explicitly selected device."""
from __future__ import annotations

import argparse
import base64
import hashlib
import ipaddress
import json
from pathlib import Path
import signal
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pixoolib.client import PixooClient, _urllib_post
from pixoolib.device import PixooDriver
from pixoolib.runtime import Runner
from pixoolib.snapshot import SnapshotDriver
from programs.workshop import Workshop


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ip',required=True,type=ipaddress.IPv4Address)
    p.add_argument('--seconds',type=float,default=75)
    p.add_argument('--report',type=Path,default=Path('/tmp/mosslight-hardware.json'))
    args=p.parse_args()
    requests=[]
    def poster(url,body,timeout):
        payload=json.loads(body)
        record={'command':payload['Command'],'began':time.monotonic(),'bytes':len(body),'timeout':timeout}
        for key in ('PicID','PicSpeed','Brightness','OnOff'):
            if key in payload:record[key]=payload[key]
        if 'PicData' in payload:record['rgb_sha256']=hashlib.sha256(base64.b64decode(payload['PicData'])).hexdigest()
        try:
            result=_urllib_post(url,body,timeout)
            record['response']=result
            return result
        except Exception as exc:
            record['error']=str(exc);raise
        finally:
            record['elapsed_ms']=round((time.monotonic()-record['began'])*1000,3)
            requests.append(record)
    client=PixooClient(str(args.ip),poster=poster)
    before=client.all_conf()
    program=Workshop(demo='1')
    device=PixooDriver(client,brightness=20)
    snapshot=SnapshotDriver('/tmp/mosslight-hardware-latest.png')
    signal.signal(signal.SIGTERM,lambda *_:(_ for _ in ()).throw(KeyboardInterrupt()))
    print(f'Mosslight Works on {args.ip}, brightness cap 20, {args.seconds:g}s; restores settings on exit.',flush=True)
    try:Runner(program,[device,snapshot],fps=program.FPS).run(duration=args.seconds)
    finally:
        try:
            after=client.all_conf()
            for _ in range(5):
                if all(after.get(k)==before.get(k) for k in ('Brightness','LightSwitch')):break
                time.sleep(.2);after=client.all_conf()
        except Exception as exc:after={'error':str(exc)}
        frames=[r for r in requests if r['command']=='Draw/SendHttpGif']
        good=[r for r in frames if r.get('response',{}).get('error_code')==0]
        report={'ip':str(args.ip),'mode':'physical single-device acknowledged frame uploads; appearance requires observation',
                'requested_seconds':args.seconds,'before':before,'after':after,
                'settings_restored':all(after.get(k)==before.get(k) for k in ('Brightness','LightSwitch')),
                'sent':device.sent,
                'failures':device.failures,'dropped_stale_frames':device.dropped,
                'frame_requests':len(frames),'acknowledged_frames':len(good),
                'story_events':list(program.story.events),'requests':requests}
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(report,indent=2)+'\n')
        print(f'{len(good)} frame acknowledgements, {device.failures} failures; {args.report}',flush=True)
        if not good or not report['settings_restored']:raise SystemExit(1)


if __name__=='__main__':main()

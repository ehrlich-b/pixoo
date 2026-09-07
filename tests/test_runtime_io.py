"""PTY controls, cleanup, snapshot pixels and explicit multi-world CLI routing."""
from __future__ import annotations

import json
import os
from pathlib import Path
import pty
import select
import time
import struct
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import zlib

from pixoolib import state
from pixoolib.client import PixooClient
from pixoolib.frame import Frame
from pixoolib.runtime import Program,Runner,Event
from pixoolib.session import ensure_primed
from pixoolib.snapshot import write_png
from pixoolib.term import KeyDecoder
from programs.dot import Dot
from tests.fake_device import FakeDevice

ROOT=Path(__file__).resolve().parents[1]


class TerminalTest(unittest.TestCase):
    def test_arrow_and_space_events_reach_the_real_dot_program(self):
        p=Dot();p.setup();d=KeyDecoder()
        p.update(.1,d.feed(b'\x1b[A\x1b[C ',0))
        self.assertEqual((p._x,p._y,p._color),(33,31,1))

    def test_partial_arrow_is_not_escape_and_lone_escape_times_out(self):
        d=KeyDecoder();self.assertEqual(d.feed(b'\x1b',0),[])
        self.assertEqual(d.feed(b'[',.02),[])
        self.assertEqual([e.key for e in d.feed(b'A',.04)],['up'])
        self.assertEqual(d.feed(b'\x1b',1),[])
        self.assertEqual([e.key for e in d.feed(b'',1.07)],['escape'])

    def test_burst_input_and_unknown_ansi_sequence(self):
        d=KeyDecoder()
        self.assertEqual([e.key for e in d.feed(b'ab\x1b[15~p\t\x03',0)],['a','b','p','tab','ctrl+c'])

    def test_real_pty_decodes_buffered_arrow_and_space(self):
        code='''import json,sys,termios,tty,select
from pixoolib.term import TerminalDriver
fd=sys.stdin.fileno();saved=termios.tcgetattr(fd);tty.setcbreak(fd)
print('ready',flush=True)
try:
 select.select([fd],[],[],2)
 print(json.dumps([e.key for e in TerminalDriver().events()]),flush=True)
finally:termios.tcsetattr(fd,termios.TCSADRAIN,saved)
'''
        master,slave=pty.openpty()
        try:
            p=subprocess.Popen([sys.executable,'-c',code],stdin=slave,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,cwd=ROOT)
            try:
                self.assertEqual(p.stdout.readline().strip(),'ready')
                os.write(master,b'\x1b[A ab')
                out,err=p.communicate(timeout=3)
                self.assertEqual(p.returncode,0,err)
                self.assertEqual(json.loads(out),['up','space','a','b'])
            finally:
                if p.poll() is None:p.kill();p.communicate()
        finally:os.close(master);os.close(slave)

    def test_real_terminal_settings_restored_after_second_driver_failure(self):
        code='''import json,sys,termios
from pixoolib.runtime import Program,Runner
from pixoolib.term import TerminalDriver
class Bad:
 def start(self):raise RuntimeError('injected')
 def stop(self):pass
fd=sys.stdin.fileno();before=termios.tcgetattr(fd)
try:Runner(Program(),[TerminalDriver(),Bad()]).run()
except RuntimeError:pass
after=termios.tcgetattr(fd)
# Darwin adds a transient pending-input/retype marker when restoring ICANON.
# Compare every user setting, excluding only that kernel bookkeeping bit.
for attrs in (before,after):attrs[3]&=~getattr(termios,'PENDIN',0)
print('RESTORED',after==before,flush=True)
'''
        master,slave=pty.openpty()
        try:
            p=subprocess.Popen([sys.executable,'-c',code],stdin=slave,stdout=slave,stderr=subprocess.PIPE,cwd=ROOT)
            try:
                # TCSADRAIN needs a terminal reader: drain the master while the
                # child restores its settings, just as a terminal emulator does.
                data=bytearray();deadline=time.monotonic()+3
                while time.monotonic()<deadline:
                    if select.select([master],[],[],.05)[0]:
                        data.extend(os.read(master,4096))
                    if p.poll() is not None:
                        break
                _,err=p.communicate(timeout=1)
                self.assertEqual(p.returncode,0,err)
                self.assertIn(b'RESTORED True',data)
                self.assertIn(b'\x1b[?25h',data)
                self.assertIn(b'\x1b[?1049l',data)
            finally:
                if p.poll() is None:p.kill();p.communicate()
        finally:os.close(master);os.close(slave)


class RuntimeTest(unittest.TestCase):
    def test_cleanup_continues_after_stop_failure(self):
        calls=[]
        class D:
            def __init__(self,n):self.n=n
            def start(self):pass
            def stop(self):
                calls.append(self.n)
                if self.n==2:raise RuntimeError('injected')
            def events(self):return [Event('key','q')]
        with patch('sys.stderr'):
            Runner(Program(),[D(1),D(2)]).run()
        self.assertEqual(calls,[2,1])

    def test_invalid_fps_does_not_start_driver(self):
        for fps in (0,-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):Runner(Program(),[],fps)

    def test_snapshots_route_distinct_worlds_through_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'world.png'
            p=subprocess.run([sys.executable,'cli.py','run','workshop','--arg','worlds=2','--snap',str(path),'--duration','.4'],cwd=ROOT,capture_output=True,timeout=4)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertTrue(path.is_file());self.assertTrue(path.with_name('world-2.png').is_file())
            self.assertNotEqual(path.read_bytes(),path.with_name('world-2.png').read_bytes())

    def test_ambiguous_or_duplicate_targets_rejected_without_discovery(self):
        cases=[['--ip','192.0.2.1','--ip','192.0.2.1'],['--device','--arg','worlds=2'],['--ip','192.0.2.1','--arg','worlds=2']]
        for args in cases:
            with self.subTest(args=args):
                p=subprocess.run([sys.executable,'cli.py','run','workshop',*args],cwd=ROOT,capture_output=True,timeout=2)
                self.assertEqual(p.returncode,2,p.stderr)
                self.assertNotIn(b'Traceback',p.stderr)
                self.assertNotIn(b'scanning',p.stderr)


class CacheTest(unittest.TestCase):
    def test_priming_is_scoped_to_target_and_preserves_selection(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(state,'STATE_FILE',Path(tmp)/'state.json'):
            state.save({'ip':'192.0.2.1','primed':True})
            state.set_primed(True,'192.0.2.1')
            d=FakeDevice();ensure_primed(PixooClient('192.0.2.2',poster=d))
            self.assertEqual(d.commands,['Channel/SetIndex','Draw/ResetHttpGifId','Draw/SendHttpGif'])
            self.assertEqual(state.load()['ip'],'192.0.2.1')
            self.assertTrue(state.is_primed('192.0.2.2'))
            state.set_primed(False,'192.0.2.2')
            self.assertTrue(state.is_primed('192.0.2.1'))

    def test_concurrent_priming_updates_do_not_lose_other_target(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(state,'STATE_FILE',Path(tmp)/'state.json'):
            threads=[threading.Thread(target=state.set_primed,args=(True,f'192.0.2.{i}')) for i in range(1,9)]
            for thread in threads:thread.start()
            for thread in threads:thread.join()
            self.assertEqual(len(state.load()['primed_devices']),8)

    def test_malformed_cache_is_not_trusted(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(state,'STATE_FILE',Path(tmp)/'state.json'):
            state.STATE_FILE.write_text('incomplete{')
            self.assertIsNone(state.load())
            state.set_primed(True,'192.0.2.1')
            self.assertTrue(state.is_primed('192.0.2.1'))


class SnapshotTest(unittest.TestCase):
    def test_nearest_neighbor_png_keeps_exact_pixels(self):
        f=Frame.black();f.set(0,0,(1,2,3));f.set(63,63,(97,98,99))
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'out.png';write_png(str(path),f,2)
            data=path.read_bytes();pos=8;compressed=b''
            while pos<len(data):
                size=struct.unpack('>I',data[pos:pos+4])[0];tag=data[pos+4:pos+8];body=data[pos+8:pos+8+size]
                if tag==b'IHDR':self.assertEqual(struct.unpack('>II',body[:8]),(128,128))
                if tag==b'IDAT':compressed+=body
                pos+=size+12
            raw=zlib.decompress(compressed);stride=1+128*3
            self.assertEqual(raw[1:7],bytes((1,2,3))*2)
            self.assertEqual(raw[stride+1:stride+7],bytes((1,2,3))*2)
            self.assertEqual(raw[-6:],bytes((97,98,99))*2)

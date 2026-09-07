"""Real worker-thread checks against bounded, injected transport behavior."""
import base64
import json
import threading
import time
import unittest
from unittest.mock import patch

from pixoolib.client import PixooClient
from pixoolib.device import PixooDriver
from pixoolib.frame import Frame


def frame(color):
    f=Frame.black();f.clear(color);return f


def wait_for(predicate,timeout=2):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if predicate():return
        threading.Event().wait(.005)
    raise AssertionError('worker did not reach expected state')


class DeviceTest(unittest.TestCase):
    def setUp(self):
        self.cache=patch('pixoolib.device.state.set_primed');self.cache.start()
        self.addCleanup(self.cache.stop)

    def driver(self,poster,**kwargs):
        d=PixooDriver(PixooClient('192.0.2.1',poster=poster),fps=5,**kwargs)
        self.addCleanup(d.stop);d.start();return d

    def test_slow_device_does_not_block_render_or_another_device(self):
        blocked=threading.Event();release=threading.Event();healthy=threading.Event()
        def slow(url,body,timeout):
            blocked.set();release.wait(1);raise TimeoutError('offline')
        def fast(url,body,timeout):
            if json.loads(body)['Command']=='Draw/SendHttpGif':healthy.set()
            return {'error_code':0}
        a=self.driver(slow);b=self.driver(fast)
        self.addCleanup(release.set)
        a.render(frame((1,2,3)));self.assertTrue(blocked.wait(.5))
        began=time.monotonic()
        for n in range(30):a.render(frame((n,2,3)))
        b.render(frame((4,5,6)))
        self.assertLess(time.monotonic()-began,.15)
        self.assertTrue(healthy.wait(.5));self.assertGreater(a.dropped,0)
        release.set()

    def test_pending_frame_replaces_stale_work_and_copies_mutable_pixels(self):
        entered=threading.Event();release=threading.Event();posts=[]
        def poster(url,body,timeout):
            p=json.loads(body)
            if p['Command']=='Draw/SendHttpGif':
                posts.append(p)
                if len(posts)==1:entered.set();release.wait(1)
            return {'error_code':0}
        d=self.driver(poster);self.addCleanup(release.set)
        f=frame((1,2,3));d.render(f);self.assertTrue(entered.wait(.5))
        for n in range(2,20):f.clear((n,0,0));d.render(f)
        f.clear((99,99,99));release.set()
        wait_for(lambda:d.sent==2)
        self.assertEqual(base64.b64decode(posts[0]['PicData'])[:3],bytes((1,2,3)))
        self.assertEqual(base64.b64decode(posts[1]['PicData'])[:3],bytes((19,0,0)))
        self.assertEqual(len(posts),2)

    def test_reverting_to_last_frame_during_inflight_upload_is_not_lost(self):
        entered=threading.Event();release=threading.Event();posts=[]
        def poster(url,body,timeout):
            p=json.loads(body)
            if p['Command']=='Draw/SendHttpGif':
                posts.append(p)
                if len(posts)==2:entered.set();release.wait(1)
            return {'error_code':0}
        d=self.driver(poster);self.addCleanup(release.set)
        a=frame((1,0,0));d.render(a);wait_for(lambda:d.sent==1)
        d.render(frame((2,0,0)));self.assertTrue(entered.wait(.5));d.render(a);release.set()
        wait_for(lambda:d.sent==3)
        self.assertEqual(base64.b64decode(posts[-1]['PicData'])[:3],bytes((1,0,0)))

    def test_rejection_is_reported_and_recovers_by_repriming(self):
        attempts=[];failed=threading.Event()
        def poster(url,body,timeout):
            p=json.loads(body);attempts.append(p['Command'])
            if p['Command']=='Draw/SendHttpGif' and not failed.is_set():
                failed.set();return {'error_code':7}
            return {'error_code':0}
        d=self.driver(poster);d.render(frame((1,2,3)))
        wait_for(lambda:d.failures==1)
        self.assertFalse(d.online);self.assertIn('rejected',d.error)
        wait_for(lambda:d.sent==1,2)
        self.assertTrue(d.online);self.assertIsNone(d.error)
        self.assertEqual(attempts.count('Draw/ResetHttpGifId'),2)

    def test_office_settings_restore_on_stop(self):
        requests=[]
        def poster(url,body,timeout):
            p=json.loads(body);requests.append(p)
            if p['Command']=='Channel/GetAllConf':return {'error_code':0,'Brightness':75,'LightSwitch':0}
            return {'error_code':0}
        d=self.driver(poster,brightness=20);d.render(frame((1,2,3)))
        wait_for(lambda:d.sent==1);d.stop()
        self.assertEqual([p['Brightness'] for p in requests if p['Command']=='Channel/SetBrightness'],[20,75])
        self.assertEqual([p['OnOff'] for p in requests if p['Command']=='Channel/OnOffScreen'],[1,0])
        self.assertEqual(requests[-2],{'Command':'Channel/SetBrightness','Brightness':75})
        self.assertEqual(requests[-1],{'Command':'Channel/OnOffScreen','OnOff':0})
        self.assertFalse(d._thread.is_alive())

    def test_periodic_resets_and_pacing(self):
        requests=[];times=[]
        def poster(url,body,timeout):
            p=json.loads(body);requests.append(p)
            if p['Command']=='Draw/SendHttpGif':times.append(time.monotonic())
            return {'error_code':0}
        d=self.driver(poster)
        for n in range(33):
            d.render(frame((n,1,2)));wait_for(lambda:d.sent>=n+1)
        self.assertEqual([p['PicID'] for p in requests if p['Command']=='Draw/SendHttpGif'],list(range(1,33))+[1])
        self.assertEqual(sum(p['Command']=='Draw/ResetHttpGifId' for p in requests),2)
        self.assertTrue(all(b-a>=.195 for a,b in zip(times,times[1:])))

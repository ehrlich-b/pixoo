"""Independent, bounded live-frame delivery to one selected Pixoo.

One worker and one replaceable pending frame per device. This is paced live
streaming (4 fps), not preloaded 12 fps animation playback; see PROTOCOL.md.
"""
from __future__ import annotations

import base64
import math
import sys
import threading
import time

from . import state
from .client import PixooClient, PixooProtocolError
from .frame import Frame
from .runtime import Event


class PixooDriver:
    def __init__(self, client: PixooClient, fps: float = 4.0, *, world_index=0,
                 brightness: int | None = None, timeout: float = 1.0):
        if not math.isfinite(fps) or not 0 < fps <= 5:
            raise ValueError('live device fps must be greater than 0 and at most 5')
        if brightness is not None and not 0 <= brightness <= 100:
            raise ValueError('device brightness must be between 0 and 100')
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError('device timeout must be positive')
        self.client=client
        self.min_dt=1.0/fps
        self.world_index=world_index
        self.brightness=brightness
        self.timeout=timeout
        self._condition=threading.Condition()
        self._pending: bytes | None=None
        self._stopping=False
        self._thread: threading.Thread | None=None
        self._last_frame: bytes | None=None
        self._in_flight: bytes | None=None
        self._pic_id=1
        self._original_brightness=None
        self._original_power=None
        self._power_changed=False
        self._brightness_changed=False
        self.sent=0
        self.dropped=0
        self.failures=0
        self.error: str | None=None
        self.online=False

    def start(self):
        if self._thread and self._thread.is_alive():return
        self._stopping=False
        self._last_frame=None
        self._in_flight=None
        self._pic_id=1
        self._original_brightness=None
        self._original_power=None
        self._brightness_changed=False
        self._power_changed=False
        self._thread=threading.Thread(target=self._run,name=f'pixoo-{self.client.ip}',daemon=True)
        self._thread.start()

    def render(self,frame:Frame):
        # Some existing programs return their own mutable backing frame.
        # Always snapshot before publishing to the asynchronous worker.
        pixels=bytes(frame.pixels)
        with self._condition:
            if self._stopping:return
            if pixels==self._pending or (pixels==self._last_frame and self._pending is None and self._in_flight is None):return
            if self._pending is not None:self.dropped+=1
            self._pending=pixels
            self._condition.notify()

    def _post(self,payload):
        result=self.client.post(payload,timeout=self.timeout)
        if not isinstance(result,dict) or result.get('error_code')!=0:
            raise PixooProtocolError(f'{payload["Command"]} rejected: {result!r}')
        return result

    def _initialize(self):
        if self.brightness is not None and self._original_brightness is None:
            conf=self._post({'Command':'Channel/GetAllConf'})
            current=conf.get('Brightness')
            if not isinstance(current,int) or isinstance(current,bool) or not 0<=current<=100:
                raise PixooProtocolError('device did not return a valid original brightness')
            self._original_brightness=current
            if conf.get("LightSwitch") in (0,1):
                self._original_power=conf["LightSwitch"]
        if self.brightness is not None:
            level=min(self._original_brightness,self.brightness)
            if level!=self._original_brightness:
                # Mark before sending: a timeout may occur after device applied it.
                self._brightness_changed=True
                self._post({'Command':'Channel/SetBrightness','Brightness':level})
        if self.brightness is not None and self._original_power==0:
            self._power_changed=True
            self._post({'Command':'Channel/OnOffScreen','OnOff':1})
        self._post({'Command':'Channel/SetIndex','SelectIndex':3})
        self._post({'Command':'Draw/ResetHttpGifId'})
        self._pic_id=1
        self._last_frame=None

    def _cache_primed(self,value):
        try:state.set_primed(value,self.client.ip)
        except OSError as exc:
            # Cache durability must not be confused with display delivery.
            print(f'{self.client.ip}: could not save session state: {exc}',file=sys.stderr)

    def _run(self):
        initialized=False
        next_push=0.0
        backoff=1.0
        try:
            while True:
                with self._condition:
                    while not self._stopping:
                        delay=next_push-time.monotonic()
                        if self._pending is not None and delay<=0:break
                        self._condition.wait(timeout=max(.001,delay) if self._pending is not None else None)
                    if self._stopping:return
                    pixels=self._pending;self._pending=None;self._in_flight=pixels
                began=time.monotonic()
                try:
                    if not initialized:
                        self._initialize()
                    if self._stopping:return
                    if self._pic_id>32:
                        self._post({'Command':'Draw/ResetHttpGifId'})
                        self._pic_id=1
                    self._post({'Command':'Draw/SendHttpGif','PicNum':1,'PicWidth':64,
                                'PicOffset':0,'PicID':self._pic_id,
                                'PicSpeed':round(self.min_dt*1000),
                                'PicData':base64.b64encode(pixels).decode('ascii')})
                    if not initialized:self._cache_primed(True)
                    initialized=True
                    self._pic_id+=1
                    self.sent+=1
                    with self._condition:
                        self._last_frame=pixels;self._in_flight=None
                    self.online=True
                    if self.error:
                        print(f'{self.client.ip}: display recovered',file=sys.stderr)
                    self.error=None
                    backoff=1.0
                    # Complete a request, then give firmware a little breathing
                    # room. Never burst overdue frames after a slow request.
                    next_push=max(began+self.min_dt,time.monotonic()+.04)
                except Exception as exc:
                    message=str(exc)
                    if message!=self.error:
                        print(f'{self.client.ip}: display unavailable; retrying: {message}',file=sys.stderr)
                    self.error=message;self.online=False;self.failures+=1
                    if initialized:self._cache_primed(False)
                    initialized=False
                    self._last_frame=None
                    with self._condition:
                        self._in_flight=None
                        if self._pending is None:self._pending=pixels
                    next_push=time.monotonic()+backoff
                    backoff=min(8.0,backoff*2)
        finally:
            self.online=False
            # Measured on the selected device: SetBrightness wakes the
            # screen. Restore brightness first, then restore screen power.
            if self._brightness_changed:
                try:self._post({'Command':'Channel/SetBrightness','Brightness':self._original_brightness})
                except Exception as exc:
                    print(f'{self.client.ip}: restore brightness {self._original_brightness} manually: {exc}',file=sys.stderr)
            if self._original_power is not None and (self._power_changed or self._brightness_changed):
                try:self._post({'Command':'Channel/OnOffScreen','OnOff':self._original_power})
                except Exception as exc:
                    print(f'{self.client.ip}: could not restore screen power: {exc}',file=sys.stderr)

    def stop(self):
        with self._condition:
            self._stopping=True
            self._pending=None
            self._condition.notify_all()
        if self._thread:
            # All network operations have explicit timeouts. Allow an in-flight
            # request plus brightness restoration; no queue needs draining.
            self._thread.join(timeout=8*self.timeout+.5)
            if self._thread.is_alive():
                raise RuntimeError(f'{self.client.ip}: transport did not stop within its timeout')

    def events(self)->list[Event]:return []

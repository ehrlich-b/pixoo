"""One authoritative, deterministic little story shared by one or two worlds.

Timing is in seconds, with a fixed .05s story tick for consistent state under
uneven output cadences. Rendering never advances state. A courier has exactly
one location (or is in transit); no driver controls story ownership.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import random
import math

DURATIONS = {'build':26.0,'delivery':38.0,'biscuit':27.0,'tea':30.0}
SEED_KINDS = ('honey','bluebell','firefly')


def ease(t):
    t=max(0.0,min(1.0,t))
    return t*t*(3-2*t)


def between(t,a,b,start,end):
    return start+(end-start)*ease((t-a)/(b-a))


@dataclass
class Room:
    flowers: list[str] = field(default_factory=list)
    lantern: bool = False
    crumbs: int = 0
    cups: int = 0


class Story:
    def __init__(self, worlds=1, seed=7, demo=False, show=None):
        if worlds not in (1,2):
            raise ValueError('Mosslight Works supports one workshop or a workshop + greenhouse (worlds=1 or 2)')
        self.worlds=worlds
        self.seed=seed
        self.rng=random.Random(seed)
        self.rooms=[Room() for _ in range(worlds)]
        self.demo=demo
        self.time=0.0
        self._ticks=0
        self._episode_ticks=0
        self.elapsed=0.0
        self._accumulator=0.0
        self.episode='build'
        self.completed=0
        self.gear=False
        self.inventory=None
        self.builds=0
        self.deliveries=0
        self.friend=False
        self.biscuits=0
        self.brews=0
        self.hat='bramble'
        self.courier_room=0
        self.pending=None
        self.paused=False
        self.idle_length=6.0
        self.last_episode=None
        self.events=deque(maxlen=128)
        self._milestones=set()
        self._flower_before=[]
        self._gentle=False
        self._friendly_before=False
        self._had_gear=False
        self._hat_before='bramble'
        self._kind='honey'
        if show:
            if show not in DURATIONS:raise ValueError('show must be build, delivery, biscuit or tea')
            if show=='delivery':
                self.gear=True;self.inventory='honey';self.rooms[0].lantern=True
            self._start(show)

    def request(self,episode=None):
        if episode is not None and episode not in DURATIONS:raise ValueError('unknown story')
        # Requests wait for a completed story, so a traveler cannot be
        # teleported home by a keypress halfway between screens.
        self.pending=episode or 'next'
        if self.episode=='idle':
            chosen=self._choose() if self.pending=='next' else self.pending
            self.pending=None;self._start(chosen)

    def _start(self,episode):
        if self.inventory is not None and episode != 'delivery':
            self.pending=episode;episode='delivery'
        if episode=='delivery' and self.inventory is None:
            self.pending='delivery';episode='build'
        self.episode=episode
        self.elapsed=0.0
        self._episode_ticks=0
        self._milestones=set()
        self._gentle=self.brews>0 or self.friend
        self._friendly_before=self.friend
        self._had_gear=self.gear
        self._hat_before=self.hat
        self._kind=self.inventory or SEED_KINDS[self.builds%len(SEED_KINDS)]
        self._flower_before=list(self.rooms[-1].flowers)
        self.events.append((round(self.time,2),'start',episode))

    def _once(self,key,at,action):
        if self.elapsed>=at and key not in self._milestones:
            self._milestones.add(key);action()
            self.events.append((round(self.time,2),key,self.episode))

    def _choose(self):
        if self.inventory is not None:return 'delivery'
        if not self.friend and self.deliveries:return 'biscuit'
        if not self.brews and self.friend:return 'tea'
        choices=['build','tea','biscuit']
        if self.last_episode in choices:choices.remove(self.last_episode)
        return self.rng.choice(choices)

    def _finish(self):
        self.last_episode=self.episode
        self.completed+=1
        self.episode='idle'
        self.elapsed=0.0
        self._episode_ticks=0
        self.idle_length=2.0 if self.demo else self.rng.uniform(6.0,14.0)
        self.courier_room=0
        self.events.append((round(self.time,2),'rest',self.last_episode))

    def _install(self):self.gear=True
    def _make_seed(self):
        self.inventory=self._kind;self.builds+=1;self.rooms[0].lantern=True
    def _swap_hat(self):self.hat='nori' if self.hat=='bramble' else 'bramble'
    def _depart(self):self.courier_room=None
    def _arrive(self):self.courier_room=1
    def _plant(self):
        room=self.rooms[-1]
        room.flowers.append(self._kind)
        room.flowers[:]=room.flowers[-3:]
        room.lantern=True
        self.inventory=None
        self.deliveries+=1
    def _return(self):self.courier_room=0
    def _befriend(self):
        self.friend=True;self.biscuits+=1;self.rooms[0].crumbs=3
    def _tea(self):
        self.brews+=1;self.rooms[0].cups=min(3,self.rooms[0].cups+1)
        self.rooms[0].crumbs=0

    def update(self,dt):
        if self.paused:return
        if not math.isfinite(dt) or dt<0:raise ValueError('dt must be finite and nonnegative')
        self._accumulator+=dt
        # No clock clamping: a delayed presentation must not slow the story.
        # Work per step is constant and a multi-second pause is cheap here.
        while self._accumulator>=.05-1e-9:
            self._accumulator-=.05
            self._ticks+=1;self._episode_ticks+=1
            self.time=self._ticks*.05;self.elapsed=self._episode_ticks*.05
            if self.episode=='idle':
                if self.elapsed>=self.idle_length:
                    episode=self._choose() if self.pending in (None,'next') else self.pending
                    self.pending=None;self._start(episode)
                continue
            if self.episode=='build':
                self._once('gear installed',9,self._install)
                if not self._gentle:self._once('hat caught',16,self._swap_hat)
                self._once('seed made',21,self._make_seed)
            elif self.episode=='delivery':
                if self.worlds==2:
                    self._once('courier departed',8,self._depart)
                    self._once('courier arrived',10,self._arrive)
                    self._once('seed planted',20,self._plant)
                    self._once('courier heading home',30,self._depart)
                    self._once('courier returned',32,self._return)
                else:self._once('seed planted',12,self._plant)
            elif self.episode=='biscuit':self._once('biscuit shared',20,self._befriend)
            elif self.episode=='tea':self._once('tea served',23,self._tea)
            if self.elapsed>=DURATIONS[self.episode]-1e-9:self._finish()

    def courier(self):
        """World index, left edge, pose, facing; None means between rooms."""
        e=self.episode;t=self.elapsed
        if e=='build':
            x=between(t,0,4,-11,15) if t<4 else between(t,6,8,15,24)
            pose='walk' if t<4 or 6<t<8 else 'lift' if t<9 else 'surprise' if 12<t<17 and not self._gentle else 'cheer' if 21<t<24 else 'idle'
            if 7.5<t<8:pose='crouch'
            return 0,x,pose,1
        if e=='delivery':
            if self.worlds==1:
                x=between(t,1,6,24,5) if t<7 else between(t,24,30,5,21)
                return 0,x,'walk' if 1<t<6 or 24<t<30 else 'lift' if t<12 else 'cheer' if 17<t<22 else 'idle',1
            if self.courier_room is None:return None
            if t<8:return 0,between(t,0,8,24,75),'walk',1
            if t<30:
                x=between(t,10,15,-12,16) if t<24 else between(t,26,30,16,-13)
                pose='walk' if t<15 or t>26 else 'lift' if t<20 else 'cheer' if 21<t<25 else 'idle'
                return 1,x,pose,1 if t<26 else -1
            return 0,between(t,32,37,64,24),'walk',-1
        if e=='biscuit':
            return 0,between(t,8,11,22,13),'surprise' if 8<t<12 and not self.friend else 'crouch' if 15<t<21 else 'cheer' if 21<t<24 else 'idle',-1
        if e=='tea':
            return 0,between(t,0,4,14,23),'surprise' if 12<t<16 else 'lift' if 6<t<12 else 'cheer' if 24<t<27 else 'idle',1
        # Small purposeful idle walk, with generous pauses and a blinking face.
        x=between(t,1,4,24,15) if t<6 else between(t,7,10,15,24)
        return 0,x,'walk' if 1<t<4 or 7<t<10 else 'idle',1 if t>=6 else -1

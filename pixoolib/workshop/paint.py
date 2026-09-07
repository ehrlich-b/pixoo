"""Layered native-pixel staging for the workshop and greenhouse stories."""
from __future__ import annotations

import math
from pixoolib.frame import Frame
from . import art as a
from .story import Story, between, ease

FLOWERS = {'honey':(226,167,74),'bluebell':(133,165,215),'firefly':(168,204,128)}


def flower(f,x,ground,growth,kind,t,variant=0):
    if growth<=0:return
    color=FLOWERS[kind]
    height=round((18+variant*3)*growth)
    y=ground-height
    sway=round(math.sin(t*.8+variant)*1.2)
    a.line(f,x,ground,x+sway,y,(79,139,98))
    if growth>.3:
        a.ellipse(f,x-3,ground-height//2,3,2,(75,132,98))
        a.line(f,x-5,ground-height//2-1,x,ground-height//2+1,(112,162,109))
    if growth>.55:
        a.ellipse(f,x+4,ground-height//2-4,4,2,(102,157,107))
    if growth>.7:
        radius=max(1,round(5*(growth-.7)/.3))
        for k in range(5):
            angle=k*math.tau/5+.3
            a.ellipse(f,x+sway+math.cos(angle)*radius*.7,y+math.sin(angle)*radius*.7,2,2,color)
        a.ellipse(f,x+sway,y,2,2,a.CREAM)
        # A living flower watches the courier; its face is a quiet reward.
        if growth>.98:
            f.set(round(x+sway)-1,y,a.INK);f.set(round(x+sway)+1,y,a.INK)
    else:a.ellipse(f,x+sway,y,2,3,(95,151,104))


def pot(f,x,y=53):
    a.rect(f,x-6,y-8,12,2,(181,119,81))
    a.rect(f,x-5,y-6,10,5,(136,79,58))
    a.rect(f,x-4,y-1,8,1,(88,59,45))
    a.rect(f,x-3,y-5,2,3,(172,101,68))


def soot(f,x,floor=53,t=0,pose='walk',friendly=False):
    x=round(x);y=round(floor-7)
    a.ellipse(f,x,y+4,4,4,(25,27,37));a.ellipse(f,x,y+3,3,3,(88,68,87))
    f.set(x-3,y,(119,83,106));f.set(x+2,y-1,(119,83,106))
    a.rect(f,x-2,y+2,2,2,a.CREAM);a.rect(f,x+1,y+2,2,2,a.CREAM)
    if pose=='surprise':a.rect(f,x,y+5,2,2,a.INK)
    else:f.set(x,y+5,a.INK)
    d=1 if int(t*4)%2 else 0
    a.rect(f,x-3-d,floor,2,1,(112,76,85));a.rect(f,x+2+d,floor,2,1,(112,76,85))
    if friendly:a.rect(f,x-2,y+6,5,1,(90,142,119))


def biscuit(f,x,y,half=0):
    for yy in range(-4,5):
        for xx in range(-5,6):
            if xx*xx/25+yy*yy/16<=1 and (not half or (xx<0 if half<0 else xx>=0)):
                f.set(round(x)+xx,round(y)+yy,(94,61,41))
    for yy in range(-3,4):
        for xx in range(-4,5):
            if xx*xx/16+yy*yy/9<=1 and (not half or (xx<0 if half<0 else xx>=0)):
                f.set(round(x)+xx,round(y)+yy,(209,156,95))
    for dx,dy in ((-2,-1),(2,1),(0,-2),(-1,2)):
        if not half or (dx<0 if half<0 else dx>=0):f.set(round(x)+dx,round(y)+dy,(112,71,49))


def heart(f,x,y):
    a.sprite(f,('rr.rr','rrrrr','.rrr.','..r..'),{'r':a.CORAL},x-2,y-2)


def cup(f,x,y,filled=False):
    a.rect(f,x-3,y-3,6,4,(163,190,165));a.rect(f,x+3,y-2,2,2,(163,190,165))
    a.line(f,x-2,y-3,x+1,y-3,a.GOLD if filled else (49,71,66))
    if filled:f.set(round(x),round(y)-5,(97,130,122))


class Painter:
    def __init__(self,worlds):
        self.backgrounds=[a.background('burrow')]
        if worlds==2:self.backgrounds.append(a.background('greenhouse',1))

    def render(self,s:Story):
        return [self._room(s,i) for i in range(s.worlds)]

    def _room(self,s,i):
        f=Frame.black();f.pixels[:]=self.backgrounds[i].pixels
        t=s.elapsed;now=s.time;e=s.episode;r=s.rooms[i]
        if r.lantern:
            if i==0:
                # A seed lights the small wall lamp, not the whole panel.
                a.rect(f,11,9,7,3,(215,175,98));a.rect(f,12,9,5,2,a.CREAM)
            else:
                for x in (7,56):
                    a.line(f,x,29,x,33,(86,107,86));a.rect(f,x-1,34,3,4,a.GOLD)
                    f.set(x,35,a.CREAM)
        if i==0:
            self._workshop_props(f,s)
            a.machine(f,progress=1 if e=='build' and 9<t<20 or e=='tea' and 5<t<18 else 0,
                      t=now*.6,cog_installed=s.gear)
            if e=='build':self._build_machine(f,s)
            if e=='tea':self._tea_above(f,s)
        else:self._garden_activity(f,s)
        # Permanent destination plants, with the newest one growing at deposit.
        plant_room=s.worlds-1
        if i==plant_room:
            x=12 if i==0 else 34
            if s.worlds==2 or r.flowers:pot(f,x)
            kinds=list(r.flowers)
            start=12 if s.worlds==1 else 20
            growing=e=='delivery' and start<=t<start+5
            for j,kind in enumerate(kinds):
                growth=ease((t-start)/5) if growing and j==len(kinds)-1 else 1.0
                flower(f,x+(j-1)*6 if len(kinds)>1 else x,45,growth,kind,now,j%2)
            if e=='delivery' and start+3<t<start+10:
                for k in range(3):
                    yy=40-((t-start-3)*3+k*4)%19
                    a.star(f,x+math.sin(t+k*2)*10,yy,FLOWERS[s._kind],1)
        if i==0:self._maker(f,s)
        else:self._gardener(f,s)
        self._courier(f,s,i)
        if i==0:
            if e=='biscuit':self._biscuit_story(f,s)
            elif s.friend:
                # The former thief now sweeps crumbs and tends the boiler.
                x=between(now%14,2,8,7,19)
                soot(f,x,t=now,friendly=True)
                a.line(f,x+3,50,x+7,54,(134,104,66));a.rect(f,x+5,54,5,2,(171,135,76))
            if e=='tea':self._tea_below(f,s)
            if e=='build':self._build_front(f,s)
        if s.worlds==2:
            active=e=='delivery' and (5<t<15 or 27<t<35)
            # Door jamb in front makes the character disappear through a place.
            x=56 if i==0 else 0
            color=(86,139,123) if active else (65,103,99)
            a.line(f,x,36,x,52,color)
            if active:
                for k in range(2):f.set(x+2+k*3,38+int((now*3+k*4)%13),a.GOLD)
        return f

    def _workshop_props(self,f,s):
        # Personal possessions stay put between stories.
        for j in range(s.rooms[0].cups):cup(f,7+j*5,22,True)
        if s.friend:
            a.rect(f,2,47,7,6,(91,71,64));a.rect(f,4,49,3,4,(29,30,33))
            a.line(f,1,47,5,44,(121,91,66));a.line(f,5,44,9,47,(121,91,66))
        for j in range(s.rooms[0].crumbs):f.set(10+j*4,56,a.GOLD)
        # Maker's hammer rests visibly at the bench edge.
        a.line(f,31,46,34,49,(136,101,61));a.rect(f,30,44,4,2,(117,150,139))

    def _build_machine(self,f,s):
        t=s.elapsed
        if 9<t<12:
            # Pressure, wobble, then an improbable living flower.
            for k in range(3):
                y=25-((t-9)*4+k*3)%10
                a.ellipse(f,39+math.sin(t*2+k)*2,y,1,1,(115,140,110))
        if 10<t<24:
            grow=ease((t-10)/3)*min(1.0,(24-t)/2)
            flower(f,39,25,grow,'honey' if not s._gentle else s._kind,s.time)
        if not s._gentle and 12.5<t<14:
            # A contained pollen sneeze; the camera and room never flash.
            for k in range(7):
                phase=(t-12.5)/1.5
                x=39+math.cos(k*2.1)*phase*13;y=18+math.sin(k*2.1)*phase*9
                a.ellipse(f,x,y,1,1,(151,162,105))
        if s._gentle and 12<t<19:
            for k in range(2):
                a.star(f,39+math.sin(t*.9+k*3)*9,17+math.cos(t*.9+k*3)*4,FLOWERS[s._kind],1)

    def _maker(self,f,s):
        e=s.episode;t=s.elapsed;pose='idle';x=44
        if e=='build':
            pose='point' if 4<t<8 else 'crouch' if 9<t<12 else 'surprise' if 12.5<t<17 and not s._gentle else 'cheer' if 21<t<24 else 'idle'
        elif e=='biscuit':pose='surprise' if 10<t<16 and not s._friendly_before else 'cheer' if 20<t<24 else 'idle'
        elif e=='tea':pose='point' if 4<t<9 else 'surprise' if 10<t<15 else 'cheer' if 24<t<27 else 'idle'
        elif e=='delivery':pose='cheer' if 3<t<5 or 35<t<37 else 'idle'
        elif int(s.time)%17 in (0,1):pose='crouch'
        flying=e=='build' and not s._gentle and 12.5<t<16
        a.creature(f,'bramble',x,pose=pose,t=s.time,facing=-1,hat=s.hat=='bramble' and not flying)
        # Thoughtful maker glances down at the gauge during a pressure build.
        if e=='build' and 9<t<12:
            height=42 if int(t*4)%2 else 39
            a.line(f,43,48,40,height+2,a.PALETTE['a'])
            a.rect(f,38,height,5,2,(137,166,149))

    def _gardener(self,f,s):
        t=s.elapsed
        watching=s.episode=='delivery' and 10<t<29
        x=44 if watching else between(s.time%18,3,9,44,39)
        pose='cheer' if watching and 23<t<27 else 'point' if watching and 14<t<19 else 'idle'
        a.creature(f,'rue',x,pose=pose,t=s.time,facing=-1)
        if not watching and int(s.time)%18<5:
            # Rue has an occupation while the workshop tells its own story.
            a.rect(f,round(x)-4,46,5,4,(101,144,142));a.line(f,x-4,46,x-8,44,(133,178,161))
            f.set(round(x)-9,47+(int(s.time*3)%3),(111,162,177))

    def _garden_activity(self,f,s):
        now=s.time
        # Snail travels the sill at a completely different pace from the maker.
        x=46+int(now*.35)%10
        a.ellipse(f,x,26,2,2,(143,112,80));a.line(f,x-2,28,x+3,28,(126,150,106));f.set(x+3,26,a.CREAM)
        if s.rooms[1].flowers:
            for k in range(2):
                x=24+math.sin(now*.33+k*3)*12;y=16+math.cos(now*.48+k)*6
                a.star(f,x,y,(154,185,116),1 if int(now*4)%3 else 0)

    def _courier(self,f,s,room):
        c=s.courier()
        if c is None or c[0]!=room:return
        _,x,pose,facing=c;t=s.elapsed;e=s.episode
        carrying=(e=='build' and t<9) or s.inventory is not None
        flying=e=='build' and not s._gentle and 12.5<t<16
        a.creature(f,'nori',x,pose=pose,t=s.time,facing=facing,
                   hat=s.hat=='nori' and not flying,carry=carrying)
        if e=='build' and t<9:
            if t<8:gx,gy=x+5,37
            else:
                gx=between(t,8,9,29,39)
                gy=between(t,8,9,37,35)-math.sin((t-8)*math.pi)*4
            if s._had_gear:
                # After the first build, Nori supplies a bulb rather than
                # repeatedly pretending an installed machine has no gear.
                a.seed(f,gx,gy)
            else:a.cog(f,gx,gy,6,t*.1)
        elif e=='build' and 19<t<21:
            a.seed(f,between(t,19,21,39,x+5),between(t,19,21,15,36))
        elif s.inventory is not None:
            planting=e=='delivery' and ((s.worlds==2 and 17<t<20) or (s.worlds==1 and 9<t<12))
            if planting:
                begin=17 if s.worlds==2 else 9;end=begin+3
                a.seed(f,between(t,begin,end,x+5,34 if s.worlds==2 else 12),between(t,begin,end,36,44))
            else:a.seed(f,x+5,36)
        if e=='delivery' and ((s.worlds==2 and 24<t<27) or(s.worlds==1 and 19<t<22)):
            heart(f,x+5,30-(t%1)*2)

    def _build_front(self,f,s):
        t=s.elapsed
        if not s._gentle and 12.5<t<16:
            u=(t-12.5)/3.5
            start,end=(49,29) if s._hat_before=='bramble' else (29,49)
            x=round(start+(end-start)*u);y=round(35-math.sin(math.pi*u)*14)
            a.rect(f,x-4,y,8,2,a.GOLD);a.rect(f,x-2,y-3,5,3,(113,82,53))
        if 21<t<24:
            a.star(f,21,32-(t-21)*2,a.CREAM,1)
            a.star(f,53,36-(t-21)*2,a.CORAL,1)

    def _biscuit_story(self,f,s):
        t=s.elapsed
        # First visit is a theft; friendship turns future visits into delivery.
        friendly=s._friendly_before
        if t<5:x=between(t,0,5,57,24)
        elif t<11:x=between(t,5,11,24,7)
        elif t<22:x=7
        else:x=between(t,22,27,7,20)
        soot(f,x,t=s.time,pose='surprise' if 11<t<15 else 'walk',friendly=friendly)
        if t<5:biscuit(f,x,39) if friendly else biscuit(f,24,47)
        elif t<16:
            biscuit(f,x,39)
            if 8<t<11:
                for j in range(3):f.set(round(x)+5+j*4,54,a.GOLD)
        elif t<22:
            u=ease((t-16)/4)
            biscuit(f,7-2*u,40,-1);biscuit(f,7+14*u,42,1)
        if 20<t<25:heart(f,13,32-(t-20)*1.5)
        if friendly and 1<t<5:heart(f,x,35)

    def _tea_above(self,f,s):
        t=s.elapsed
        if 5<t<17:
            # A tiny rain shower from the boiler. The courier tries to catch it
            # with an umbrella, realizes it is backwards, and turns it over.
            for k in range(4):
                phase=((t-5)*.75+k*.25)%1
                x=39-11*phase;y=23+8*phase*phase
                a.line(f,x,y,x,y+1,a.GOLD)
        if 6<t<20:
            flipped=t>=13
            color=(127,113,145)
            a.line(f,28,32,28,41,(180,155,111))
            for dx in range(-7,8):
                h=round(math.sqrt(max(0,49-dx*dx))*.55)
                y=31+h if flipped else 32-h
                a.line(f,28+dx,y,28+dx,33,color)
            a.line(f,21,33,35,33,(185,149,159))
            if flipped:
                a.line(f,23,32,33,32,a.GOLD)
                for k in range(2):f.set(26+k*4,31,a.CREAM)
            elif t>9:
                for side in (-1,1):
                    y=35+int((t*6)%7);f.set(28+side*8,y,a.GOLD)

    def _tea_below(self,f,s):
        t=s.elapsed
        if 17<t<24:
            cup(f,28,47,t>20);cup(f,47,47,t>22)
            if t<21:
                for k in range(3):f.set(28,38+int((t*4+k*2)%7),a.GOLD)
        if 24<t<28:
            cup(f,28,44,True);cup(f,47,44,True)
            a.star(f,37,38,a.CREAM,1)

"""Original pixel art for Mosslight Works. All drawing is on the native 64px grid."""
from __future__ import annotations

import math
from pixoolib.frame import Frame

INK = (13, 24, 32)
CREAM = (236, 218, 167)
GOLD = (214, 156, 67)
MINT = (125, 198, 158)
CORAL = (224, 113, 87)


def rect(f, x, y, w, h, color):
    f.fill_rect(round(x), round(y), w, h, color)


def line(f, x0, y0, x1, y1, c):
    x0,y0,x1,y1=map(round,(x0,y0,x1,y1))
    dx=abs(x1-x0); sx=1 if x0<x1 else -1
    dy=-abs(y1-y0); sy=1 if y0<y1 else -1
    err=dx+dy
    while True:
        f.set(x0,y0,c)
        if x0==x1 and y0==y1:break
        e=2*err
        if e>=dy:err+=dy;x0+=sx
        if e<=dx:err+=dx;y0+=sy


def ellipse(f,x,y,rx,ry,c):
    for yy in range(math.floor(y-ry),math.ceil(y+ry)+1):
        for xx in range(math.floor(x-rx),math.ceil(x+rx)+1):
            if ((xx-x)/max(rx,.1))**2+((yy-y)/max(ry,.1))**2<=1:
                f.set(xx,yy,c)


def sprite(f, rows, palette, x,y,flip=False):
    x,y=round(x),round(y)
    for yy,row in enumerate(rows):
        for xx,key in enumerate(row):
            if key!='.': f.set(x+(len(row)-1-xx if flip else xx),y+yy,palette[key])


def star(f,x,y,color=CREAM,size=2):
    x,y=round(x),round(y)
    f.set(x,y,color)
    for d in range(1,size+1):
        for a,b in ((d,0),(-d,0),(0,d),(0,-d)):f.set(x+a,y+b,color)


# Nori: tall soft ears, a cream muzzle and a coral scarf visible from behind.
NORI = (
    '.oo....oo...',
    '.om....mo...',
    '.omm..mmo...',
    '..ommmmo....',
    '.ommmmmmo...',
    'ommmmmmmmo..',
    'ommcimcimmo.',
    'omcccccmmo..',
    '.occcicmo...',
    '..rrrrr.....',
    '.orrmmo.....',
    '.ommmmo.....',
    '..obbo......',
)
# Bramble: stocky, two antler-like antennae, round goggles and work apron.
BRAMBLE = (
    '..a.....a...',
    '...a...a....',
    '..ooooooo...',
    '.oaaaaaaao..',
    'oaaaaggggao.',
    'oaagcigcigo.',
    'oaaggggggao.',
    '.oaaccaaao..',
    '..oaaiao....',
    '.oattttao...',
    '.oatgttao...',
    '..otttto....',
    '..ob..bo....',
)
# Rue: greenhouse keeper; mushroom bonnet, lilac face, little leaf apron.
RUE = (
    '....ppp.....',
    '..pphpppp...',
    '.pppppphpp..',
    'pphpppppppp.',
    '.ooooooooo..',
    '..ovvvvvo...',
    '.ovcivcivo..',
    '.ovvccvvvo..',
    '..ovvicvo...',
    '..ottitto...',
    '..ottttto...',
    '...ob.bo....',
)
PALETTE = {'o':INK,'m':MINT,'c':CREAM,'i':INK,'r':CORAL,
           'b':(55,49,43),'a':(190,132,83),'g':GOLD,'t':(61,119,109),
           'v':(191,158,184),'p':(139,85,106),'h':(226,163,153)}


def creature(f, who, x, floor=53, pose='idle', t=0, facing=1, hat=False, carry=False):
    rows={'nori':NORI,'bramble':BRAMBLE,'rue':RUE}[who]
    walk=pose=='walk'
    step=int(t*4)%4
    bob=(-1 if step in (1,3) else 0) if walk else 0
    if pose=='cheer':bob=-2 if int(t*3)%2 else 0
    if pose=='crouch':bob=2
    x=round(x);top=round(floor-len(rows)+bob)
    # Feet are separate so silhouette changes on every readable walking pose.
    shadow=(20,36,36)
    ellipse(f,x+5,floor,5,1,shadow)
    sprite(f,rows,PALETTE,x,top,flip=facing<0)
    foot=PALETTE['b']
    rect(f,x+2-(1 if walk and step==1 else 0),floor-1+bob,3,2,foot)
    rect(f,x+7+(1 if walk and step==3 else 0),floor-1+bob,3,2,foot)
    if pose in ('lift','cheer','surprise') or carry:
        hand_y = top + (1 if pose == 'lift' or carry else 3)
        line(f,x,top+8,x-1,hand_y,PALETTE['m'] if who=='nori' else PALETTE['a'])
        line(f,x+10,top+8,x+11,hand_y,PALETTE['m'] if who=='nori' else PALETTE['a'])
    if pose=='point':line(f,x+9,top+9,x+14,top+8,PALETTE['a'])
    eye_y = top + (5 if who == 'bramble' else 6)
    eyes = (4, 7) if who == 'bramble' else (3, 6)
    blink = t % 4.75 < .25 and pose not in ('surprise', 'cheer')
    for ex in eyes:
        px = x + (10-ex if facing < 0 else ex)
        if blink or pose in ('sleep', 'cheer'):
            rect(f, px, eye_y, 2, 1, INK)
        elif pose == 'surprise':
            rect(f, px, eye_y-1, 2, 3, CREAM)
            f.set(px+(0 if facing < 0 else 1), eye_y, INK)
    if pose == 'surprise':
        rect(f,x+5,top+9,2,2,INK)
    elif pose == 'cheer':
        line(f,x+4,top+8,x+7,top+8,INK)
        rect(f,x+5,top+9,2,1,CREAM)
    if hat:
        rect(f,x+2,top-2,8,2,GOLD);rect(f,x+4,top-5,5,3,(113,82,53))


def cog(f,x,y,r=5,t=0):
    ellipse(f,x,y,r,r,(83,61,41));ellipse(f,x,y,r-1,r-1,GOLD)
    for k in range(8):
        a=k*math.tau/8+t
        rect(f,round(x+math.cos(a)*r)-1,round(y+math.sin(a)*r)-1,3,3,GOLD)
    ellipse(f,x,y,2,2,INK);f.set(round(x)-2,round(y)-2,CREAM)


def seed(f,x,y,t=0):
    ellipse(f,x,y,4,5,(110,80,49));ellipse(f,x,y-1,3,4,GOLD)
    rect(f,x-1,y-3,2,3,CREAM)
    line(f,x,y-5,x+2,y-7,(83,139,109));rect(f,x+2,y-8,3,2,MINT)


def portal(f,side='right',active=False,t=0):
    x=56 if side=='right' else 0
    color=(103,161,146) if active else (65,103,99)
    rect(f,x,36,8,18,(16,30,36));rect(f,x+1,35,6,2,color)
    line(f,x,37,x,52,color);line(f,x+7,37,x+7,52,color)
    rect(f,x,53,8,2,(103,83,60))
    if active:
        for k in range(3):f.set(x+2+k*2,38+int((t*3+k*4)%12),GOLD)


def background(kind='burrow',room=0):
    f=Frame.black()
    if kind=='burrow':
        f.clear((16,29,34))
        ellipse(f,32,32,33,33,(38,58,56));ellipse(f,32,32,29,30,(29,45,45))
        for y in (14,23,32,41):
            line(f,5,y,58,y,(36,51,49))
            for x in range(9+(y%2)*7,60,15):line(f,x,y-7,x,y-1,(36,51,49))
        # Amber alcove and rim, warm light held in a small portion of the frame.
        ellipse(f,14,10,9,8,(57,64,49));line(f,14,0,14,5,(106,89,58))
        rect(f,9,6,11,2,(126,101,61));rect(f,11,8,7,4,GOLD);rect(f,12,8,5,2,CREAM)
        rect(f,5,23,17,2,(125,86,57));rect(f,6,25,2,3,(76,58,45))
        for x,h,c in [(7,5,(94,142,129)),(12,7,(145,96,94)),(17,4,(151,129,76))]:
            rect(f,x,23-h,3,h,c);f.set(x+1,22-h,CREAM)
        # High crescent window.
        ellipse(f,45,12,8,8,(98,91,69));ellipse(f,45,12,6,6,(26,49,61))
        ellipse(f,46,10,3,3,(150,177,161));ellipse(f,47,9,3,3,(26,49,61))
        line(f,39,13,50,13,(90,86,65));line(f,45,6,45,18,(90,86,65))
    elif kind=='greenhouse':
        f.clear((17,33,44))
        ellipse(f,32,31,31,33,(35,59,62));ellipse(f,32,31,28,30,(23,45,51))
        for x in (7,19,32,45,57):line(f,x,9 if x in(7,57) else 3,x,46,(59,91,86))
        for y in (15,29):line(f,4,y,59,y,(59,91,86))
        ellipse(f,43,10,5,5,(176,191,153));ellipse(f,45,9,5,5,(23,45,51))
        for x,y in ((12,8),(27,11),(53,20),(36,22)):f.set(x,y,(99,136,127))
        # Hanging leaves.
        line(f,13,0,13,23,(66,98,78))
        for x,y in ((10,9),(15,14),(10,19)):
            ellipse(f,x,y,3,2,(64,113,87));f.set(x-1,y,(93,141,99))
        rect(f,46,28,13,3,(101,79,53));rect(f,49,23,7,5,(155,93,67))
        for x in (49,52,55):line(f,52,24,x,20,(103,151,104))
    elif kind=='attic':
        f.clear((25,27,47))
        for x in range(64):
            line(f,32,0,x,24,(36,35,53))
        line(f,0,25,32,1,(134,90,67));line(f,32,1,63,25,(134,90,67))
        rect(f,2,27,60,22,(46,37,48))
        ellipse(f,32,15,8,8,(120,92,78));ellipse(f,32,15,6,6,(37,58,76))
        star(f,31,14,(209,186,123),2)
        rect(f,7,32,17,2,(148,94,70))
        rect(f,10,26,5,6,(91,133,140));rect(f,18,22,4,10,(176,117,99))
        line(f,51,7,51,22,(163,132,85));ellipse(f,51,24,4,5,GOLD)
    elif kind=='mushroom':
        f.clear((18,34,36));ellipse(f,32,34,30,33,(53,57,48))
        ellipse(f,31,11,30,10,(115,66,60));ellipse(f,29,7,22,6,(151,88,68))
        for x,y in ((12,8),(34,5),(46,9)):ellipse(f,x,y,3,2,(205,158,104))
        for x in (9,20,43,54):line(f,x,22,x,48,(65,62,48))
        ellipse(f,43,29,6,8,(122,118,74));ellipse(f,43,29,4,6,(180,177,111))
        rect(f,8,32,15,3,(120,79,51));rect(f,11,28,4,4,(94,143,120))
    rect(f,0,54,64,10,(49,54,45));line(f,0,54,63,54,(120,104,73))
    for y in (59,63):line(f,0,y,63,y,(35,43,39))
    for x in (8,26,48):line(f,x,55,x-3,58,(61,61,48));line(f,x+10,60,x+7,63,(61,61,48))
    portal(f,'right' if room%2==0 else 'left')
    return f


def machine(f,progress=0,t=0,cog_installed=False):
    # Curved copper boiler above a little workbench; an upward-facing spout.
    rect(f,28,43,24,3,(131,91,56));rect(f,29,46,3,8,(78,60,44));rect(f,47,46,3,8,(78,60,44))
    ellipse(f,39,35,8,8,(90,61,41));ellipse(f,38,34,7,7,(161,105,56))
    rect(f,33,32,3,6,(203,145,72));rect(f,34,28,10,3,GOLD)
    rect(f,36,25,6,3,(128,88,48));rect(f,35,24,8,2,(187,137,70))
    rect(f,42,34,7,3,(151,101,53));rect(f,47,32,3,5,GOLD)
    if cog_installed:cog(f,39,35,4,t if progress else 0)
    else:ellipse(f,39,35,3,3,(61,51,37));f.set(39,35,(105,82,48))
    rect(f,29,36,3,2,(94,124,99));rect(f,28,33,2,5,(87,101,75))
    if progress:
        for x,y in ((32,39),(43,30)):f.set(x,y,CREAM)

"""ANSI half-block preview with unbuffered key decoding and multiple worlds."""
from __future__ import annotations

import os
import select
import shutil
import sys
import termios
import time
import tty

from .frame import Frame
from .runtime import Event

ENTER_ALT='\x1b[?1049h';EXIT_ALT='\x1b[?1049l'
HIDE_CURSOR='\x1b[?25l';SHOW_CURSOR='\x1b[?25h'
CURSOR_HOME='\x1b[H';CLEAR_SCREEN='\x1b[2J';RESET='\x1b[0m'
ARROW={b'\x1b[A':'up',b'\x1b[B':'down',b'\x1b[C':'right',b'\x1b[D':'left',
       b'\x1bOA':'up',b'\x1bOB':'down',b'\x1bOC':'right',b'\x1bOD':'left'}


class KeyDecoder:
    """Retain partial ANSI sequences; only a lone timed-out ESC means quit."""
    def __init__(self):
        self.buffer=bytearray()
        self.escape_since=None

    def feed(self,data:bytes,now:float):
        self.buffer.extend(data)
        out=[]
        while self.buffer:
            if self.buffer[0]==27:
                if self.escape_since is None:self.escape_since=now
                if len(self.buffer)==1:
                    if now-self.escape_since<.06:break
                    del self.buffer[0];out.append(Event('key','escape'));self.escape_since=None;continue
                if self.buffer[1] in (ord('['),ord('O')):
                    # CSI ends at a byte in 0x40..0x7e, after its introducer.
                    end=next((i+1 for i in range(2,len(self.buffer)) if 64<=self.buffer[i]<=126),None)
                    if end is None:
                        if now-self.escape_since<.1:break
                        self.buffer.clear();self.escape_since=None;continue
                    seq=bytes(self.buffer[:end]);del self.buffer[:end]
                    key=ARROW.get(seq)
                    if key:out.append(Event('key',key))
                    self.escape_since=None;continue
                # Alt+key is not a request to quit.
                del self.buffer[:2];self.escape_since=None;continue
            ch=self.buffer.pop(0)
            key={3:'ctrl+c',9:'tab',10:'enter',13:'enter',32:'space'}.get(ch)
            if key is None and 33<=ch<127:key=chr(ch)
            if key:out.append(Event('key',key))
        return out


def frame_rows(frames):
    rows=[]
    for row in range(32):
        parts=[]
        for n,frame in enumerate(frames):
            if n:parts.append(RESET+'  ')
            p=frame.pixels;last=None
            for col in range(64):
                ti=(row*2*64+col)*3;bi=ti+64*3
                colors=tuple(p[ti:ti+3])+tuple(p[bi:bi+3])
                if colors!=last:
                    r,g,b,rr,gg,bb=colors
                    parts.append(f'\x1b[38;2;{r};{g};{b};48;2;{rr};{gg};{bb}m');last=colors
                parts.append('▀')
        rows.append(''.join(parts)+RESET+'\x1b[K')
    return rows


class TerminalDriver:
    def __init__(self,status=None):
        self._saved_termios=None
        self._started=False
        self.decoder=KeyDecoder()
        self.focus=0
        self._worlds=1
        self.status=status
        self._last_size=None

    def start(self):
        if not sys.stdout.isatty() or not sys.stdin.isatty():
            raise RuntimeError('terminal preview requires a TTY; use --snap PATH for headless output')
        fd=sys.stdin.fileno()
        self._saved_termios=termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            sys.stdout.write(ENTER_ALT+HIDE_CURSOR+CLEAR_SCREEN+CURSOR_HOME)
            sys.stdout.flush();self._started=True
        except BaseException:
            termios.tcsetattr(fd,termios.TCSADRAIN,self._saved_termios)
            raise

    def stop(self):
        if not self._started:return
        try:
            sys.stdout.write(RESET+SHOW_CURSOR+EXIT_ALT);sys.stdout.flush()
        finally:
            if self._saved_termios is not None:
                termios.tcsetattr(sys.stdin.fileno(),termios.TCSADRAIN,self._saved_termios)
            self._started=False

    def render(self,frame:Frame):self.render_worlds([frame])

    def render_worlds(self,frames):
        self._worlds=len(frames)
        width,height=shutil.get_terminal_size()
        buf=CURSOR_HOME
        if self._last_size!=(width,height):buf+=CLEAR_SCREEN;self._last_size=(width,height)
        if width<64 or height<34:
            message='Resize to at least 64 columns × 34 rows. q quits.'
            sys.stdout.write(buf+message[:max(1,width-1)]+RESET+'\x1b[K');sys.stdout.flush();return
        all_fit=width>=len(frames)*66-2
        selected=frames if all_fit else [frames[self.focus%len(frames)]]
        lines=frame_rows(selected)
        title=self.status() if self.status else 'q / Esc to quit'
        if len(frames)>1:
            title=('Workshop | Greenhouse — ' if all_fit else f'World {self.focus%len(frames)+1}/{len(frames)} · Tab switches — ')+title
        lines.append(title[:width-1]+'\x1b[K')
        sys.stdout.write(buf+'\r\n'.join(lines));sys.stdout.flush()

    def events(self):
        fd=sys.stdin.fileno();data=bytearray()
        while select.select([fd],[],[],0)[0]:
            block=os.read(fd,4096)
            if not block:return [Event('key','ctrl+c')]
            data.extend(block)
        events=self.decoder.feed(bytes(data),time.monotonic())
        for event in events:
            if event.key=='tab':self.focus=(self.focus+1)%self._worlds
        return events

"""Atomic device-selection and target-specific priming cache."""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import threading

STATE_FILE=Path(__file__).resolve().parent.parent/'.pixoo-state.json'
_LOCK=threading.RLock()


def save(d:dict):
    with _LOCK:
        fd,name=tempfile.mkstemp(prefix='.pixoo-state-',dir=STATE_FILE.parent)
        try:
            with os.fdopen(fd,'w') as fp:json.dump(d,fp,indent=2)
            os.replace(name,STATE_FILE)
        finally:
            if os.path.exists(name):os.unlink(name)


def load()->dict|None:
    with _LOCK:
        try:
            value=json.loads(STATE_FILE.read_text())
            return value if isinstance(value,dict) else None
        except (FileNotFoundError,json.JSONDecodeError):return None


def is_primed(ip):
    s=load() or {}
    targets=s.get('primed_devices',{})
    return isinstance(targets,dict) and targets.get(ip) is True


def set_primed(v:bool,ip:str|None=None):
    with _LOCK:
        s=load() or {}
        ip=ip or s.get('ip')
        targets=s.get('primed_devices',{})
        if not isinstance(targets,dict):targets={}
        if ip:targets[ip]=bool(v)
        s['primed_devices']=targets
        if ip==s.get('ip'):s['primed']=bool(v)
        save(s)

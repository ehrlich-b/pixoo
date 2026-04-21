"""Pre-upload a multi-frame animation to the Pixoo via N POSTs.

Device semantics (see PROTOCOL.md):
- Same PicID across all frames, PicOffset 0..N-1, PicNum=N on every POST.
- Device starts looping when the last offset for a PicID arrives.
- PicSpeed is ms/frame on playback; floor ~80ms (12fps).
- Community cap: 60 frames per PicID before upload freezes.
"""
from __future__ import annotations

from .client import PixooClient
from .frame import Frame


UPLOAD_TIMEOUT = 15.0


def upload_animation(client: PixooClient, frames: list[Frame],
                     speed_ms: int, pic_id: int) -> None:
    """Upload frames as one animation under pic_id.

    Blocks until all N POSTs complete. Any HTTP error propagates.
    """
    n = len(frames)
    for i, frame in enumerate(frames):
        client.post({
            "Command":   "Draw/SendHttpGif",
            "PicNum":    n,
            "PicWidth":  64,
            "PicOffset": i,
            "PicID":     pic_id,
            "PicSpeed":  speed_ms,
            "PicData":   frame.to_base64(),
        }, timeout=UPLOAD_TIMEOUT)

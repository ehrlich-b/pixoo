"""Display the cached Pixoo IP on the device so you know where it lives."""
from __future__ import annotations

from pixoolib.digits import draw_text, text_width
from pixoolib.frame import Frame
from pixoolib.session import ensure_primed, get_client


def main() -> None:
    c = get_client()
    ensure_primed(c)
    ip = c.ip
    parts = ip.split(".")
    line1 = ".".join(parts[:2])
    line2 = ".".join(parts[2:])
    f = Frame.black()
    draw_text(f, line1, (64 - text_width(line1)) // 2, 20, (0, 255, 0))
    draw_text(f, line2, (64 - text_width(line2)) // 2, 36, (0, 255, 0))
    c.reset_gif_id()
    c.post({
        "Command": "Draw/SendHttpGif",
        "PicNum": 1, "PicWidth": 64, "PicOffset": 0,
        "PicID": 1, "PicSpeed": 1000, "PicData": f.to_base64(),
    })
    print(f"displayed {ip}")


if __name__ == "__main__":
    main()

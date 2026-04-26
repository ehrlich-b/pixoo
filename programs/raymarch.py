"""Raymarch — bouncing SDF sphere over a checker plane."""
from __future__ import annotations

import math

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


MARCH_STEPS = 28
HIT_EPS = 0.012
FAR = 32.0
SPHERE_R = 1.0
SPHERE_R2 = SPHERE_R * SPHERE_R


class Raymarch(Program):
    DESCRIPTION = "Raymarched SDF sphere bouncing over a checker plane"

    def setup(self) -> None:
        self._t = 0.0
        # Light direction (toward light, normalized).
        l = (0.55, 0.85, -0.25)
        ll = 1.0 / math.sqrt(l[0]**2 + l[1]**2 + l[2]**2)
        self._lx, self._ly, self._lz = l[0]*ll, l[1]*ll, l[2]*ll

    def update(self, dt: float, events) -> None:
        self._t += dt

    def render(self) -> Frame:
        f = Frame.black()
        t = self._t
        # Sphere bouncing in a small arc.
        bx = math.sin(t * 0.7) * 1.1
        bz = math.cos(t * 0.9) * 1.1
        by = SPHERE_R + abs(math.sin(t * 2.4)) * 0.55
        # Camera orbits the origin.
        ang = t * 0.32
        cam_x = math.sin(ang) * 4.6
        cam_y = 2.1
        cam_z = math.cos(ang) * 4.6
        # Look direction toward origin (slightly above).
        ldx = -cam_x
        ldy = -cam_y + 0.7
        ldz = -cam_z
        ll = 1.0 / math.sqrt(ldx*ldx + ldy*ldy + ldz*ldz)
        ldx *= ll; ldy *= ll; ldz *= ll
        # Camera basis.
        wx, wy, wz = 0.0, 1.0, 0.0
        rx = ldy * wz - ldz * wy
        ry = ldz * wx - ldx * wz
        rz = ldx * wy - ldy * wx
        rl = 1.0 / math.sqrt(rx*rx + ry*ry + rz*rz)
        rx *= rl; ry *= rl; rz *= rl
        upx = ry * ldz - rz * ldy
        upy = rz * ldx - rx * ldz
        upz = rx * ldy - ry * ldx
        FOV = 1.0
        lx, ly, lz = self._lx, self._ly, self._lz
        px_buf = f.pixels
        sqrt = math.sqrt
        floor = math.floor
        for py_ in range(HEIGHT):
            v = -((py_ + 0.5) / HEIGHT * 2 - 1) * FOV
            for px_ in range(WIDTH):
                u = ((px_ + 0.5) / WIDTH * 2 - 1) * FOV
                dx = ldx + u * rx + v * upx
                dy = ldy + u * ry + v * upy
                dz = ldz + u * rz + v * upz
                inv = 1.0 / sqrt(dx*dx + dy*dy + dz*dz)
                dx *= inv; dy *= inv; dz *= inv
                tdist = 0.0
                hit = 0
                hx = hy = hz = 0.0
                for _ in range(MARCH_STEPS):
                    x = cam_x + dx * tdist
                    y = cam_y + dy * tdist
                    z = cam_z + dz * tdist
                    sx = x - bx; sy = y - by; sz = z - bz
                    sphere = sqrt(sx*sx + sy*sy + sz*sz) - SPHERE_R
                    plane = y
                    if sphere < plane:
                        d = sphere; obj = 1
                    else:
                        d = plane; obj = 2
                    if d < HIT_EPS:
                        hit = obj
                        hx = x; hy = y; hz = z
                        break
                    tdist += d
                    if tdist > FAR:
                        break
                if hit == 1:
                    nx = (hx - bx) / SPHERE_R
                    ny = (hy - by) / SPHERE_R
                    nz = (hz - bz) / SPHERE_R
                    diff = nx * lx + ny * ly + nz * lz
                    if diff < 0.0:
                        diff = 0.0
                    # Specular highlight (Phong).
                    hxv = (lx - dx) * 0.5
                    hyv = (ly - dy) * 0.5
                    hzv = (lz - dz) * 0.5
                    hl = 1.0 / max(0.001, sqrt(hxv*hxv + hyv*hyv + hzv*hzv))
                    hxv *= hl; hyv *= hl; hzv *= hl
                    sp = nx*hxv + ny*hyv + nz*hzv
                    spec = sp**32 if sp > 0 else 0.0
                    intensity = 0.18 + 0.75 * diff
                    r = int(min(255, 235 * intensity + 230 * spec))
                    g = int(min(255, 80 * intensity + 230 * spec))
                    b = int(min(255, 60 * intensity + 230 * spec))
                    pi = (py_ * WIDTH + px_) * 3
                    px_buf[pi] = r; px_buf[pi+1] = g; px_buf[pi+2] = b
                elif hit == 2:
                    cx_ = int(floor(hx + 100)) & 1
                    cz_ = int(floor(hz + 100)) & 1
                    check = cx_ ^ cz_
                    # Shadow probe — does ray (h, eps→light) hit the sphere?
                    shx = hx - bx; shy = -by; shz = hz - bz
                    bb = 2 * (shx*lx + shy*ly + shz*lz)
                    cc = shx*shx + shy*shy + shz*shz - SPHERE_R2
                    disc = bb*bb - 4 * cc
                    in_shadow = False
                    if disc > 0:
                        t1 = (-bb - sqrt(disc)) * 0.5
                        if t1 > 0.001:
                            in_shadow = True
                    fade = max(0.0, 1.0 - tdist / FAR)
                    if check:
                        cr, cg, cb = 190, 190, 210
                    else:
                        cr, cg, cb = 50, 50, 70
                    if in_shadow:
                        cr //= 3; cg //= 3; cb //= 3
                    pi = (py_ * WIDTH + px_) * 3
                    px_buf[pi] = int(cr * fade)
                    px_buf[pi+1] = int(cg * fade)
                    px_buf[pi+2] = int(cb * fade)
                else:
                    sky = dy * 0.7 + 0.3
                    if sky < 0:
                        sky = 0.0
                    pi = (py_ * WIDTH + px_) * 3
                    px_buf[pi] = int(40 + 60 * sky)
                    px_buf[pi+1] = int(80 + 100 * sky)
                    px_buf[pi+2] = int(140 + 95 * sky)
        return f

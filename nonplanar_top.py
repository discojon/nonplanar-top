#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# nonplanar_top - smooth top surfaces for PrusaSlicer prints (Prusa Core One INDX)
# Copyright (C) 2026 DiscoJon
#
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software Foundation,
# either version 3 of the License, or (at your option) any later version.  It is
# distributed WITHOUT ANY WARRANTY; see the LICENSE file for details.
#
# The toolhead clearance tables (INDX_FINE, INDX_COARSE) are measurements derived from
# the reverse-engineered INDX CAD by robertsamples (github.com/robertsamples/INDX-CAD,
# CC BY-SA 4.0), itself based on Prusa Research's INDX toolhead model.  The shroud table
# (SHROUD_REL) is measured from Prusa's CORE_One_INDX_fan_shroud_r1 part.
"""
nonplanar_top.py - smooth the shallow top surfaces of a PrusaSlicer print.

Replaces the stair-stepped top layers of gently sloped / domed surfaces with a
two-pass skin that follows the surface (the nozzle moves in Z while extruding):
  1. a levelling pass of variable thickness that fills the layer steps
  2. a finish pass of constant thickness that follows the smooth surface

Use it either
  * as a PrusaSlicer post-processing script (Print Settings > Output options >
    Post-processing scripts), where it runs automatically on every export, or
  * on its own:  python nonplanar_top.py  input.gcode|input.bgcode  [-o out.gcode]

Built for the Prusa Core One with the INDX toolhead.  Every converted file is
re-simulated (nozzle, heater block and part-cooling shroud clearance, coverage,
retraction bookkeeping) before it is written; if a check fails the file is not
converted.

Requires: Python 3.9+, numpy, scipy, shapely, opencv-python.
"""
import sys, os, re, math, time, struct, zlib, base64, configparser, argparse, traceback

try:
    import numpy as np
    import cv2
    from scipy import ndimage as ndi
    from shapely.geometry import Polygon, LineString, MultiPolygon, Point
    from shapely.ops import unary_union
    from shapely import affinity
    _IMPORT_ERROR = None
except ImportError as _e:      # reported later, so the script can still pass files through
    _IMPORT_ERROR = _e

VERSION = "0.2.0"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(SCRIPT_DIR, "nonplanar_top_last.log")

# --------------------------------------------------------------------------------------
# settings
# --------------------------------------------------------------------------------------
DEFAULTS = {
    # When to act. "notes": only when Print Settings > Notes contains the word "nonplanar"
    # (lets you switch it on per print profile).  "always": every export.
    "activate": "notes",
    # Lowest point of the part-cooling fan shroud above the nozzle tip, in mm.
    # MEASURE THIS ON YOUR PRINTER (heat the nozzle first, it changes the gap a little).
    "shroud_height_mm": "1.5",
    # Extra clearance kept between any part of the toolhead and the print (except the nozzle tip).
    "safety_margin_mm": "0.3",
    # How far the flat face of the nozzle may "iron" into the surface right next to it.
    "plow_tolerance_mm": "0.08",
    # Steepest surface that will be smoothed.  Steeper areas stay as normal layers.
    "max_slope_deg": "12",
    # Smallest area worth smoothing, and the minimum number of layer steps it must cross.
    "min_region_area_mm2": "20",
    "min_levels": "3",
    # Distance kept from vertical walls and hole edges.  0 = the skin runs right up to the edge.
    "edge_inset_mm": "0.0",
    # Skin: finish pass thickness, and the thinnest allowed levelling pass.
    "finish_layer_mm": "0.2",
    "min_level_layer_mm": "0.1",
    # Finish pass line direction: auto (along the region's long side), x, y, or an angle in degrees.
    "finish_direction": "auto",
    # Speeds in mm/s.
    "level_perimeter_speed": "40",
    "level_infill_speed": "60",
    "finish_perimeter_speed": "35",
    "finish_infill_speed": "50",
    "skin_accel": "1500",
    # Height of travel moves over the skin.
    "travel_lift_mm": "0.6",
    # What to do when the conversion fails its safety checks:
    #   error -> stop the export and show the reason in PrusaSlicer
    #   skip  -> export the file unchanged
    "on_unsafe": "error",
    # Write a picture of the regions next to the log (needs matplotlib).
    "debug_image": "0",
}

def load_settings(notes_text):
    cfg = dict(DEFAULTS)
    ini = os.path.join(SCRIPT_DIR, "nonplanar_top.ini")
    if os.path.exists(ini):
        cp = configparser.ConfigParser(inline_comment_prefixes=(";", "#"))
        cp.read(ini, encoding="utf-8")
        if cp.has_section("nonplanar_top"):
            for k, v in cp.items("nonplanar_top"):
                cfg[k] = v.strip()
    # per-profile overrides in Print Settings > Notes, e.g.  "nonplanar_top: max_slope_deg=8, finish_direction=y"
    for m in re.finditer(r"nonplanar_top\s*:\s*([^\n\\]*)", notes_text or ""):
        for kv in m.group(1).split(","):
            if "=" in kv:
                k, v = kv.split("=", 1)
                cfg[k.strip()] = v.strip()
    return cfg

def fnum(cfg, k):
    return float(cfg[k])

# --------------------------------------------------------------------------------------
# toolhead model (Core One + INDX)
#   radial profile = lowest point of the head at a given horizontal distance from the
#   nozzle axis, relative to the nozzle tip, taken over all directions.
#   INDX values from the reverse-engineered CAD (github.com/robertsamples/INDX-CAD),
#   shroud values from CORE_One_INDX_fan_shroud_r1.stl relative to its own lowest
#   point, with 3 mm allowance for uncertainty in where it sits.
# --------------------------------------------------------------------------------------
INDX_FINE = [  # (r_from, r_to, lowest head z above the tip)
    (0.0, 0.6, 0.0), (0.6, 0.8, 0.146), (0.8, 1.0, 0.365), (1.0, 1.2, 0.583), (1.2, 1.4, 0.802),
    (1.4, 1.6, 1.094), (1.6, 1.8, 1.312), (1.8, 2.0, 1.531), (2.0, 2.2, 1.75), (2.2, 3.4, 2.657),
    (3.4, 3.6, 2.829), (3.6, 3.8, 3.122), (3.8, 4.0, 3.338), (4.0, 4.4, 3.636), (4.4, 6.0, 3.819)]
INDX_COARSE = [3.84, 4.09, 4.36, 4.65, 4.89, 4.97, 5.06, 5.11, 5.04, 4.96, 4.92, 5.12, 5.28, 5.31,
               5.47, 5.78, 6.13, 6.52, 6.95, 7.29, 7.68, 8.07, 8.46, 8.85, 9.24, 9.78, 13.45, 13.59,
               13.62, 13.67, 15.44, 14.40, 4.17, 4.17, 4.17, 4.16, 4.16, 4.16, 4.16, 4.16, 54.98,
               55.12, 56.60, 56.88, 56.91, 56.93, 56.96, 56.98, 57.01, 57.04, 57.06, 57.09, 57.11,
               57.15]  # 1 mm bins starting at r = 6
SHROUD_REL = {6: 38.35, 7: 20.67, 8: 15.43, 9: 15.43, 10: 13.42, 11: 13.42, 12: 11.91, 13: 9.97,
              14: 7.29, 15: 4.67, 16: 3.10, 17: 1.75, 18: 0.05, 19: 0, 20: 0, 21: 0, 22: 0, 23: 0,
              24: 0, 25: 0, 26: 0, 27: 0, 28: 0, 29: 2.15, 30: 6.67, 31: 19.18, 32: 21.42,
              33: 23.42, 34: 25.29, 35: 27.07, 36: 28.82, 37: 30.43, 38: 32.22, 39: 33.92,
              40: 35.66, 41: 37.72, 42: 39.62, 43: 41.75, 44: 43.63, 45: 46.07, 46: 48.76,
              47: 52.39}

def head_envelope(cfg, step=0.1, rmax=60.0):
    """returns radii r[i] (bin starts) and E[i]: lowest head point (above tip) at any distance >= r[i]"""
    hs = fnum(cfg, "shroud_height_mm")
    r = np.arange(0.0, rmax, step)
    e = np.full(r.shape, 1e3)
    for a, b, h in INDX_FINE:
        m = (r + step > a) & (r < b)
        e[m] = np.minimum(e[m], h)
    for k, h in enumerate(INDX_COARSE):
        a = 6.0 + k
        m = (r + step > a) & (r < a + 1)
        e[m] = np.minimum(e[m], h)
    for a, h in SHROUD_REL.items():
        m = (r + step > a) & (r < a + 1)
        e[m] = np.minimum(e[m], hs + h)
    E = np.minimum.accumulate(e[::-1])[::-1]
    return r, E

# --------------------------------------------------------------------------------------
# binary G-code (.bgcode) reading
# --------------------------------------------------------------------------------------
def _heatshrink_py(data, W, L, outlen):
    out = bytearray()
    nbits = len(data) * 8
    pos = 0
    mv = data
    def get(n):
        nonlocal pos
        if pos + n > nbits:
            return None
        v = 0
        for _ in range(n):
            byte = mv[pos >> 3]
            v = (v << 1) | ((byte >> (7 - (pos & 7))) & 1)
            pos += 1
        return v
    while len(out) < outlen:
        t = get(1)
        if t is None:
            break
        if t:
            b = get(8)
            if b is None:
                break
            out.append(b)
        else:
            i = get(W); c = get(L)
            if i is None or c is None:
                break
            i += 1; c += 1
            for _ in range(c):
                out.append(out[-i] if i <= len(out) else 0)
    return bytes(out[:outlen])

def heatshrink_decompress(data, W, L, outlen):
    try:
        import heatshrink2
        return heatshrink2.decompress(data, window_sz2=W, lookahead_sz2=L)[:outlen]
    except Exception:
        return _heatshrink_py(data, W, L, outlen)

_MP_TBL = "0123456789. \nGX"
def meatpack_decode(src):
    out = []
    unb = False; nosp = False; cmd_active = False; char_buf = 0; cmd_count = 0; fcq = 0
    add_space = False
    PARAMS = set("XYZEFIJRSGPWHCA")
    def gc(n):
        if n == 11:
            return "E" if nosp else " "
        return _MP_TBL[n]
    def emit(ch):
        nonlocal add_space
        new_line = False
        if ch == "G" and (not out or out[-1] == "\n"):
            add_space = True; new_line = True
        elif ch == "\n" or ch == " ":
            add_space = False
        if not new_line and add_space and ch in PARAMS:
            out.append(" ")
        if ch != "\n" or not out or out[-1] != "\n":
            out.append(ch)
    def rx(c):
        nonlocal fcq, char_buf
        if unb:
            if fcq > 0:
                emit(chr(c))
                if char_buf:
                    emit(char_buf); char_buf = 0
                fcq -= 1
            else:
                lo = c & 0xF; hi = c >> 4
                if lo == 0xF:
                    fcq += 1
                    if hi == 0xF:
                        fcq += 1
                    else:
                        char_buf = gc(hi)
                else:
                    a = gc(lo); emit(a)
                    if a != "\n":
                        if hi == 0xF:
                            fcq += 1
                        else:
                            emit(gc(hi))
        else:
            emit(chr(c))
    for c in src:
        if c == 0xFF:
            if cmd_count > 0:
                cmd_active = True; cmd_count = 0
            else:
                cmd_count += 1
        else:
            if cmd_active:
                if c == 251: unb = True
                elif c == 250: unb = False
                elif c == 247: nosp = True
                elif c == 246: nosp = False
                elif c == 249: unb = False
                cmd_active = False
            else:
                if cmd_count > 0:
                    rx(0xFF); cmd_count = 0
                rx(c)
    return "".join(out)

def read_bgcode(path, metadata_only=False):
    d = open(path, "rb").read()
    if d[:4] != b"GCDE":
        raise ValueError("not a binary G-code file")
    ver, cks = struct.unpack_from("<IH", d, 4)
    p = 10
    blocks = []
    while p < len(d):
        start = p
        typ, comp, usz = struct.unpack_from("<HHI", d, p); p += 8
        csz = usz
        if comp:
            csz, = struct.unpack_from("<I", d, p); p += 4
        psz = 6 if typ == 5 else 2
        params = d[p:p + psz]; p += psz
        raw = d[p:p + csz]; p += csz
        if cks == 1:
            crc, = struct.unpack_from("<I", d, p)
            if zlib.crc32(d[start:p]) != crc:
                raise ValueError("binary G-code checksum mismatch (file damaged?)")
            p += 4
        if metadata_only and typ in (1, 5):
            continue
        if comp == 0: data = raw
        elif comp == 1: data = zlib.decompress(raw)
        elif comp == 2: data = heatshrink_decompress(raw, 11, 4, usz)
        elif comp == 3: data = heatshrink_decompress(raw, 12, 4, usz)
        else: raise ValueError("unknown compression %d" % comp)
        blocks.append((typ, params, data))
    return blocks

def bgcode_to_ascii(path, metadata_only=False):
    """returns (ascii text, slicer config dict). Layout mirrors PrusaSlicer's own conversion."""
    blocks = read_bgcode(path, metadata_only)
    kv = lambda b: [l.split("=", 1) for l in b.decode("utf-8", "replace").split("\n") if "=" in l]
    conf = {}
    for t, p, d in blocks:
        if t == 2:
            conf = {k.strip(): v.strip() for k, v in kv(d)}
    if metadata_only:
        return None, conf
    out = []
    fm = {k: v for t, p, d in blocks if t == 0 for k, v in kv(d)}
    out.append("; generated by %s on %s\n\n\n" % (fm.get("Producer", "PrusaSlicer"), fm.get("Produced on", "")))
    names = {0: "thumbnail", 1: "thumbnail_JPG", 2: "thumbnail_QOI"}
    for t, p, d in blocks:
        if t == 5:
            f, w, h = struct.unpack("<HHH", p)
            enc = base64.b64encode(d).decode()
            out.append("\n;\n; %s begin %dx%d %d\n" % (names.get(f, "thumbnail"), w, h, len(enc)))
            for i in range(0, len(enc), 78):
                out.append("; " + enc[i:i + 78] + "\n")
            out.append("; %s end\n;\n" % names.get(f, "thumbnail"))
    out.append("\n")
    for t, p, d in blocks:
        if t == 1:
            enc, = struct.unpack("<H", p)
            out.append(meatpack_decode(d) if enc in (1, 2) else d.decode("latin1"))
    out.append("\n")
    for t, p, d in blocks:
        if t == 4:
            for k, v in kv(d):
                out.append("; %s = %s\n" % (k, v))
    out.append("\n; prusaslicer_config = begin\n")
    for t, p, d in blocks:
        if t == 2:
            for k, v in kv(d):
                out.append("; %s = %s\n" % (k, v))
    out.append("; prusaslicer_config = end\n\n")
    return "".join(out), conf

def ascii_config(text_tail):
    conf = {}
    m = text_tail.rfind("; prusaslicer_config = begin")
    if m < 0:
        return conf
    for l in text_tail[m:].split("\n")[1:]:
        if l.startswith("; prusaslicer_config = end"):
            break
        if l.startswith("; ") and " = " in l:
            k, v = l[2:].split(" = ", 1)
            conf[k.strip()] = v.strip()
    return conf

def conf_list(conf, key, tool=0, default=None, cast=float):
    v = conf.get(key)
    if v is None or v == "":
        return default
    parts = [s.strip().strip('"') for s in re.split(r"[;,]", v)]
    s = parts[tool] if tool < len(parts) else parts[0]
    if s in ("nil", ""):
        return default
    s = s.rstrip("%")
    try:
        return cast(s)
    except ValueError:
        return default

# --------------------------------------------------------------------------------------
# G-code parsing
# --------------------------------------------------------------------------------------
NUM = re.compile(r"([A-Z])(-?\d*\.?\d+)")
SURFACE_EXCLUDE = {"Support material", "Support material interface", "Wipe tower", "Skirt/Brim",
                   "Skirt", "Brim", "Custom", ""}

def arc_points(x, y, nx, ny, p, cw, seg=0.2):
    cx = x + p.get("I", 0.0); cy = y + p.get("J", 0.0)
    r = math.hypot(x - cx, y - cy)
    a0 = math.atan2(y - cy, x - cx); a1 = math.atan2(ny - cy, nx - cx)
    if cw:
        if a1 >= a0: a1 -= 2 * math.pi
    else:
        if a1 <= a0: a1 += 2 * math.pi
    n = max(2, int(abs(a1 - a0) * r / seg) + 1)
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / n), cy + r * math.sin(a0 + (a1 - a0) * i / n))
            for i in range(1, n)] + [(nx, ny)]

class Parsed:
    pass

def parse_gcode(lines):
    """One pass over the file.  Collects extrusion segments (for rasterising) and per-line
    motion info (for rewriting)."""
    P = Parsed()
    seg_x0 = []; seg_y0 = []; seg_x1 = []; seg_y1 = []; seg_lz = []; seg_w = []
    seg_surf = []; seg_tool = []; seg_obj = []; seg_line = []
    motion = {}          # line index -> (cmd, params, x0, y0, x1, y1, rel)
    layer_starts = []    # (line index, z, height)
    x = y = z = 0.0
    rel = False
    tool = 0; lz = None; height = 0.2; width = 0.45; typ = ""; obj = -1
    last_ext = -1
    tool_at = {}         # line index of T commands -> tool
    m204 = None; m106 = None
    for i, raw in enumerate(lines):
        if not raw:
            continue
        c0 = raw[0]
        if c0 == ";":
            if raw.startswith(";Z:"):
                lz = float(raw[3:]); layer_starts.append([i, lz, height])
            elif raw.startswith(";HEIGHT:"):
                height = float(raw[8:])
                if layer_starts and layer_starts[-1][0] >= i - 3:
                    layer_starts[-1][2] = height
            elif raw.startswith(";WIDTH:"):
                width = float(raw[7:])
            elif raw.startswith(";TYPE:"):
                typ = raw[6:].strip()
            continue
        code = raw.split(";", 1)[0].strip()
        if not code:
            continue
        if c0 == "G":
            head = code.split(None, 1)[0]
            if head in ("G0", "G1", "G2", "G3"):
                p = {k: float(v) for k, v in NUM.findall(code[len(head):])}
                if rel:
                    nx = x + p.get("X", 0.0); ny = y + p.get("Y", 0.0); nz = z + p.get("Z", 0.0)
                else:
                    nx = p.get("X", x); ny = p.get("Y", y); nz = p.get("Z", z)
                motion[i] = (head, p, x, y, nx, ny, rel)
                e = p.get("E", 0.0)
                if e > 0 and not rel and (nx != x or ny != y) and lz is not None:
                    if head in ("G2", "G3") and ("I" in p or "J" in p):
                        pts = arc_points(x, y, nx, ny, p, head == "G2")
                    else:
                        pts = [(nx, ny)]
                    px, py = x, y
                    surf = typ not in SURFACE_EXCLUDE
                    for qx, qy in pts:
                        seg_x0.append(px); seg_y0.append(py); seg_x1.append(qx); seg_y1.append(qy)
                        seg_lz.append(lz); seg_w.append(width); seg_surf.append(surf)
                        seg_tool.append(tool); seg_obj.append(obj); seg_line.append(i)
                        px, py = qx, qy
                    last_ext = i
                x, y, z = nx, ny, nz
            elif head == "G91":
                rel = True
            elif head == "G90":
                rel = False
            elif head == "G28":
                pass
        elif c0 == "T":
            m = re.match(r"^T(\d+)", code)
            if m:
                tool = int(m.group(1)); tool_at[i] = tool
        elif c0 == "M":
            if code.startswith("M486 S"):
                try:
                    obj = int(float(code.split()[1][1:]))
                except ValueError:
                    pass
    P.segs = {k: np.array(v) for k, v in dict(x0=seg_x0, y0=seg_y0, x1=seg_x1, y1=seg_y1, lz=seg_lz,
                                               w=seg_w, surf=seg_surf, tool=seg_tool, obj=seg_obj,
                                               line=seg_line).items()}
    P.motion = motion
    P.layers = layer_starts
    P.last_ext = last_ext
    P.tool_at = tool_at
    return P

# --------------------------------------------------------------------------------------
# rasterising
# --------------------------------------------------------------------------------------
class Grid:
    def __init__(self, x0, y0, x1, y1, res):
        self.res = res
        self.x0 = math.floor(x0 / res) * res; self.y0 = math.floor(y0 / res) * res
        self.W = int(math.ceil((x1 - self.x0) / res)); self.H = int(math.ceil((y1 - self.y0) / res))
    def xs(self):
        return self.x0 + (np.arange(self.W) + 0.5) * self.res
    def ys(self):
        return self.y0 + (np.arange(self.H) + 0.5) * self.res

def rasterize(segs, grid, layer_filter=None):
    """returns Hall (top z of anything), Hpart (top z of part surfaces), tool & object of the part top"""
    H, W, res = grid.H, grid.W, grid.res
    Hall = np.zeros((H, W), np.float32); Hpart = np.zeros((H, W), np.float32)
    toolm = np.full((H, W), -1, np.int16); objm = np.full((H, W), -1, np.int16)
    if len(segs["lz"]) == 0:
        return Hall, Hpart, toolm, objm
    SH = 2; sc = (1 << SH) / res
    order = np.argsort(segs["lz"], kind="stable")
    lzs = segs["lz"][order]
    bounds = np.flatnonzero(np.diff(lzs)) + 1
    groups = np.split(order, bounds)
    img = np.zeros((H, W), np.uint8)
    for g in groups:
        lz = float(segs["lz"][g[0]])
        if layer_filter is not None and not layer_filter(lz):
            continue
        X0 = ((segs["x0"][g] - grid.x0) * sc).astype(np.int32); Y0 = ((segs["y0"][g] - grid.y0) * sc).astype(np.int32)
        X1 = ((segs["x1"][g] - grid.x0) * sc).astype(np.int32); Y1 = ((segs["y1"][g] - grid.y0) * sc).astype(np.int32)
        th = np.maximum(1, np.round(segs["w"][g] / res)).astype(np.int32)
        surf = segs["surf"][g]; tool = segs["tool"][g]; obj = segs["obj"][g]
        x_lo = max(0, (min(X0.min(), X1.min()) >> SH) - 10); x_hi = min(W, (max(X0.max(), X1.max()) >> SH) + 11)
        y_lo = max(0, (min(Y0.min(), Y1.min()) >> SH) - 10); y_hi = min(H, (max(Y0.max(), Y1.max()) >> SH) + 11)
        if x_hi <= x_lo or y_hi <= y_lo:
            continue
        sub = img[y_lo:y_hi, x_lo:x_hi]
        off = np.array([x_lo << SH, y_lo << SH], np.int32)
        keys = sorted(set(zip(th.tolist(), surf.tolist(), tool.tolist(), obj.tolist())), key=lambda k: k[1])
        # everything -> Hall
        sub[:] = 0
        for t in sorted(set(th.tolist())):
            m = th == t
            pts = np.stack([np.stack([X0[m], Y0[m]], 1), np.stack([X1[m], Y1[m]], 1)], 1) - off
            cv2.polylines(sub, list(pts.reshape(-1, 2, 2)), False, 255, int(t), cv2.LINE_8, SH)
        msk = sub > 0
        Hall[y_lo:y_hi, x_lo:x_hi][msk] = lz
        # part surfaces -> Hpart, per tool/object
        for (t, s, tl, ob) in keys:
            if not s:
                continue
            m = (th == t) & surf & (tool == tl) & (obj == ob)
            sub[:] = 0
            pts = np.stack([np.stack([X0[m], Y0[m]], 1), np.stack([X1[m], Y1[m]], 1)], 1) - off
            cv2.polylines(sub, list(pts.reshape(-1, 2, 2)), False, 255, int(t), cv2.LINE_8, SH)
            msk = sub > 0
            Hpart[y_lo:y_hi, x_lo:x_hi][msk] = lz
            toolm[y_lo:y_hi, x_lo:x_hi][msk] = tl
            objm[y_lo:y_hi, x_lo:x_hi][msk] = ob
    return Hall, Hpart, toolm, objm

# --------------------------------------------------------------------------------------
# smooth surface reconstruction from the layer steps
#   A layer with top z_k is printed where the model surface is above that layer's
#   slicing plane m_k (mid-height), so the boundary between two steps is the contour
#   s = m_k.  Interpolating between neighbouring contours gives the surface.
# --------------------------------------------------------------------------------------
def reconstruct_surface(Hpart, grid, Zs, dmax_mm=15.0):
    res = grid.res
    # fill pinholes between top-layer lines (they expose the layer below and would act as
    # false contour lines); gaps up to ~0.5 mm are closed, real steps are kept
    k5 = max(3, int(round(0.5 / res)) | 1)
    Hc = ndi.grey_closing(Hpart, size=(k5, k5))
    Hpart = np.where(Hpart > 0, np.maximum(Hpart, Hc), 0).astype(np.float32)
    L = np.full(Hpart.shape, -1, np.int32)
    has = Hpart > 0
    L[has] = np.clip(np.searchsorted(Zs, Hpart[has] - 1e-4), 0, len(Zs) - 1)
    mids = np.empty(len(Zs) + 1)
    mids[1:-1] = (Zs[:-1] + Zs[1:]) / 2
    mids[0] = Zs[0] / 2
    mids[-1] = Zs[-1] + (Zs[-1] - (Zs[-2] if len(Zs) > 1 else 0)) / 2
    Lpad = np.where(has, L, -10).astype(np.int32)
    # cliffs: a drop of more than one layer (or to nothing) right next to a pixel
    mn = ndi.minimum_filter(Lpad, size=3, mode="constant", cval=-10)
    cliff = has & (mn < Lpad - 1)
    # steep: more than one layer of drop within 0.8 mm (steeper than ~26 deg), on either side
    fp = disc(0.8 / res).astype(bool)
    mn8 = ndi.minimum_filter(Lpad, footprint=fp, mode="constant", cval=-10)
    mx8 = ndi.maximum_filter(np.where(has, L, -10), footprint=fp, mode="constant", cval=-10)
    steep_any = has & ((mn8 < Lpad - 1) | (mx8 > Lpad + 1))
    near_cliff = ndi.binary_dilation(cliff, structure=fp)
    steep = steep_any & ~near_cliff        # chamfers and steep slopes, not the top of a vertical wall
    sta = steep_any
    dd = np.full(Hpart.shape, np.inf); du = np.full(Hpart.shape, np.inf)
    pad = int(dmax_mm / res)
    present = np.unique(L[has])
    for k in present:
        mk = L == k
        ys, xs = np.nonzero(mk)
        y0 = max(0, ys.min() - pad); y1 = min(L.shape[0], ys.max() + pad + 1)
        x0 = max(0, xs.min() - pad); x1 = min(L.shape[1], xs.max() + pad + 1)
        Lc = L[y0:y1, x0:x1]; mkc = mk[y0:y1, x0:x1]
        for kk, store in ((k - 1, dd), (k + 1, du)):
            # only gentle steps count as contour lines (chamfers and walls do not)
            tgt = (Lc == kk) & ~sta[y0:y1, x0:x1]
            if not tgt.any():
                continue
            d = ndi.distance_transform_edt(~tgt) * res
            st = store[y0:y1, x0:x1]
            st[mkc] = d[mkc]
    dd[dd > dmax_mm] = np.inf; du[du > dmax_mm] = np.inf
    both = np.isfinite(dd) & np.isfinite(du) & has
    w = np.where(both, dd + du, np.nan)
    if both.any():
        idx = ndi.distance_transform_edt(~both, return_distances=False, return_indices=True)
        wnear = w[idx[0], idx[1]]
        # smooth the step-width field (a nearest-neighbour fill leaves visible seams)
        sgw = 3.0 / res; kw = int(round(3 * sgw)) * 2 + 1
        vb = both.astype(np.float32)
        num = cv2.GaussianBlur(np.where(both, w, 0).astype(np.float32), (kw, kw), sgw)
        den = cv2.GaussianBlur(vb, (kw, kw), sgw)
        wfill = np.where(den > 0.02, num / np.maximum(den, 1e-6), wnear)
    else:
        wfill = np.full(Hpart.shape, np.inf)
    Lk = np.where(has, L, 0)
    m_lo = mids[Lk]; m_hi = mids[Lk + 1]; hstep = m_hi - m_lo; zk = Zs[Lk]
    s_both = m_lo + hstep * dd / np.where(both, dd + du, 1)
    only_d = np.isfinite(dd) & ~np.isfinite(du) & has
    only_u = ~np.isfinite(dd) & np.isfinite(du) & has
    with np.errstate(invalid="ignore", divide="ignore"):
        s_d = np.minimum(m_lo + hstep * np.where(only_d, dd, 0) / wfill, zk)
        s_u = np.maximum(m_hi - hstep * np.where(only_u, du, 0) / wfill, zk)
    S = np.where(both, s_both, np.where(only_d, s_d, np.where(only_u, s_u, zk)))
    S = np.where(has, S, 0)
    # smoothing inside the surface (not across cliffs / steep parts), wider where the steps are wide
    wmask = (has & ~steep_any & ~ndi.binary_dilation(cliff, iterations=2)).astype(np.float32)
    sig = np.clip(0.35 * np.where(np.isfinite(wfill), wfill, 4.0), 1.0, 4.0)
    levels = [1.0, 2.0, 4.0]
    blurred = []
    for sg in levels:
        k = int(round(3 * sg / res)) * 2 + 1
        num = cv2.GaussianBlur((S * wmask).astype(np.float32), (k, k), sg / res)
        den = cv2.GaussianBlur(wmask, (k, k), sg / res)
        blurred.append(np.where(den > 0.05, num / np.maximum(den, 1e-6), S))
    Ss = np.where(sig <= 2.0, blurred[0] + (blurred[1] - blurred[0]) * (sig - 1.0),
                  blurred[1] + (blurred[2] - blurred[1]) * (sig - 2.0) / 2.0)
    # smoothing only removes small kinks: never move more than 0.04 mm from the interpolated
    # surface, and never outside the height band this layer step can represent
    Ss = np.clip(Ss, S - 0.04, S + 0.04)
    Ss = np.clip(Ss, m_lo, m_hi)
    Ss = np.where(has, Ss, 0).astype(np.float32)
    return Ss, L, cliff, steep

# --------------------------------------------------------------------------------------
# head clearance
# --------------------------------------------------------------------------------------
def disc(radius_px):
    r = max(0, int(math.ceil(radius_px)))
    y, x = np.mgrid[-r:r + 1, -r:r + 1]
    return ((x * x + y * y) <= radius_px * radius_px + 1e-9).astype(np.uint8)

def required_nozzle_z(Hf, grid, cfg, coarse=0.5, which="all"):
    """lowest nozzle-tip height at each pixel that keeps the head clear of Hf"""
    r, E = head_envelope(cfg)
    margin = fnum(cfg, "safety_margin_mm"); plow = fnum(cfg, "plow_tolerance_mm")
    hmax = float(Hf.max()); hmin = float(Hf[Hf > 0].min()) if (Hf > 0).any() else 0.0
    span = hmax - hmin + margin + 1.0
    # bands of the monotone envelope
    bands = []
    i = 0; n = len(r)
    while i < n:
        e0 = E[i]
        if e0 > span:
            break
        j = i
        tol = 0.02 if r[i] < 2.5 else 0.25
        while j + 1 < n and E[j + 1] - e0 <= tol:
            j += 1
        r_out = r[j] + (r[1] - r[0])
        if r[i] < 0.6:
            m = -plow
        elif r_out <= 2.5:
            m = 0.0
        else:
            m = margin
        bands.append((r_out, e0, m))
        i = j + 1
    R = np.full(Hf.shape, -1e3, np.float32)
    res = grid.res
    f = int(round(coarse / res))
    Hc = None
    for r_out, e0, m in bands:
        if (which == "near" and r_out > 3.0) or (which == "far" and r_out <= 3.0):
            continue
        if r_out <= 3.0:
            d = cv2.dilate(Hf, disc(r_out / res))
            R = np.maximum(R, d - e0 + m)
        else:
            if Hc is None:
                Hh = Hf.shape[0] // f * f; Ww = Hf.shape[1] // f * f
                pad = np.zeros((math.ceil(Hf.shape[0] / f) * f, math.ceil(Hf.shape[1] / f) * f), np.float32)
                pad[:Hf.shape[0], :Hf.shape[1]] = Hf
                Hc = pad.reshape(pad.shape[0] // f, f, pad.shape[1] // f, f).max(axis=(1, 3))
            d = cv2.dilate(Hc, disc(r_out / coarse + 1.0))
            up = np.repeat(np.repeat(d, f, 0), f, 1)[:Hf.shape[0], :Hf.shape[1]]
            R = np.maximum(R, up - e0 + m)
    return R, bands

# --------------------------------------------------------------------------------------
# region selection
# --------------------------------------------------------------------------------------
def remove_small(mask, min_px):
    lab, n = ndi.label(mask)
    if n == 0:
        return mask
    sz = ndi.sum(mask, lab, range(1, n + 1))
    keep = np.zeros(n + 1, bool); keep[1:] = sz >= min_px
    return keep[lab]

def fill_small_holes(mask, max_px):
    lab, n = ndi.label(~mask)
    if n == 0:
        return mask
    sz = ndi.sum(~mask, lab, range(1, n + 1))
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])).tolist())
    fill = np.zeros(n + 1, bool)
    for i in range(1, n + 1):
        fill[i] = sz[i - 1] <= max_px and i not in border
    return mask | fill[lab]

def ell(mm, res):
    r = max(1, int(round(mm / res)))
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))

# --------------------------------------------------------------------------------------
# polygons
# --------------------------------------------------------------------------------------
def smooth_ring(coords, win_mm, step=0.2):
    ring = LineString(list(coords) + [coords[0]])
    Lr = ring.length
    n = max(8, int(Lr / step))
    pts = np.array([ring.interpolate(i * Lr / n).coords[0] for i in range(n)])
    w = int(min(win_mm, Lr / 8) / step) | 1
    if w >= 3:
        k = np.ones(w) / w
        pts = np.stack([np.convolve(np.concatenate([pts[-w:, a], pts[:, a], pts[:w, a]]), k, "same")[w:-w]
                        for a in (0, 1)], -1)
    return pts

def mask_to_polygons(mask, grid, smooth_mm=1.5):
    cs, hier = cv2.findContours(mask.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    if hier is None:
        return []
    hier = hier[0]
    tox = lambda c: [(grid.x0 + (p[0][0] + 0.5) * grid.res, grid.y0 + (p[0][1] + 0.5) * grid.res) for p in c]
    polys = []
    for i, c in enumerate(cs):
        if hier[i][3] != -1 or len(c) < 6:
            continue
        ext = smooth_ring(tox(c), smooth_mm)
        holes = []
        j = hier[i][2]
        while j != -1:
            if len(cs[j]) >= 6:
                holes.append(smooth_ring(tox(cs[j]), min(smooth_mm, 1.0)))
            j = hier[j][0]
        pg = Polygon(ext).buffer(0)
        for h in holes:
            pg = pg.difference(Polygon(h).buffer(0))
        polys.append(pg)
    out = []
    for pg in polys:
        pg = pg.buffer(grid.res / 2).buffer(-0.3).buffer(0.3).simplify(0.01)
        for g in getattr(pg, "geoms", [pg]):
            if g.geom_type == "Polygon" and not g.is_empty:
                out.append(g)
    return out

def rasterize_polys(polys, grid, buffer_mm=0.0):
    img = np.zeros((grid.H, grid.W), np.uint8)
    f = lambda ring: np.round((np.array(ring.coords) - [grid.x0, grid.y0]) / grid.res - 0.5).astype(np.int32)
    for pg in polys:
        q = pg.buffer(buffer_mm) if buffer_mm else pg
        for g in getattr(q, "geoms", [q]):
            tmp = np.zeros_like(img)
            cv2.fillPoly(tmp, [f(g.exterior)], 1)
            for r in g.interiors:
                cv2.fillPoly(tmp, [f(r)], 0)
            img |= tmp
    return img.astype(bool)

# --------------------------------------------------------------------------------------
# helpers to sample grids
# --------------------------------------------------------------------------------------
class Field:
    def __init__(self, A, grid):
        self.A = A; self.g = grid
    def at(self, x, y):
        g = self.g
        fx = (np.asarray(x, float) - g.x0) / g.res - 0.5; fy = (np.asarray(y, float) - g.y0) / g.res - 0.5
        i0 = np.clip(np.floor(fy).astype(int), 0, g.H - 2); j0 = np.clip(np.floor(fx).astype(int), 0, g.W - 2)
        ty = np.clip(fy - i0, 0, 1); tx = np.clip(fx - j0, 0, 1)
        A = self.A
        return ((A[i0, j0] * (1 - tx) + A[i0, j0 + 1] * tx) * (1 - ty) +
                (A[i0 + 1, j0] * (1 - tx) + A[i0 + 1, j0 + 1] * tx) * ty)
    def near(self, x, y):
        g = self.g
        i = np.clip(((np.asarray(y, float) - g.y0) / g.res).astype(int), 0, g.H - 1)
        j = np.clip(((np.asarray(x, float) - g.x0) / g.res).astype(int), 0, g.W - 1)
        return self.A[i, j]

def fmt(v, n=3):
    s = "%.*f" % (n, v)
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    if s.startswith("0."): s = s[1:]
    elif s.startswith("-0."): s = "-" + s[2:]
    return s if s not in ("", "-", "-0") else "0"

# --------------------------------------------------------------------------------------
# planar layer clipping
# --------------------------------------------------------------------------------------
def clip_planar(lines, P, THR, ws, ins, conf, tool_at_ws, THRhi=None):
    """Rewrite lines[ws:ins]: extrusion that lies above the skin's base is turned into
    non-extruding moves.  Original retract/prime moves are never dropped; extra
    retractions added around the dry moves are folded into them."""
    segs = P.segs
    sl = segs["line"]
    a = np.searchsorted(sl, ws); b = np.searchsorted(sl, ins)
    idx = np.arange(a, b)
    x0 = segs["x0"][idx]; y0 = segs["y0"][idx]; x1 = segs["x1"][idx]; y1 = segs["y1"][idx]; lz = segs["lz"][idx]
    Ls = np.hypot(x1 - x0, y1 - y0)
    n = np.maximum(1, np.ceil(Ls / 0.1).astype(int))
    rep = np.repeat(np.arange(len(idx)), n)
    k = np.arange(len(rep)) - np.repeat(np.cumsum(n) - n, n)
    t = (k + 0.5) / np.repeat(n, n)
    sx = x0[rep] + (x1 - x0)[rep] * t; sy = y0[rep] + (y1 - y0)[rep] * t
    flag = THR.near(sx, sy) < lz[rep] - 1e-4
    if THRhi is not None:   # never cut into material that stands clearly above the surface (ribs, walls)
        flag &= lz[rep] <= THRhi.near(sx, sy) + 1e-4
    starts = np.cumsum(n) - n
    nrem = np.add.reduceat(flag.astype(np.int64), starts) if len(starts) else np.zeros(0, np.int64)
    # per line: segments and their sample flags
    line_of = sl[idx]
    seg_info = {}
    for li in np.unique(line_of[nrem > 0]):
        seg_info[int(li)] = None
    seg_first = {}
    for j, li in enumerate(line_of):
        seg_first.setdefault(int(li), []).append(j)

    def runs_for_line(li):
        pieces = []
        for j in seg_first[li]:
            s0 = starts[j]; nn = n[j]
            f = flag[s0:s0 + nn]
            for q in range(nn):
                ta = q / nn; tb = (q + 1) / nn
                pa = (x0[j] + (x1[j] - x0[j]) * ta, y0[j] + (y1[j] - y0[j]) * ta)
                pb = (x0[j] + (x1[j] - x0[j]) * tb, y0[j] + (y1[j] - y0[j]) * tb)
                pieces.append((bool(f[q]), pa, pb, Ls[j] / nn))
        runs = []
        for kk, pa, pb, L in pieces:
            if runs and runs[-1][0] == kk:
                runs[-1][1].append(pb); runs[-1][2] += L
            else:
                runs.append([kk, [pa, pb], L])
        # short kept pieces next to removed ones are removed too (never the other way round:
        # material inside the clip zone must go)
        changed = True
        while changed and len(runs) > 1:
            changed = False
            for q, r in enumerate(runs):
                if r[2] < 0.3 and not r[0]:
                    r[0] = True; changed = True
            q = 0
            while q < len(runs) - 1:
                if runs[q][0] == runs[q + 1][0]:
                    runs[q][1].extend(runs[q + 1][1][1:]); runs[q][2] += runs[q + 1][2]; runs.pop(q + 1)
                else:
                    q += 1
        out = []
        for kk, pts, L in runs:      # drop collinear points
            keep = [pts[0]]
            for q in range(1, len(pts) - 1):
                (ax, ay), (bx, by), (cx, cy) = keep[-1], pts[q], pts[q + 1]
                if abs((bx - ax) * (cy - ay) - (by - ay) * (cx - ax)) > 1e-6 * max(1.0, math.hypot(cx - ax, cy - ay)):
                    keep.append(pts[q])
            keep.append(pts[-1])
            out.append((kk, keep, L))
        return out

    tool = tool_at_ws
    R_len = lambda tl: conf_list(conf, "filament_retract_length", tl, None) or conf_list(conf, "retract_length", tl, 0.8)
    R_spd = lambda tl: 60 * (conf_list(conf, "filament_retract_speed", tl, None) or conf_list(conf, "retract_speed", tl, 35))
    D_spd = lambda tl: 60 * (conf_list(conf, "filament_deretract_speed", tl, None) or conf_list(conf, "deretract_speed", tl, 0) or conf_list(conf, "retract_speed", tl, 35))
    travelF = 60 * (conf_list(conf, "travel_speed", 0, 150))
    out = []
    p_extra = 0.0          # retraction added by us, not yet undone
    orig_r = 0.0           # how far the original program is retracted (for the hand-over)
    curF = None; emF = None
    st = {"removed_e": 0.0, "kept_e": 0.0, "removed_len": 0.0, "dry_runs": 0}
    in_dry = False
    # remaining dry length look-ahead per line (for deciding to retract)
    def emit_F(code, F_in_line):
        nonlocal emF
        if F_in_line is not None:
            emF = F_in_line
            return code
        if curF is not None and emF != curF:
            emF = curF
            return code + " F" + fmt(curF, 3)
        return code
    def resolve_extra():
        nonlocal p_extra, emF
        if p_extra > 1e-6:
            out.append("G1 E%s F%s" % (fmt(p_extra, 5), fmt(D_spd(tool), 1))); emF = D_spd(tool)
            p_extra = 0.0
    for i in range(ws, ins):
        raw = lines[i]
        if not raw or raw[0] == ";":
            out.append(raw); continue
        code = raw.split(";", 1)[0].strip()
        if not code:
            out.append(raw); continue
        if code[0] == "T":
            m = re.match(r"^T(\d+)", code)
            resolve_extra()
            if m:
                tool = int(m.group(1))
            out.append(raw); continue
        if code.startswith("G91") or code.startswith("G28"):
            resolve_extra()
            out.append(raw); continue
        mo = P.motion.get(i)
        if mo is None:
            out.append(raw); continue
        head, p, mx0, my0, mx1, my1, rel = mo
        F = p.get("F")
        e = p.get("E")
        hasxy = (mx1 != mx0 or my1 != my0)
        if rel:
            resolve_extra()
            if e:
                orig_r = max(0.0, orig_r - e) if e > 0 else orig_r - e
            if F is not None: curF = F; emF = F
            out.append(raw); in_dry = False; continue
        if e is None or abs(e) < 1e-12:
            # travel / feed change
            if F is not None: curF = F
            if hasxy or "Z" in p:
                out.append(emit_F(code, F) if (hasxy or "Z" in p) else raw)
            else:
                out.append(raw); emF = F if F is not None else emF
            in_dry = False
            continue
        if not hasxy:
            # E-only move (retract / prime / flush): fold our extra retraction into it
            if F is not None: curF = F
            orig_r = max(0.0, orig_r - e) if e > 0 else min(10.0, orig_r - e)
            ee = e + p_extra; p_extra = 0.0
            if abs(ee) > 1e-6:
                out.append("G1 E%s F%s" % (fmt(ee, 5), fmt(F if F is not None else (R_spd(tool) if ee < 0 else D_spd(tool)), 1)))
                emF = F if F is not None else emF
            in_dry = False
            continue
        if e < 0:
            # wipe move with retraction
            if F is not None: curF = F
            orig_r = min(10.0, orig_r - e)
            a_ret = -e
            c = re.sub(r"\s+E-?\d*\.?\d+", "", code)
            if p_extra >= a_ret:
                p_extra -= a_ret
            else:
                c += " E" + fmt(-(a_ret - p_extra), 5); p_extra = 0.0
            out.append(emit_F(c, F)); in_dry = False
            continue
        # extrusion
        if F is not None: curF = F
        orig_r = 0.0
        if i not in seg_info:
            resolve_extra()
            out.append(emit_F(code, F)); st["kept_e"] += e; in_dry = False
            continue
        runs = runs_for_line(i)
        tot = sum(r[2] for r in runs) or 1.0
        if len(runs) == 1 and runs[0][0]:
            runs_iter = [(True, None, runs[0][2])]
        else:
            runs_iter = runs
        for kk, pts, L in runs_iter:
            if kk:
                st["removed_e"] += e * L / tot; st["removed_len"] += L
                if p_extra < 1e-6:
                    r = R_len(tool)
                    out.append("G1 E-%s F%s" % (fmt(r, 5), fmt(R_spd(tool), 1))); emF = R_spd(tool)
                    p_extra = r; st["dry_runs"] += 1
                if pts is None:   # whole line dry: keep its exact geometry (arcs included)
                    c = re.sub(r"\s+[EF]-?\d*\.?\d+", "", code)
                    out.append(c + " F" + fmt(travelF, 0)); emF = travelF
                else:
                    first = True
                    for q in pts[1:]:
                        c = "G1 X%s Y%s" % (fmt(q[0]), fmt(q[1]))
                        if first:
                            c += " F" + fmt(travelF, 0); emF = travelF; first = False
                        out.append(c)
                in_dry = True
            else:
                resolve_extra()
                st["kept_e"] += e * L / tot
                for qa, qb in zip(pts[:-1], pts[1:]):
                    segL = math.hypot(qb[0] - qa[0], qb[1] - qa[1])
                    c = "G1 X%s Y%s E%s" % (fmt(qb[0]), fmt(qb[1]), fmt(e * segL / tot, 5))
                    out.append(emit_F(c, None))
                in_dry = False
    st["end_retracted"] = orig_r + p_extra
    st["end_tool"] = tool
    st["end_F"] = curF
    return out, st

# --------------------------------------------------------------------------------------
# skin generation
# --------------------------------------------------------------------------------------
def hatch_lines(region, angle_deg, spacing):
    """parallel lines at angle covering region; returns rows (each: list of ((xa,ya),(xb,yb)))"""
    rot = affinity.rotate(region, -angle_deg, origin=(0, 0))
    minx, miny, maxx, maxy = rot.bounds
    nrow = int((maxy - miny) / spacing)
    off = ((maxy - miny) - nrow * spacing) / 2
    rows = []
    ca, sa = math.cos(math.radians(angle_deg)), math.sin(math.radians(angle_deg))
    back = lambda x, y: (x * ca - y * sa, x * sa + y * ca)
    for k in range(nrow + 1):
        yv = miny + off + k * spacing
        gi = rot.intersection(LineString([(minx - 1, yv), (maxx + 1, yv)]))
        segs = []
        for part in getattr(gi, "geoms", [gi]):
            if part.geom_type != "LineString" or part.length < 0.3:
                continue
            (xa, _), (xb, _) = part.coords[0], part.coords[-1]
            xa, xb = min(xa, xb), max(xa, xb)
            segs.append((xa, xb))
        segs.sort()
        rows.append((yv, segs, back))
    return rows

def order_monotonic(rows):
    ids = [(k, i) for k, (c, segs, _) in enumerate(rows) for i in range(len(segs))]
    def ov(a, b):
        return a[0] < b[1] - 0.05 and b[0] < a[1] - 0.05
    preds = {}
    for k, (c, segs, _) in enumerate(rows):
        for i, s in enumerate(segs):
            preds[(k, i)] = [(k - 1, j) for j, t in enumerate(rows[k - 1][1]) if ov(s, t)] if k > 0 else []
    def pt(k, a):
        c, _, back = rows[k]
        return back(a, c)
    done = set(); remaining = set(ids); out = []; pos = None; cur = None
    def ready(q):
        return all(p in done for p in preds[q])
    def dist_to(q):
        a, b = rows[q[0]][1][q[1]]
        return min(math.dist(pos, pt(q[0], a)), math.dist(pos, pt(q[0], b)))
    while remaining:
        cand = None
        if cur is not None:
            k, i = cur
            if k + 1 < len(rows):
                nxt = [(k + 1, j) for j, t in enumerate(rows[k + 1][1])
                       if (k + 1, j) in remaining and ov(rows[k][1][i], t) and ready((k + 1, j))]
                if nxt:
                    cand = min(nxt, key=dist_to)
        if cand is None:
            rd = [q for q in remaining if ready(q)]
            cand = min(rd) if pos is None else min(rd, key=dist_to)
        k, i = cand
        a, b = rows[k][1][i]
        pa, pb = pt(k, a), pt(k, b)
        if pos is not None and math.dist(pos, pb) < math.dist(pos, pa):
            pa, pb = pb, pa
        out.append((pa, pb)); pos = pb; cur = cand
        done.add(cand); remaining.discard(cand)
    return out

class SkinWriter:
    def __init__(self, ctx, start_xy, start_z, retracted, tool):
        self.c = ctx; self.g = []; self.pos = start_xy; self.z = start_z
        self.retracted = retracted; self.tool = tool
        self.e_total = 0.0; self.lifted = True
        conf = ctx["conf"]
        self.R = conf_list(conf, "filament_retract_length", tool, None) or conf_list(conf, "retract_length", tool, 0.8)
        self.RF = 60 * (conf_list(conf, "filament_retract_speed", tool, None) or conf_list(conf, "retract_speed", tool, 35))
        self.DF = 60 * (conf_list(conf, "filament_deretract_speed", tool, None) or conf_list(conf, "deretract_speed", tool, 0) or conf_list(conf, "retract_speed", tool, 35))
        self.TF = 60 * conf_list(conf, "travel_speed", 0, 150)
        self.vz = conf_list(conf, "machine_max_feedrate_z", 0, 12)
        self.ZF = 60 * min(self.vz, conf_list(conf, "travel_speed_z", 0, 0) or self.vz)
        d = conf_list(conf, "filament_diameter", tool, 1.75)
        self.fil_a = math.pi * (d / 2) ** 2
        self.em = conf_list(conf, "extrusion_multiplier", tool, 1.0)
        self.lift = ctx["lift"]; self.plow = ctx["plow"]
        self.S = ctx["S"]
        self.set_pass(0)
    def set_pass(self, k):
        self.Rq = self.c["R_pass"][k]; self.Hf = self.c["H_pass"][k]
    def surf(self, x, y):
        return float(self.S.at(x, y))
    def along(self, xa, ya, xb, yb):
        L = math.hypot(xb - xa, yb - ya)
        n = max(2, int(L / 0.25) + 1)
        t = np.linspace(0, 1, n)
        xs = xa + (xb - xa) * t; ys = ya + (yb - ya) * t
        return float(self.Hf.near(xs, ys).max()), float(self.Rq.near(xs, ys).max())
    def safe_z_along(self, xa, ya, xb, yb):
        h, r = self.along(xa, ya, xb, yb)
        return max(h + self.lift, r + 0.25)
    def retract(self):
        if self.retracted < self.R - 1e-6:
            self.g.append("G1 E-%s F%s" % (fmt(self.R - self.retracted, 5), fmt(self.RF, 0)))
            self.retracted = self.R
    def prime(self):
        if self.retracted > 1e-6:
            self.g.append("G1 E%s F%s" % (fmt(self.retracted, 5), fmt(self.DF, 0)))
            self.retracted = 0.0
    def travel(self, x, y, zt):
        d = math.dist(self.pos, (x, y))
        if d < 1e-6 and not self.lifted and abs(zt - self.z) < 1e-4:
            return
        if d < 1.5 and not self.lifted and self.retracted < 1e-6:
            h, r = self.along(self.pos[0], self.pos[1], x, y)
            if h <= min(self.z, zt) + self.plow - 0.04 and r <= min(self.z, zt) - 0.04:
                self.g.append("G1 X%s Y%s Z%s F%s" % (fmt(x), fmt(y), fmt(zt), fmt(self.TF, 0)))
                self.pos = (x, y); self.z = zt
                return
        self.retract()
        zs = max(self.safe_z_along(self.pos[0], self.pos[1], x, y), self.z, zt + self.lift)
        if zs > self.z + 1e-4:
            self.g.append("G1 Z%s F%s" % (fmt(zs), fmt(self.ZF, 0)))
        self.g.append("G1 X%s Y%s F%s" % (fmt(x), fmt(y), fmt(self.TF, 0)))
        self.g.append("G1 Z%s F%s" % (fmt(zt), fmt(self.ZF, 0)))
        self.pos = (x, y); self.z = zt; self.lifted = False
    def path(self, pts, zoff, thick_fn, width, feed, infill_spacing=None):
        x0, y0 = pts[0]
        self.travel(x0, y0, self.surf(x0, y0) + zoff)
        self.prime()
        first = True
        for (xa, ya), (xb, yb) in zip(pts[:-1], pts[1:]):
            L = math.hypot(xb - xa, yb - ya)
            if L < 1e-6:
                continue
            n = max(1, int(math.ceil(L / 1.0)))
            for q in range(1, n + 1):
                pxa = xa + (xb - xa) * (q - 1) / n; pya = ya + (yb - ya) * (q - 1) / n
                pxb = xa + (xb - xa) * q / n; pyb = ya + (yb - ya) * q / n
                th = thick_fn((pxa + pxb) / 2, (pya + pyb) / 2)
                area = infill_spacing * th if infill_spacing else th * (width - th * (1 - math.pi / 4))
                e = area * (L / n) / self.fil_a * self.em
                zb = self.surf(pxb, pyb) + zoff
                dz = abs(zb - self.z)
                f = feed
                if dz > 1e-6:
                    f = min(feed, 60 * self.vz * (L / n) / dz)
                c = "G1 X%s Y%s Z%s E%s" % (fmt(pxb), fmt(pyb), fmt(zb), fmt(e, 5))
                if first or abs(f - feed) > 1 or getattr(self, "_lastF", None) != f:
                    c += " F" + fmt(f, 0); self._lastF = f
                first = False
                self.g.append(c)
                self.e_total += e; self.z = zb
        self.pos = pts[-1]
    def lift_off(self):
        self.retract()
        zt = self.safe_z_along(self.pos[0], self.pos[1], self.pos[0], self.pos[1]) + 0.4
        if zt > self.z:
            self.g.append("G1 Z%s F%s" % (fmt(zt), fmt(self.ZF, 0))); self.z = zt
        self.lifted = True

def make_skin(ctx, regions, start_xy, start_z, retracted, tool, cfg):
    hf = fnum(cfg, "finish_layer_mm"); tmin = fnum(cfg, "min_level_layer_mm")
    Zs = ctx["Zs"]
    w_peri = 0.45; spacing = 0.38
    nd = conf_list(ctx["conf"], "nozzle_diameter", tool, 0.4)
    w_peri = round(nd * 1.125, 3); spacing = round(nd * 0.95, 3)
    S = ctx["S"]
    def base_top(x, y):
        s = S.at(x, y)
        thr = s - hf - tmin + 1e-4
        k = np.searchsorted(Zs, thr, side="right") - 1
        return Zs[max(k, 0)] if k >= 0 else 0.0
    def t_level(x, y):
        return max(tmin * 0.5, float(S.at(x, y)) - hf - base_top(x, y))
    t_finish = lambda x, y: hf
    W = SkinWriter(ctx, start_xy, start_z, retracted, tool)
    W.g.append("M204 P%s" % fmt(fnum(cfg, "skin_accel"), 0))
    spd = lambda k: 60 * fnum(cfg, k)
    # order regions nearest-first
    todo = list(regions); ordered = []
    pos = start_xy
    while todo:
        j = min(range(len(todo)), key=lambda q: todo[q]["poly"].exterior.distance(Point(pos)))
        r = todo.pop(j); ordered.append(r)
        c = r["poly"].centroid; pos = (c.x, c.y)
    stats = []
    for passno, (zoff, tfn, pf, inf_key, name) in enumerate([
            (-hf, t_level, "level_perimeter_speed", "level_infill_speed", "levelling pass"),
            (0.0, t_finish, "finish_perimeter_speed", "finish_infill_speed", "finish pass")]):
        W.set_pass(passno)
        for r in ordered:
            pg = r["poly"]
            W.g.append("; nonplanar skin: %s, region %d" % (name, r["id"]))
            if r.get("obj", -1) >= 0:
                W.g.append("M486 S%d" % r["obj"])
            W.g.append(";TYPE:Top solid infill")
            W.g.append(";WIDTH:%s" % fmt(w_peri))
            W.g.append(";HEIGHT:%s" % fmt(hf))
            e0 = W.e_total
            Q = pg.buffer(-w_peri / 2)
            rings = []
            for g in getattr(Q, "geoms", [Q]):
                for ring in [g.exterior] + list(g.interiors):
                    ring = ring.simplify(0.01)
                    if ring.length > 1.0:
                        rings.append(list(ring.coords))
            # rings nearest-first, starting at the closest vertex
            while rings:
                best = None
                for ri, rr in enumerate(rings):
                    a = np.array(rr[:-1]); d = np.hypot(a[:, 0] - W.pos[0], a[:, 1] - W.pos[1]); jj = int(d.argmin())
                    if best is None or d[jj] < best[0]:
                        best = (d[jj], ri, jj)
                _, ri, jj = best
                rr = rings.pop(ri)[:-1]; rr = rr[jj:] + rr[:jj] + [rr[jj]]
                W.path(rr, zoff, tfn, w_peri, spd(pf))
            region = pg.buffer(-(w_peri + spacing / 2 - 0.07))
            ang = r["angle"] + (90.0 if passno == 0 else 0.0)
            if not region.is_empty:
                rows = hatch_lines(region, ang, spacing)
                segs = order_monotonic(rows) if any(rw[1] for rw in rows) else []
                W.g.append(";WIDTH:%s" % fmt(spacing + 0.04))
                for pa, pb in segs:
                    W.path([pa, pb], zoff, tfn, spacing, spd(inf_key), infill_spacing=spacing)
            stats.append((name, r["id"], W.e_total - e0))
            W.lift_off()
            if r.get("obj", -1) >= 0:
                W.g.append("M486 S-1")
    return W, stats

# --------------------------------------------------------------------------------------
# verification
# --------------------------------------------------------------------------------------
def retraction_lint(lines):
    """counts extrusions while retracted (> 0.05 mm) and over-retractions"""
    r = 0.0; rel = False; bad = 0; over = 0; maxr = 0.0
    for raw in lines:
        if not raw or raw[0] not in "GT":
            continue
        code = raw.split(";", 1)[0]
        if code.startswith("G91"): rel = True; continue
        if code.startswith("G90"): rel = False; continue
        if code[0] == "T":
            continue
        if not (code.startswith("G1 ") or code.startswith("G0 ") or code.startswith("G2 ") or code.startswith("G3 ")):
            continue
        m = re.search(r"E(-?\d*\.?\d+)", code)
        if not m:
            continue
        e = float(m.group(1))
        xy = ("X" in code or "Y" in code)
        if e < 0:
            r -= e; maxr = max(maxr, r)
        elif xy and not rel:
            if r > 0.05:
                bad += 1
            r = 0.0
        else:
            r = max(0.0, r - e)
    return bad, maxr

def verify(out_lines, skin_range, ctx, regions_mask, cfg, grid, conf, P_in):
    """re-simulate the converted file; returns (ok, messages, numbers)"""
    msgs = []; num = {}
    P2 = parse_gcode(out_lines)
    s0, s1 = skin_range
    sl = P2.segs["line"]
    keep = (sl < s0) | (sl >= s1)
    planar = {k: v[keep] for k, v in P2.segs.items()}
    Hall2, Hpart2, _, _ = rasterize(planar, grid)
    S = ctx["S"].A
    hf = fnum(cfg, "finish_layer_mm")
    M = regions_mask
    # final geometry: planar material plus the skin up to the smooth surface
    plow = fnum(cfg, "plow_tolerance_mm")
    if os.environ.get("NPT_DEBUG"):
        np.savez_compressed(os.path.join(os.environ["NPT_DEBUG"], "verify.npz"), M=M, Hall2=Hall2, S=S, x0=grid.x0, y0=grid.y0, res=grid.res)
    w_fin_far = np.where(M, np.maximum(Hall2, S), Hall2).astype(np.float32)
    w_fin_near = np.where(M, np.maximum(Hall2, S - hf), Hall2).astype(np.float32)
    w_lev_far = w_fin_near
    w_lev_near = Hall2
    Rp = [np.maximum(required_nozzle_z(w_lev_far, grid, cfg, which="far")[0], required_nozzle_z(w_lev_near, grid, cfg, which="near")[0]),
          np.maximum(required_nozzle_z(w_fin_far, grid, cfg, which="far")[0], required_nozzle_z(w_fin_near, grid, cfg, which="near")[0])]
    Hp = [cv2.dilate(w_lev_far, disc(0.6 / grid.res)), cv2.dilate(w_fin_far, disc(0.6 / grid.res))]
    Hp_below = [cv2.dilate(Hall2, disc(0.6 / grid.res)), cv2.dilate(w_lev_far, disc(0.6 / grid.res))]
    # walk the skin moves
    x = y = z = 0.0
    for i in range(s0 - 1, -1, -1):
        mo = P2.motion.get(i)
        if mo and not mo[6]:
            x, y = mo[4], mo[5]
            break
    # z before skin
    for i in range(s0 - 1, -1, -1):
        raw = out_lines[i]
        if raw.startswith("G1") and " Z" in raw.split(";")[0]:
            z = float(re.search(r"Z(-?\d*\.?\d+)", raw.split(";")[0]).group(1)); break
    ext_pts = []; trav_pts = []
    passno = 0; pass_of = []
    cover = [np.zeros((grid.H, grid.W), np.uint8), np.zeros((grid.H, grid.W), np.uint8)]
    sc = 4 / grid.res
    for i in range(s0, s1):
        raw = out_lines[i]
        if raw.startswith("; nonplanar skin: levelling"): passno = 0
        elif raw.startswith("; nonplanar skin: finish"): passno = 1
        if not raw.startswith("G1"):
            continue
        p = {k: float(v) for k, v in NUM.findall(raw.split(";")[0][2:])}
        nx = p.get("X", x); ny = p.get("Y", y); nz = p.get("Z", z); e = p.get("E", 0.0)
        L = math.hypot(nx - x, ny - y)
        n = max(1, int(math.ceil(max(L, abs(nz - z)) / 0.25)))
        t = (np.arange(n) + 1.0) / n
        pts = np.stack([x + (nx - x) * t, y + (ny - y) * t, z + (nz - z) * t], 1)
        if e > 0 and L > 0:
            ext_pts.append(np.concatenate([pts, np.full((n, 1), passno)], 1))
            a = (int((x - grid.x0) * sc), int((y - grid.y0) * sc)); b = (int((nx - grid.x0) * sc), int((ny - grid.y0) * sc))
            cv2.line(cover[passno], a, b, 1, max(1, int(round(0.40 / grid.res))), cv2.LINE_8, 2)
        elif L > 0 or nz != z:
            trav_pts.append(np.concatenate([pts, np.full((n, 1), passno)], 1))
        x, y, z = nx, ny, nz
    E = np.concatenate(ext_pts) if ext_pts else np.zeros((0, 4))
    T = np.concatenate(trav_pts) if trav_pts else np.zeros((0, 4))
    ok = True
    # material under/next to the nozzle while printing (nozzle flat radius 0.6)
    Hpl_n = cv2.dilate(Hall2, disc(0.6 / grid.res))
    num["skin_points"] = int(len(E))
    if len(E):
        pen1 = Field(Hpl_n, grid).near(E[:, 0], E[:, 1]) - E[:, 2]
        num["max_plow_into_layers_mm"] = float(pen1.max())
        if pen1.max() > 0.15:
            ok = False; msgs.append("nozzle would dig %.2f mm into the layers below the skin" % pen1.max())
        worst = -1e9
        for k in (0, 1):
            sel = E[:, 3] == k
            if sel.any():
                dd = Field(Rp[k], grid).near(E[sel, 0], E[sel, 1]) - E[sel, 2]
                if dd.max() > worst:
                    worst = float(dd.max()); j = int(dd.argmax())
                    num["head_clearance_worst_at"] = "pass %d  X%.2f Y%.2f Z%.3f" % (k, E[sel][j, 0], E[sel][j, 1], E[sel][j, 2])
                    num["head_clearance_count_short"] = int((dd > 0.02).sum())
        num["head_clearance_worst_mm"] = -worst
        if worst > 0.02:
            ok = False; msgs.append("toolhead clearance too small while printing the skin (short by %.2f mm)" % worst)
    if len(T):
        worst = -1e9
        for k in (0, 1):
            sel = T[:, 3] == k
            if sel.any():
                tx, ty, tz = T[sel, 0], T[sel, 1], T[sel, 2]
                d1 = Field(Rp[k], grid).near(tx, ty) - tz
                # at surface height (short hops, landing on the next line) the nozzle rides on the
                # layer below, like it does while printing; higher up it must clear everything
                surf_z = Field(S, grid).at(tx, ty) - (hf if k == 0 else 0.0)
                low = tz < surf_z + 0.05
                d2 = np.where(low, Field(Hp_below[k], grid).near(tx, ty), Field(Hp[k], grid).near(tx, ty)) - tz - plow
                dm = np.maximum(d1, d2)
                if dm.max() > worst:
                    worst = float(dm.max()); j = int(dm.argmax())
                    num["travel_worst_at"] = "pass %d X%.2f Y%.2f Z%.3f (head %.3f, material %.3f)" % (
                        k, T[sel][j, 0], T[sel][j, 1], T[sel][j, 2], d1[j], d2[j])
        num["travel_clearance_worst_mm"] = -worst
        if worst > 0.02:
            ok = False; msgs.append("a travel move over the skin is too low (by %.2f mm)" % worst)
    Me = cv2.erode(M.astype(np.uint8), ell(0.25, grid.res)).astype(bool)
    if Me.any():
        c0 = float((cover[0] > 0)[Me].mean()); c1 = float((cover[1] > 0)[Me].mean())
        num["coverage_levelling"] = c0; num["coverage_finish"] = c1
        if min(c0, c1) < 0.985:
            ok = False; msgs.append("skin does not cover the region (%.1f%% / %.1f%%)" % (100 * c0, 100 * c1))
    bad_in, maxr_in = retraction_lint(ctx["lines_in"])
    bad_out, maxr_out = retraction_lint(out_lines)
    num["retraction_issues_in_out"] = (bad_in, bad_out)
    if bad_out > bad_in:
        ok = False; msgs.append("retraction bookkeeping error (%d extrusions while retracted)" % (bad_out - bad_in))
    if maxr_out > max(maxr_in, 1.0) * 1.5 + 0.01:
        ok = False; msgs.append("over-retraction %.2f mm" % maxr_out)
    # feed rates in everything we wrote (clipped layers + skin)
    fr = []
    for raw in out_lines[ctx["ws"]:s1]:
        if raw.startswith("G1") or raw.startswith("G0") or raw.startswith("G2") or raw.startswith("G3"):
            m = re.search(r"\bF(-?\d*\.?\d+)", raw.split(";")[0])
            if m:
                fr.append(float(m.group(1)))
    if fr:
        orig_low = set()
        for raw in ctx["lines_in"]:
            if raw[:2] in ("G0", "G1", "G2", "G3"):
                m = re.search(r"\bF(-?\d*\.?\d+)", raw.split(";")[0])
                if m and float(m.group(1)) < 100:
                    orig_low.add(float(m.group(1)))
        new_low = [f for f in fr if f < 100 and f not in orig_low]
        num["feedrate_range_mm_min"] = (min(fr), max(fr))
        if new_low or max(fr) > 60000:
            ok = False; msgs.append("feed rate out of range (%s)" % (new_low[:3] or max(fr)))
    zmax = float(E[:, 2].max()) if len(E) else 0
    num["skin_z_range"] = (float(E[:, 2].min()) if len(E) else 0, zmax)
    if zmax > ctx["max_z"] + 0.05:
        ok = False; msgs.append("skin goes above the top of the print")
    return ok, msgs, num

# --------------------------------------------------------------------------------------
# main conversion
# --------------------------------------------------------------------------------------
class Skip(Exception):
    """nothing to do / not applicable (file left unchanged)"""

class Unsafe(Exception):
    """conversion produced something that failed the safety checks"""

def last_before(d, idx, default):
    best = None
    for k in d:
        if k < idx and (best is None or k > best):
            best = k
    return d[best] if best is not None else default

def convert(text, conf, cfg, log):
    t0 = time.time()
    lines = text.split("\n")
    if conf.get("use_relative_e_distances", "1") != "1":
        raise Skip("needs relative E distances (Printer Settings > General > Advanced)")
    if conf.get("complete_objects", "0") == "1":
        raise Skip("sequential (one object at a time) printing is not supported")
    if conf.get("spiral_vase", "0") == "1":
        raise Skip("spiral vase mode")
    hf = fnum(cfg, "finish_layer_mm"); tmin = fnum(cfg, "min_level_layer_mm")
    P = parse_gcode(lines)
    if P.last_ext < 0 or len(P.segs["lz"]) == 0:
        raise Skip("no extrusion found")
    log("parsed %d lines, %d extrusion segments, %d layers (%.1fs)" % (len(lines), len(P.segs["lz"]), len(P.layers), time.time() - t0))
    sg = P.segs
    okb = (sg["x0"] > -20) & (sg["y0"] > -20)
    xmin = float(min(sg["x0"][okb].min(), sg["x1"][okb].min())) - 3; xmax = float(max(sg["x0"][okb].max(), sg["x1"][okb].max())) + 3
    ymin = float(min(sg["y0"][okb].min(), sg["y1"][okb].min())) - 3; ymax = float(max(sg["y0"][okb].max(), sg["y1"][okb].max())) + 3
    grid = Grid(xmin, ymin, xmax, ymax, 0.1)
    Zs = np.unique(np.round(sg["lz"], 4))
    max_z = float(Zs.max())
    Hall, Hpart, toolm, objm = rasterize(sg, grid)
    log("rasterised %dx%d grid (%.1fs)" % (grid.W, grid.H, time.time() - t0))
    S, L, cliff, steep = reconstruct_surface(Hpart, grid, Zs)
    # slope over a 0.6 mm baseline (single-pixel kinks of a few microns are irrelevant)
    Sd = S.astype(np.float64); kb = 3
    Spad = np.pad(Sd, kb, mode="edge")
    gx = (Spad[kb:-kb, 2 * kb:] - Spad[kb:-kb, :-2 * kb]) / (2 * kb * grid.res)
    gy = (Spad[2 * kb:, kb:-kb] - Spad[:-2 * kb, kb:-kb]) / (2 * kb * grid.res)
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    has = Hpart > 0
    top = has & (Hall <= Hpart + 1e-3)
    ei = fnum(cfg, "edge_inset_mm")
    inset = ndi.binary_dilation(cliff, structure=ell(ei, grid.res).astype(bool)) if ei > 0 else cliff
    # slope over a small neighbourhood (ignore single-pixel noise)
    slope_s = np.where(has, slope, 90)
    C0 = top & ~steep & (slope_s <= fnum(cfg, "max_slope_deg")) & ~inset
    C0 = cv2.morphologyEx(C0.astype(np.uint8), cv2.MORPH_CLOSE, ell(0.25, grid.res)).astype(bool) & top & ~inset
    C0 = cv2.morphologyEx(C0.astype(np.uint8), cv2.MORPH_OPEN, ell(0.5, grid.res)).astype(bool)
    min_px = fnum(cfg, "min_region_area_mm2") / grid.res ** 2
    C0 = remove_small(C0, min_px)
    C0 = fill_small_holes(C0, 1.0 / grid.res ** 2)
    if not C0.any():
        raise Skip("no shallow top surfaces found")
    log("candidate area %.0f mm2 (%.1fs)" % (C0.sum() * grid.res ** 2, time.time() - t0))
    Sf = S.astype(np.float32)
    BAND = 0.8      # planar material this close outside a region is lowered below the skin (nozzle cone clearance)
    w_peri_half = 0.225
    def worlds(C, Hbase, Craw=None):
        """required nozzle heights for the finish and levelling passes, with the skin
        surface inside C and Hbase (planar material) everywhere else"""
        fin_far = np.where(C, np.maximum(Sf, Hbase if Craw is None else Sf), Hbase).astype(np.float32)
        fin_near = np.where(C, Sf - hf, Hbase).astype(np.float32)
        lev_far = np.where(C, Sf - hf, Hbase).astype(np.float32)
        lev_near = np.where(C, np.minimum(Sf - hf - tmin, Hbase), Hbase).astype(np.float32)
        R_fin = np.maximum(required_nozzle_z(fin_far, grid, cfg, which="far")[0], required_nozzle_z(fin_near, grid, cfg, which="near")[0])
        R_lev = np.maximum(required_nozzle_z(lev_far, grid, cfg, which="far")[0], required_nozzle_z(lev_near, grid, cfg, which="near")[0])
        return R_fin, R_lev, fin_far
    # first estimate: candidate surface everywhere it could be
    band0 = ndi.binary_dilation(C0, structure=ell(BAND + 0.25, grid.res).astype(bool)) & ~C0
    Hbase0 = np.where(band0, np.minimum(Hall, Sf - hf), Hall).astype(np.float32)   # what clipping will leave
    R_fin, R_lev, _ = worlds(C0, Hbase0)
    C0reach = cv2.erode(C0.astype(np.uint8), ell(0.2, grid.res)).astype(bool)
    viol = C0reach & ((Sf < R_fin + 0.02) | (Sf - hf < R_lev + 0.02))
    viol_total = viol.copy()
    C = C0 & ~ndi.binary_dilation(viol, structure=ell(0.5, grid.res).astype(bool))
    # insertion point and tool at the end of the print
    ins = None
    for i in range(P.last_ext + 1, len(lines)):
        c = lines[i].split(";", 1)[0].strip()
        if c == "M107" or lines[i].startswith(";TYPE:Custom"):
            ins = i; break
    if ins is None:
        raise Skip("could not find the end of the print")
    end_tool = last_before(P.tool_at, ins, 0)

    def make_regions(C, quiet=False):
        C = cv2.morphologyEx(C.astype(np.uint8), cv2.MORPH_OPEN, ell(0.5, grid.res)).astype(bool)
        C = remove_small(C, min_px)
        C = fill_small_holes(C, 1.0 / grid.res ** 2) & C0
        lab, n = ndi.label(C)
        regions = []; notes = []
        for k in range(1, n + 1):
            mk = lab == k
            lv = np.unique(L[mk]); lv = lv[lv >= 0]
            if len(lv) < int(fnum(cfg, "min_levels")):
                notes.append("an area of %.0f mm2 skipped: flat (crosses only %d layer)" % (mk.sum() * grid.res ** 2, len(lv)))
                continue
            tools = toolm[mk]; tools = tools[tools >= 0]
            if len(tools) == 0:
                continue
            tv, tc = np.unique(tools, return_counts=True)
            if tv[tc.argmax()] != end_tool or tc.max() < 0.99 * len(tools):
                notes.append("an area of %.0f mm2 skipped: its top is printed with T%d but the print ends on T%d"
                             % (mk.sum() * grid.res ** 2, tv[tc.argmax()], end_tool))
                continue
            ov, oc = np.unique(objm[mk], return_counts=True)
            obj = int(ov[oc.argmax()])
            for pg in mask_to_polygons(mk, grid):
                if pg.area < fnum(cfg, "min_region_area_mm2"):
                    continue
                fd = cfg["finish_direction"].strip().lower()
                if fd == "x": ang = 0.0
                elif fd == "y": ang = 90.0
                elif fd == "auto":
                    rr = pg.minimum_rotated_rectangle
                    cs = list(rr.exterior.coords)
                    e1 = (cs[1][0] - cs[0][0], cs[1][1] - cs[0][1]); e2 = (cs[2][0] - cs[1][0], cs[2][1] - cs[1][1])
                    e = e1 if math.hypot(*e1) >= math.hypot(*e2) else e2
                    ang = math.degrees(math.atan2(e[1], e[0]))
                    if abs(ang % 90) < 3 or abs(ang % 90) > 87:
                        ang = round(ang / 90) * 90.0
                    ang = ang % 180.0
                else:
                    ang = float(fd)
                regions.append({"poly": pg, "id": len(regions) + 1, "obj": obj, "angle": ang,
                                "levels": len(lv), "zrange": (float(S[mk].min()), float(S[mk].max())),
                                "slope_max": float(np.percentile(slope[cv2.erode(mk.astype(np.uint8), ell(0.5, grid.res)).astype(bool) | (~mk.any())], 99.5)) if mk.sum() > 400 else float(slope[mk].max())})
        if not quiet:
            for m_ in notes:
                log(m_)
        return regions, notes

    # iterate: clip, look at the real remaining geometry, shrink where the head would not clear
    for it in range(4):
        regions, notes = make_regions(C, quiet=it > 0)
        if not regions:
            why = list(notes)
            if viol_total.any():
                why.append("toolhead/shroud clearance excluded %.0f mm2 (tall parts nearby, or shroud_height_mm too small)"
                           % (viol_total.sum() * grid.res ** 2))
            raise Skip("; ".join(why) if why else "no usable regions")
        polys = [r["poly"] for r in regions]
        M = rasterize_polys(polys, grid); D = rasterize_polys(polys, grid, BAND + 0.25)   # + half a line width
        # outside a region, only lower what the nozzle cone would touch while printing the
        # levelling pass along the region edge (judged from the nearest point of the region)
        dist, (ii, jj) = ndi.distance_transform_edt(~M, return_indices=True)
        dist = dist * grid.res
        S_edge = Sf[ii, jj]
        starts = np.array([a for a, b, h in INDX_FINE]); hts = np.array([h for a, b, h in INDX_FINE])
        # (decided on line centres, so allow for half a line width reaching towards the region)
        cone = hts[np.clip(np.searchsorted(starts, np.maximum(dist - 0.3, 0), side="right") - 1, 0, len(hts) - 1)]
        THRb = (S_edge - hf + cone - 0.03).astype(np.float32)
        THR = np.where(M, Sf - hf - tmin, np.where(D, THRb, np.inf)).astype(np.float32)
        minTHR = float(THR[D].min())
        ws = None
        for li, z, h in P.layers:
            if z > minTHR + 1e-4:
                ws = li; break
        if ws is None or ws >= ins:
            raise Skip("nothing to remove")
        tool_ws = last_before(P.tool_at, ws, 0)
        THRhi = np.where(M, np.inf, np.maximum(Sf, S_edge) + 0.3).astype(np.float32)
        clipped, st = clip_planar(lines, P, Field(THR, grid), ws, ins, conf, tool_ws, Field(THRhi, grid))
        Pc = parse_gcode(lines[:ws] + clipped)
        Hall2, _, _, _ = rasterize(Pc.segs, grid)
        R_fin, R_lev, Hf = worlds(M, Hall2)
        Mreach = cv2.erode(M.astype(np.uint8), ell(0.2, grid.res)).astype(bool)   # where the nozzle centre goes
        viol = Mreach & ((Sf < R_fin + 0.02) | (Sf - hf < R_lev + 0.02))
        if os.environ.get("NPT_DEBUG"):
            Rfn = required_nozzle_z(np.where(M, Sf - hf, Hall2).astype(np.float32), grid, cfg, which="near")[0]
            Rff = required_nozzle_z(Hf, grid, cfg, which="far")[0]
            np.savez_compressed(os.path.join(os.environ["NPT_DEBUG"], "it%d.npz" % it), M=M, D=D, THR=THR, Hall2=Hall2, S=Sf, R_fin=R_fin,
                                R_lev=R_lev, viol=viol, Rfn=Rfn, Rff=Rff, x0=grid.x0, y0=grid.y0, res=grid.res)
        if not viol.any():
            break
        viol_total |= viol
        log("pass %d: shrinking regions by %.1f mm2 for toolhead clearance" % (it + 1, viol.sum() * grid.res ** 2))
        C = M & C0 & ~ndi.binary_dilation(viol, structure=ell(1.0, grid.res).astype(bool))
    else:
        raise Unsafe("could not find regions that keep the toolhead clear")
    if viol_total.any():
        log("toolhead clearance excluded %.0f mm2 of shallow surface" % (viol_total.sum() * grid.res ** 2))
    viol = viol_total
    log("removed %.1f mm of filament (%.1f m of path) from the top layers (%.1fs)" % (st["removed_e"], st["removed_len"] / 1000, time.time() - t0))
    # hand-over state
    sx = sy = None
    for i in range(ins - 1, -1, -1):
        mo = P.motion.get(i)
        if mo and not mo[6]:
            sx, sy = mo[4], mo[5]; break
    sz = max_z
    for i in range(ins - 1, -1, -1):
        c = lines[i].split(";", 1)[0]
        if c.startswith("G1") or c.startswith("G0"):
            m = re.search(r"\bZ(-?\d*\.?\d+)", c)
            if m:
                sz = float(m.group(1)); break
    m204 = None
    for i in range(ins - 1, -1, -1):
        c = lines[i].split(";", 1)[0].strip()
        if c.startswith("M204"):
            m204 = c; break
    plow = fnum(cfg, "plow_tolerance_mm")
    H_lev = np.where(M, np.maximum(Sf - hf, Hall2), Hall2).astype(np.float32)
    H_fin = np.where(M, np.maximum(Sf, Hall2), Hall2).astype(np.float32)
    dil = lambda A: cv2.dilate(A, disc(0.6 / grid.res))
    ctx = {"conf": conf, "S": Field(Sf, grid), "Zs": Zs, "lift": fnum(cfg, "travel_lift_mm"), "plow": plow,
           "R_pass": [Field(R_lev, grid), Field(R_fin, grid)],
           "H_pass": [Field(dil(H_lev), grid), Field(dil(H_fin), grid)],
           "lines_in": lines, "max_z": max_z, "ws": ws}
    W, stats = make_skin(ctx, regions, (sx, sy), sz, st["end_retracted"], end_tool, cfg)
    skin = ["; ===== nonplanar_top %s: skin start =====" % VERSION] + W.g
    if m204: skin.append(m204)
    skin.append("; ===== nonplanar_top: skin end =====")
    out_lines = lines[:ws] + clipped + skin + lines[ins:]
    s0 = ws + len(clipped); s1 = s0 + len(skin)
    log("skin: %d moves, %.1f mm of filament (%.1fs)" % (len(W.g), W.e_total, time.time() - t0))
    ratio = W.e_total / max(st["removed_e"], 1e-6)
    ok, msgs, numbers = verify(out_lines, (s0, s1), ctx, M, cfg, grid, conf, P)
    log("verification: %s (%.1fs)" % ("passed" if ok else "FAILED", time.time() - t0))
    for k, v in numbers.items():
        log("   %s: %s" % (k, v))
    if not (0.6 < ratio < 1.5):
        ok = False; msgs.append("filament balance looks wrong (skin %.0f mm vs removed %.0f mm)" % (W.e_total, st["removed_e"]))
    if not ok:
        raise Unsafe("; ".join(msgs))
    # filament totals
    de = W.e_total - st["removed_e"]
    for i in range(len(out_lines) - 1, max(len(out_lines) - 400, 0), -1):
        l = out_lines[i]
        if l.startswith("; filament used [mm] ="):
            vals = [v.strip() for v in l.split("=", 1)[1].split(",")]
            if end_tool < len(vals):
                try:
                    vals[end_tool] = "%.2f" % (float(vals[end_tool]) + de)
                    out_lines[i] = "; filament used [mm] = " + ", ".join(vals)
                except ValueError:
                    pass
    summary = {"regions": regions, "removed_e": st["removed_e"], "skin_e": W.e_total, "numbers": numbers,
               "seconds": time.time() - t0, "grid": grid, "S": S, "M": M, "Hpart": Hpart, "viol": viol, "C0": C0}
    hdr = ["; nonplanar_top %s: %d region(s) smoothed, shroud height setting %s mm, max slope setting %s deg"
           % (VERSION, len(regions), cfg["shroud_height_mm"], cfg["max_slope_deg"])]
    for r in regions:
        hdr.append("; nonplanar_top: region %d  %.0f mm2  Z %.2f..%.2f  steepest %.1f deg  finish lines at %.0f deg"
                   % (r["id"], r["poly"].area, r["zrange"][0], r["zrange"][1], r["slope_max"], r["angle"]))
    return "\n".join(hdr + out_lines), summary

def debug_image(summary, path):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    g = summary["grid"]; Hp = summary["Hpart"]
    ext = [g.x0, g.x0 + g.W * g.res, g.y0, g.y0 + g.H * g.res]
    fig, ax = plt.subplots(figsize=(14, 9))
    ax.imshow(np.where(Hp > 0, Hp, np.nan), origin="lower", extent=ext, cmap="Greys")
    ax.contour(np.where(summary["viol"], 1, 0), levels=[0.5], origin="lower", extent=ext, colors="red", linewidths=0.6)
    for r in summary["regions"]:
        pg = r["poly"]
        ax.plot(*pg.exterior.xy, color="#1f6fb2", lw=1)
        for h in pg.interiors:
            ax.plot(*h.xy, color="#1f6fb2", lw=0.8)
        c = pg.representative_point(); ax.text(c.x, c.y, str(r["id"]), color="#1f6fb2")
    ax.set_aspect("equal"); ax.set_title("blue: smoothed regions   red: excluded by toolhead clearance")
    plt.tight_layout(); plt.savefig(path, dpi=90); plt.close(fig)

def main(argv=None):
    ap = argparse.ArgumentParser(description="Smooth shallow top surfaces of PrusaSlicer G-code (nonplanar skin).")
    ap.add_argument("input")
    ap.add_argument("-o", "--output", help="output file (standalone use). Default: <input>_nonplanar.gcode")
    ap.add_argument("--force", action="store_true", help="convert even if the print profile notes do not ask for it")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE", help="override a setting")
    args = ap.parse_args(argv)
    in_slicer = "SLIC3R_PP_OUTPUT_NAME" in os.environ and not args.output
    logbuf = []
    def log(m):
        logbuf.append(m)
        print(m)
    def write_log():
        try:
            with open(LOG_PATH, "w", encoding="utf-8") as f:
                f.write("nonplanar_top %s  %s\ninput: %s\n" % (VERSION, time.strftime("%Y-%m-%d %H:%M:%S"), args.input))
                f.write("\n".join(logbuf) + "\n")
        except OSError:
            pass
    path = args.input
    with open(path, "rb") as f:
        magic = f.read(4)
    binary = magic == b"GCDE"
    if binary:
        _, conf = bgcode_to_ascii(path, metadata_only=True)
    else:
        sz = os.path.getsize(path)
        with open(path, "rb") as f:
            f.seek(max(0, sz - 600000))
            conf = ascii_config(f.read().decode("utf-8", "replace"))
    notes = conf.get("notes", "")
    cfg = load_settings(notes)
    for kv in args.set:
        k, v = kv.split("=", 1); cfg[k.strip()] = v.strip()
    if cfg["activate"].strip().lower() != "always" and "nonplanar" not in notes.lower() and not args.force:
        if not in_slicer:
            print("Not converting: the print profile notes do not contain 'nonplanar' (use --force to convert anyway).")
        return 0
    if _IMPORT_ERROR is not None:
        msg = ("nonplanar_top: missing Python package (%s). Install with:\n"
               "  pip install numpy scipy shapely opencv-python" % _IMPORT_ERROR)
        sys.stderr.write(msg + "\n")
        return 1
    try:
        if binary:
            text, conf = bgcode_to_ascii(path)
        else:
            text = open(path, "r", encoding="utf-8", errors="surrogateescape").read()
        text = text.replace("\r\n", "\n")
        log("nonplanar_top %s - %s" % (VERSION, os.path.basename(path)))
        log("settings: shroud_height_mm=%s max_slope_deg=%s safety_margin_mm=%s" % (cfg["shroud_height_mm"], cfg["max_slope_deg"], cfg["safety_margin_mm"]))
        out_text, summary = convert(text, conf, cfg, log)
    except Skip as e:
        log("No changes made: %s" % e)
        write_log()
        return 0
    except Unsafe as e:
        log("NOT CONVERTED - safety check failed: %s" % e)
        write_log()
        if cfg["on_unsafe"].strip().lower() == "error":
            sys.stderr.write("nonplanar_top: not converted, safety check failed:\n%s\n(details: %s)\n" % (e, LOG_PATH))
            return 1
        return 0
    except Exception:
        log("CRASH:\n" + traceback.format_exc())
        write_log()
        sys.stderr.write("nonplanar_top crashed - see %s\n%s\n" % (LOG_PATH, traceback.format_exc().splitlines()[-1]))
        return 1
    # write
    if in_slicer:
        out_path = path
        with open(out_path, "w", encoding="utf-8", errors="surrogateescape", newline="\n") as f:
            f.write(out_text)
        if binary:
            on = os.environ.get("SLIC3R_PP_OUTPUT_NAME", "")
            base = re.sub(r"\.bgcode$", "", on, flags=re.I) + ".gcode"
            with open(path + ".output_name", "w", encoding="utf-8") as f:
                f.write(base + "\n")
            log("binary G-code input: written as plain G-code, renamed to %s" % os.path.basename(base))
    else:
        out_path = args.output or re.sub(r"\.(b?gcode)$", "", path, flags=re.I) + "_nonplanar.gcode"
        with open(out_path, "w", encoding="utf-8", errors="surrogateescape", newline="\n") as f:
            f.write(out_text)
        log("written %s" % out_path)
    if cfg.get("debug_image", "0") == "1":
        debug_image(summary, os.path.join(SCRIPT_DIR, "nonplanar_top_last.png"))
    write_log()
    return 0

if __name__ == "__main__":
    sys.exit(main())

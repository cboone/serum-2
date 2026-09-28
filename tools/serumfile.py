#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["cbor2==6.1.4", "zstandard==0.25.0"]
# ///
"""
serumfile.py: read, write, inspect and diff Serum 2 files (.SerumPreset, .XferShape).

Both file types share one container, reverse-engineered from Serum 2.1.5 files:

    b"XferJson\\0"                      9 bytes, magic
    <Q  header_len                      little-endian uint64
    header JSON (header_len bytes)      compact JSON, keys in Serum's order;
                                        "hash" = MD5 hex of the compressed block below
    <I  raw_len                         length of the *uncompressed* CBOR body
    <I  fmt                             always 2 so far
    zstd frame                          compressed CBOR body (content size written, no checksum)

Serum checks the hash, so any edited file must get a fresh MD5 of its new zstd block;
write() does this. The CBOR encoder below reproduces Serum's own bytes exactly
(verified byte-for-byte on all 18 factory curves, user-drawn curves and saved
presets): definite-length maps/arrays in insertion order, text keys, and floats stored
as float32 when that is exact, else float64 (never float16). Serum's zstd settings are
NOT reproduced exactly for presets (the compressed bytes differ), but Serum loads our
level-3 frames without complaint; for curve files level 3 happened to match exactly.

Run it with uv, which installs the pinned cbor2 and zstandard from the PEP 723
block above, hash-checked against serumfile.py.lock: `tools/serumfile.py ...`.
The pins are exact because the byte-for-byte encoding, the zstd output and the
committed fixtures all depend on these libraries. To import it from another
script, give that script the same pins in its own PEP 723 block, put tools/ on
PYTHONPATH, and run it with `uv run --script`.

CLI:
    serumfile.py verify     FILE              hash and CBOR round-trip checks (exit 1 on failure)
    serumfile.py dump       FILE [OUT.json]   whole body as JSON
    serumfile.py matrix     FILE              readable mod-matrix listing (presets)
    serumfile.py rowcurves  FILE [CURVE_DIR]  name the curve file in each row (default serum/Curves)
    serumfile.py diff       A B               every differing leaf between two files
    serumfile.py curve      FILE              point list of a .XferShape curve

In `matrix` and `rowcurves` output, macros, oscillators and FX slots use the UI's
numbering (macros count from 1, oscillators are A, B, C, Noise, Sub, and FX slots
count from 1 in rack order), although the file stores them 0-based.
"""

import glob
import hashlib
import json
import os
import struct
import sys

import cbor2
import zstandard

MAGIC = b"XferJson\x00"
# The committed curve files; rowcurves compares rows against these by default.
REPO_CURVES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "serum", "Curves")


# ---------------------------------------------------------------- container I/O
def read(path):
    """Return (header: dict, fmt: int, body: object) for a Serum XferJson file."""
    with open(path, "rb") as f:
        d = f.read()
    if d[:9] != MAGIC:
        raise ValueError(f"{path}: not an XferJson file")
    n = struct.unpack("<Q", d[9:17])[0]
    header = json.loads(d[17 : 17 + n])
    raw_len, fmt = struct.unpack("<II", d[17 + n : 25 + n])
    comp = d[25 + n :]
    raw = zstandard.ZstdDecompressor().decompress(comp, max_output_size=64 * 2**20)
    if len(raw) != raw_len:
        raise ValueError(f"{path}: length field {raw_len} != decompressed {len(raw)}")
    return header, fmt, cbor2.loads(raw)


def hash_ok(path):
    with open(path, "rb") as f:
        d = f.read()
    n = struct.unpack("<Q", d[9:17])[0]
    return hashlib.md5(d[25 + n :]).hexdigest() == json.loads(d[17 : 17 + n]).get("hash")


# ---------------------------------------------------------------- CBOR encoder
def _head(major, n):
    if n < 24:
        return bytes([major << 5 | n])
    if n < 256:
        return bytes([major << 5 | 24, n])
    if n < 65536:
        return bytes([major << 5 | 25]) + struct.pack(">H", n)
    if n < 2**32:
        return bytes([major << 5 | 26]) + struct.pack(">I", n)
    return bytes([major << 5 | 27]) + struct.pack(">Q", n)


def encode(o):
    """CBOR-encode the way Serum does (see module docstring)."""
    if o is None:
        return b"\xf6"
    if isinstance(o, bool):  # must precede int (bool is an int)
        return b"\xf5" if o else b"\xf4"
    if isinstance(o, int):
        return _head(0, o) if o >= 0 else _head(1, -1 - o)
    if isinstance(o, float):
        f32 = struct.pack(">f", o)
        if struct.unpack(">f", f32)[0] == o:  # exactly representable -> float32
            return b"\xfa" + f32
        return b"\xfb" + struct.pack(">d", o)
    if isinstance(o, str):
        b = o.encode()
        return _head(3, len(b)) + b
    if isinstance(o, (bytes, bytearray)):
        return _head(2, len(o)) + bytes(o)
    if isinstance(o, (list, tuple)):
        return _head(4, len(o)) + b"".join(encode(x) for x in o)
    if isinstance(o, dict):
        return _head(5, len(o)) + b"".join(encode(k) + encode(v) for k, v in o.items())
    raise TypeError(f"cannot encode {type(o)}")


def write(path, header, body, fmt=2):
    """Write a Serum file with a correct hash. `header` is copied; its hash is replaced."""
    raw = encode(body)
    comp = zstandard.ZstdCompressor(
        level=3, write_content_size=True, write_checksum=False
    ).compress(raw)
    hdr = dict(header)
    hdr["hash"] = hashlib.md5(comp).hexdigest()
    hj = json.dumps(hdr, separators=(",", ":")).encode()
    data = MAGIC + struct.pack("<Q", len(hj)) + hj + struct.pack("<II", len(raw), fmt) + comp
    with open(path, "wb") as f:
        f.write(data)
    return data


# ---------------------------------------------------------------- curves (.XferShape)
CURVE_META = {
    "fileType": "XferShape",
    "product": "Serum2",
    "productVersion": "2.1.5",
    "url": "https://xferrecords.com/",
    "vendor": "Xfer Records",
    "version": 11.0,
}


def make_curve(points, curve_vals=None):
    """
    Build (header, body) for a matrix-row curve.

    points: list of (x, value) with x in [0, 1] ascending, starting at x = 0 and ending
            at x = 1, value in [0, 1] where 1 = TOP of Serum's editor.
            Serum stores y measured from the top, so y = 1 - value (done here).
            The last entry (x = 1) is the fixed endpoint; numPoints = len(points) - 1,
            which matches every factory file.
    curve_vals: per-entry segment bend, 0.5 = straight (default). Direction of bend
            for values != 0.5 was never pinned down, so prefer many straight segments.
    Keep len(points) <= 33: no factory curve uses more than 32, limit unknown.
    For a MIDI-note source, x = note / 127. For velocity, x = velocity / 127.
    """
    xs = [float(x) for x, _ in points]
    assert xs[0] == 0.0 and xs[-1] == 1.0 and xs == sorted(xs), "x must run 0 -> 1"
    lfo = {
        "curveVals": list(curve_vals) if curve_vals else [0.5] * len(xs),
        "numPoints": len(xs) - 1,
        "xVals": xs,
        "yVals": [1.0 - float(v) for _, v in points],
    }
    body = {"LFO": lfo, **CURVE_META}
    header = {
        "fileType": "XferShape",
        "hash": "",
        **{k: v for k, v in CURVE_META.items() if k != "fileType"},
    }
    return header, body


def curve_points(body_or_flex):
    """Return [(x, value)] from a curve body, or from a ModSlot 'flex' entry."""
    c = body_or_flex.get("LFO", body_or_flex)
    return [(x, 1.0 - y) for x, y in zip(c["xVals"], c["yVals"], strict=True)]


def sample(points, x):
    """Linear interpolation (valid for straight segments, curveVals == 0.5)."""
    for (x0, v0), (x1, v1) in zip(points, points[1:], strict=False):
        if x0 <= x <= x1:
            return v0 if x1 == x0 else v0 + (v1 - v0) * (x - x0) / (x1 - x0)
    return points[-1][1]


def curve_distance(a, b, n=400):
    """Largest difference between two point lists, sampled at n + 1 evenly spaced x."""
    return max(abs(sample(a, i / n) - sample(b, i / n)) for i in range(n + 1))


# ---------------------------------------------------------------- presets
# ModSlotN["source"] = [source_id, aux_id]; 0 = none.
# CONFIRMED from a saved preset's matrix: 1 Mod Wheel, 3 ENV 2, 6-9 LFO 1-4, 16 Velocity,
# 17 Note, 25-32 Macro 1-8. The rest are inferred from ordering; confirm before relying.
SOURCES = {
    0: "-",
    1: "ModWheel",
    2: "ENV1?",
    3: "ENV2",
    4: "ENV3?",
    5: "ENV4?",
    6: "LFO1",
    7: "LFO2",
    8: "LFO3",
    9: "LFO4",
    16: "Velo",
    17: "Note",
    **{24 + i: f"Macro{i}" for i in range(1, 9)},
}
OSC = {0: "A", 1: "B", 2: "C", 3: "Noise", 4: "Sub"}  # Oscillator/WTOsc module ids


def used_slots(body):
    """Yield (index, slot) for every mod slot that has a source."""
    for i in range(64):
        s = body.get(f"ModSlot{i}")
        if s and "source" in s:
            yield i, s


def dest_label(slot):
    """Destination in UI numbering: Macro2.Value, WTOsc[C].TablePos, FXReverb[7].Wet."""
    mod, mid = slot.get("destModuleTypeString"), slot.get("destModuleID")
    param = slot.get("destModuleParamName", "?").replace("kParam", "")
    if mod == "Macro":
        return f"Macro{mid + 1}.{param}"
    if mod in ("Oscillator", "WTOsc"):
        return f"{mod}[{OSC.get(mid, mid)}].{param}"
    if mod and mod.startswith("FX") and isinstance(mid, int):
        return f"{mod}[{mid + 1}].{param}"
    return f"{mod}[{mid}].{param}"


def slot_curve(slot):
    """The row's loaded main curve as a point list, or None if the row has none."""
    flex = slot.get("flex")
    if flex and flex[0].get("xVals"):
        return curve_points(flex[0])
    return None


def matrix(body):
    """Yield one readable line per used mod slot."""
    for i, s in used_slots(body):
        src, aux = (s["source"] + [0, 0])[:2]
        pp = s.get("plainParams", {})
        # Presets store only non-default values, so an absent amount is Serum's
        # default for a new row, which the file cannot tell us.
        amt = f"{pp['kParamAmount']:7.2f}" if "kParamAmount" in pp else "default"
        extra = {
            k.replace("kParam", ""): round(v, 3)
            for k, v in pp.items()
            if k not in ("kParamAmount", "kParamBipolar")
        }
        curve = ""
        if slot_curve(s):
            curve = f" curve[{s['flex'][0].get('numPoints')}pts]"
        yield (
            f"{i:2d}  {SOURCES.get(src, src):>8} -> {dest_label(s):<34} "
            f"amt {amt}  {'bi ' if pp.get('kParamBipolar') else 'uni'}"
            f"  aux {SOURCES.get(aux, aux):<7}{curve} {extra if extra else ''}"
        ).rstrip()


def load_curves(directory):
    """Return {name: points} for every .XferShape file in a directory."""
    curves = {}
    for path in sorted(glob.glob(os.path.join(directory, "*.XferShape"))):
        _, _, body = read(path)
        curves[os.path.basename(path)[: -len(".XferShape")]] = curve_points(body)
    return curves


def row_curves(body, curves, tolerance=1e-4):
    """
    Yield (index, slot, matches, nearest) for every row with a loaded curve.

    matches lists every curve file within `tolerance` of the row's stored curve
    (several files can be identical). When nothing matches, nearest is
    (distance, name) of the closest file.
    """
    for i, s in used_slots(body):
        pts = slot_curve(s)
        if pts is None:
            continue
        dists = sorted((curve_distance(pts, c), n) for n, c in curves.items())
        matches = [n for d, n in dists if d <= tolerance]
        yield i, s, matches, (None if matches or not dists else dists[0])


# ---------------------------------------------------------------- diff
def diff(a, b, path=""):
    """Yield (path, a_value, b_value) for every differing leaf."""
    if isinstance(a, dict) and isinstance(b, dict):
        for k in list(a) + [k for k in b if k not in a]:
            p = f"{path}/{k}"
            if k not in a:
                yield p, "<absent>", b[k]
            elif k not in b:
                yield p, a[k], "<absent>"
            else:
                yield from diff(a[k], b[k], p)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b, strict=True)):
            yield from diff(x, y, f"{path}[{i}]")
    elif a != b:
        yield path, a, b


# ---------------------------------------------------------------- CLI
def _short(v, n=120):
    s = json.dumps(v, default=str)
    return s if len(s) <= n else s[:n] + "…"


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    cmd, f = argv[1], argv[2]
    h, fmt, body = read(f)
    if cmd == "verify":
        with open(f, "rb") as fh:
            d = fh.read()
        n = struct.unpack("<Q", d[9:17])[0]
        raw = zstandard.ZstdDecompressor().decompress(d[25 + n :], max_output_size=64 * 2**20)
        rt = encode(body) == raw
        ok = hash_ok(f)
        print(f"hash ok: {ok}   cbor round-trip identical: {rt}   fmt {fmt}")
        if not (ok and rt):
            return 1
    elif cmd == "dump":
        out = json.dumps({"header": h, "body": body}, indent=1, default=str)
        if len(argv) > 3:
            with open(argv[3], "w") as fh:
                fh.write(out)
        else:
            print(out)
    elif cmd == "matrix":
        for line in matrix(body):
            print(line)
    elif cmd == "rowcurves":
        curves = load_curves(argv[3] if len(argv) > 3 else REPO_CURVES)
        for i, s, matches, nearest in row_curves(body, curves):
            src = SOURCES.get(s["source"][0], s["source"][0])
            if matches:
                found = " = ".join(matches)
            elif nearest:
                found = f"no file matches (nearest {nearest[1]}, max diff {nearest[0]:.3f})"
            else:
                found = "no curve files found"
            print(f"{i:2d}  {src:>8} -> {dest_label(s):<34} {found}")
    elif cmd == "diff":
        h2, _, body2 = read(argv[3])
        for p, x, y in diff(
            {"header": {k: v for k, v in h.items() if k != "hash"}, **body},
            {"header": {k: v for k, v in h2.items() if k != "hash"}, **body2},
        ):
            print(f"{p}\n    A: {_short(x)}\n    B: {_short(y)}")
    elif cmd == "curve":
        for x, v in curve_points(body):
            print(f"x {x:.4f} (MIDI {127 * x:6.1f})  value {v:.4f}  ({16 * v:5.2f} squares of 16)")
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

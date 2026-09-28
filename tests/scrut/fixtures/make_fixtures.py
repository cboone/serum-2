# /// script
# requires-python = ">=3.10"
# dependencies = ["cbor2==6.1.4", "zstandard==0.25.0"]
# ///
"""Write the synthetic example preset and curves the scrut tests read.

Usage: make_fixtures.py OUTDIR

Writes OUTDIR/Presets/Example.SerumPreset and three curves in OUTDIR/Curves/.
Run with `uv run --script` and `tools/` on PYTHONPATH, from the repository root:

    PYTHONPATH=tools uv run --script tests/scrut/fixtures/make_fixtures.py \
        tests/scrut/fixtures/serum

The preset is synthetic. It carries only the header and the keys the tools read
(macro names and matrix rows), in the layout Serum 2.1.5 writes, so it exercises
the container, the encoder and the matrix readers. It is not a complete patch and
is not expected to load in Serum as a playable sound.

The output is deterministic, so rerunning this script reproduces the committed
fixtures byte for byte. The fixtures are CC0 (see LICENSE-ASSETS).
"""

import math
import os
import sys

import serumfile as S


def s_rise(a, b):
    """Points for a cosine S-rise from 0 at x = a to 1 at x = b."""

    def f(x):
        if x <= a:
            return 0.0
        if x >= b:
            return 1.0
        return 0.5 - 0.5 * math.cos(math.pi * (x - a) / (b - a))

    xs = sorted({0.0, 1.0, *[round(a + (b - a) * i / 24, 6) for i in range(25)]})
    return [(x, f(x)) for x in xs]


CURVES = {
    "Linear Ramp": [(0.0, 0.0), (1.0, 1.0)],
    "S Rise": s_rise(0.2, 0.8),
    # Identical to S Rise, so `rowcurves` has two matching files to list.
    "S Rise (copy)": s_rise(0.2, 0.8),
}


def flex(points):
    """A matrix row's `flex` entry: the main curve, then an empty aux curve."""
    _, body = S.make_curve(points)
    return [body["LFO"], {}]


def slot(source, aux, module, module_id, param_id, param, plain=None, curve=None):
    s = {
        "destModuleID": module_id,
        "destModuleParamID": param_id,
        "destModuleParamName": param,
        "destModuleTypeString": module,
    }
    if curve is not None:
        s["flex"] = flex(curve)
    if plain:
        s["plainParams"] = plain
    s["source"] = [source, aux]
    return s


META = {
    "presetAuthor": "",
    "presetComment": "",
    "presetDescription": "",
    "presetName": "Example",
    "product": "Serum2",
    "productVersion": "2.1.5",
    "tags": [],
    "url": "https://xferrecords.com/",
    "vendor": "Xfer Records",
    "version": 11.0,
}


def preset():
    body = {
        "Macro0": {"name": "TONE", "plainParams": {"kParamValue": 50.0}},
        "Macro1": {"name": "MOTION"},
        # Mod Wheel -> Macro 2, gated by Macro 8 as aux.
        "ModSlot0": slot(1, 32, "Macro", 1, 0, "kParamValue", {"kParamAmount": 50.0}),
        # Velocity -> amp, through a curve.
        "ModSlot1": slot(
            16,
            0,
            "Global",
            0,
            2,
            "kParamVoiceAmp",
            {"kParamAmount": 100.0, "kParamMainCurveData": 1.0},
            CURVES["Linear Ramp"],
        ),
        # Note -> Osc A detune, bipolar, through a curve.
        "ModSlot2": slot(
            17,
            0,
            "Oscillator",
            0,
            3,
            "kParamDetune",
            {"kParamAmount": 20.0, "kParamBipolar": 1.0, "kParamMainCurveData": 1.0},
            CURVES["S Rise"],
        ),
        # Macro 1 -> reverb wet in FX slot 2.
        "ModSlot3": slot(25, 0, "FXReverb", 1, 1, "kParamWet", {"kParamAmount": 25.0}),
        # LFO 1 -> filter cutoff, with no stored amount.
        "ModSlot4": slot(6, 0, "VoiceFilter", 0, 0, "kParamFreq"),
        "fileType": "SerumPreset",
        **META,
    }
    header = {"fileType": "SerumPreset", "hash": "", **META}
    return header, body


def main(outdir):
    os.makedirs(os.path.join(outdir, "Curves"), exist_ok=True)
    os.makedirs(os.path.join(outdir, "Presets"), exist_ok=True)
    for name, points in CURVES.items():
        header, body = S.make_curve(points)
        S.write(os.path.join(outdir, "Curves", f"{name}.XferShape"), header, body)
    header, body = preset()
    S.write(os.path.join(outdir, "Presets", "Example.SerumPreset"), header, body)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1])

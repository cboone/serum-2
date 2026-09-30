# Serum 2 file formats and tooling

These structures were reverse-engineered from files saved by Serum 2.1.5. Nothing here comes from Xfer Records documentation. Curves, wavetables and a modified preset copy written by these tools all loaded in Serum 2.1.5, and other versions may differ. Structure described below without a qualifier was observed in files saved by Serum 2.1.5. Claims that go further say how they were established, and anything inferred or unconfirmed is marked as such. The implementation is in `tools/serumfile.py`.

This project is not affiliated with, endorsed by, or sponsored by Xfer Records. Serum is a trademark of Xfer Records, named here only to describe compatibility.

## The XferJson container (.SerumPreset and .XferShape)

Both file types use one container:

```text
"XferJson\0"                   9-byte magic
uint64 LE   header_len
header JSON                    compact, keys in Serum's order; "hash" = MD5 (hex) of the zstd block
uint32 LE   raw_len            length of the uncompressed CBOR body
uint32 LE   fmt                always 2 so far
zstd frame                     CBOR body; content size written, no checksum
```

The hash was confirmed against 18 factory curves, a user-drawn curve, and saved presets. Any edited file needs a fresh hash, which `serumfile.write()` computes. The header repeats the metadata (`fileType`, `product` "Serum2", `productVersion` "2.1.5", `url`, `vendor`, `version` 11.0, plus `presetName`, `presetAuthor`, `presetComment`, `presetDescription` and `tags` for presets).

The body is CBOR, and Serum's encoding is regular enough to reproduce byte for byte: definite-length maps and arrays in insertion order, text-string keys, and floats written as float32 whenever that is exact, otherwise float64. `serumfile.encode()` does this. `serumfile.py verify FILE` checks both the hash and that decoding and re-encoding reproduces the body exactly, and it passes on every file seen so far. Serum's zstd parameters for presets are not reproduced exactly (the compressed bytes differ from Serum's own), but Serum accepts level-3 frames, and for curve files level 3 happens to match Serum's output byte for byte.

## Curve files (.XferShape)

A curve body is the metadata fields plus one key, `LFO`:

```text
{"LFO": {"curveVals": [...], "numPoints": N, "xVals": [...], "yVals": [...]},
 "fileType": "XferShape", "product": "Serum2", "productVersion": "2.1.5",
 "url": "https://xferrecords.com/", "vendor": "Xfer Records", "version": 11.0}
```

Three facts matter. First, **y is stored from the top**: stored y = 1 − value, where value 1 is the top of the editor (confirmed by the factory remap "Mid at Hi16th", which stores y ≈ 0.062 at x = 0.5). Second, every file stores **one more entry than `numPoints`**, the fixed endpoint at x = 1. Third, `curveVals` holds one bend value per entry, with 0.5 meaning a straight segment. The bend direction away from 0.5 is unmeasured, so generated curves use many straight segments instead (24–33 entries; no examined factory curve uses more than 32 points, and the limit is unknown). With points every 2–4 semitones, straight segments stay within a few hundredths of a grid square of the ideal shape.

To generate a curve, compute the target value at each x, then call `make_curve` and `write`. Give a script like this the PEP 723 block from `tools/serumfile.py` (the same exact `cbor2` and `zstandard` pins), then run it from the repository root with `PYTHONPATH=tools uv run --script SCRIPT.py`:

```python
# /// script
# requires-python = ">=3.10"
# dependencies = ["cbor2==6.1.4", "zstandard==0.25.0"]
# ///
import math

import serumfile as S

# S-rise from 0 at x=a to 1 at x=b
a, b = 0.2, 0.8


def f(x):
    if x <= a:
        return 0.0
    if x >= b:
        return 1.0
    return 0.5 - 0.5 * math.cos(math.pi * (x - a) / (b - a))


xs = sorted({0.0, 1.0, *[round(a + (b - a) * i / 24, 6) for i in range(25)]})
header, body = S.make_curve([(x, f(x)) for x in xs])
S.write("S Rise.XferShape", header, body)
```

For a note source use x = MIDI note / 127, and for velocity x = velocity / 127. `tools/serumfile.py curve FILE` lists a curve's points with MIDI numbers and "squares of 16", a unit for comparison with Serum's editor. Rebuilding a curve file saved by Serum from its own points with `make_curve` reproduced it byte for byte, which confirms the builder matches Serum.

## Presets (.SerumPreset)

The decoded body has about 177 top-level keys. The ones that matter here:

| Key                                  | Contents                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `Oscillator0`–`Oscillator4`          | A, B, C, Noise, Sub. `plainParams` holds the shared oscillator settings (kParamVolume, kParamOctave, kParamDetune, kParamDetuneMode "kDetuneSuper"/"kDetuneExp", kParamUnison, kParamUnisonRange, kParamUnisonStereo = WIDTH, kParamEnable, …). A nested `WTOsc0` and so on holds the wavetable settings (`relativePathToWT` such as "User/Dirichlet Sweep (normalized).wav", kParamWarpMenu "kSync", kParamWarpMenu2 "kDistTapeSat", kParamWarpVar, …). The noise oscillator is `NoiseOsc3` with kParamNoiseType. |
| `VoiceFilter0`                       | Filter 1 (kParamFreq stored normalized 0–1, kParamReso, kParamDrive, …)                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `Env0`–`Env3`, `LFO0`–`LFO9`         | ENV 1–4 and LFO 1–10 (0-based). LFOs include `curveData` in the same point format as curves, plus kParamRate, kParamDelay, kParamRise, kParamMode "Free", kParamType "Lorenz"/"Rossler", kParamMono.                                                                                                                                                                                                                                                                                                               |
| `Macro0`–`Macro7`                    | `name` (the macro's label) and plainParams.kParamValue (0–100; absent = 0)                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `ModSlot0`–`ModSlot63`               | The matrix rows (below)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `FXRack0` (`FX` list, in rack order) | Each entry is `{"<FXType>": {"plainParams": …}, "type": n}`. Types seen: 0 Distortion, 2 Phaser, 3 Chorus, 4 Delay, 6 Reverb, 7 EQ, 9 HyperDimension. Phaser and chorus also store an `lfophasor` (LFO phase at save time), which changes on every save and can be ignored in diffs.                                                                                                                                                                                                                               |
| `Global0`                            | Mono, portamento, bend range, oversampling and so on                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `midiMap`                            | e.g. `{"ccNum": 21, "paramIDs": [7000000]}`; 7000000 + 1000·k is Macro k+1                                                                                                                                                                                                                                                                                                                                                                                                                                         |

Only non-default values are stored.

**Matrix rows.** A used `ModSlotN` contains `source: [source_id, aux_id]` (0 = none), `destModuleTypeString` (Oscillator, WTOsc, VoiceFilter, Macro, Global, FXDistortion, FXHyperD, …), `destModuleID` (the oscillator index, macro index, or position in the FX rack, all 0-based; `serumfile.py matrix` and `rowcurves` print them in the UI's numbering, such as Macro2 or FXReverb[7]), `destModuleParamName` (for example kParamFine, kParamDetune, kParamDetuneWid, kParamUnisonStereo, kParamTablePos, kParamWarpVar, kParamWet, kParamDimEWet, kParamLevelOut, kParamGain2, kParamVoiceAmp, kParamValue), and `plainParams` (kParamAmount in percent, stored with fractional precision such as 15.42 and absent when it is the default, kParamBipolar 1.0 when bipolar, kParamMainCurveData 1.0 when a custom curve is loaded, and kParamCurveIn, whose meaning is not established). A row with a custom curve also has `flex`, a list of two curve dicts in the `.XferShape` point format. `flex[0]` is the main source curve; its points matched the loaded `.XferShape` files exactly when compared (sampled at 400 points, maximum difference 0.000), so a row's curve can be checked by comparing `flex[0]` with a file, which is what `serumfile.py rowcurves` does. Replacing a curve by swapping `flex[0]` (with kParamMainCurveData set to 1.0) should work but has not been tried; verify the result in Serum before relying on it. `flex[1]` is probably the aux curve (inferred). In the presets examined it was empty on almost every curve row; one row held a two-point diagonal although it had no aux.

Source IDs confirmed from a saved preset: **1 Mod Wheel, 3 ENV 2, 6–9 LFO 1–4, 16 Velocity, 17 Note, 25–32 Macro 1–8**. By position, 2, 4 and 5 are probably ENV 1, 3 and 4, and 10–15 probably LFO 5–10, but those are not confirmed. kParamUnisonStereo is unison WIDTH. kParamDetuneWid is probably BLEND (inferred from the rows that target it).

Useful commands:

```bash
tools/serumfile.py verify    Lead.SerumPreset
tools/serumfile.py matrix    Lead.SerumPreset
tools/serumfile.py rowcurves Lead.SerumPreset CURVE_DIR
tools/serumfile.py diff      A.SerumPreset B.SerumPreset
tools/serumfile.py dump      Lead.SerumPreset lead.json
```

In `matrix` output an amount shows as `default` when the row doesn't store one, because the file cannot say what Serum's default is.

**Editing a preset.** Read it, change the body, set `header["presetName"]`, write it under a new file name, then diff against the original to prove that only the intended keys changed. Removing a key resets that parameter to its default. For example, to reset two matrix rows' amounts in a named copy:

```python
import serumfile as S

h, fmt, body = S.read("Lead.SerumPreset")
for n in (1, 2):
    body[f"ModSlot{n}"]["plainParams"].pop("kParamAmount", None)
h["presetName"] = "Lead (default amounts)"
S.write("Lead (default amounts).SerumPreset", h, body, fmt)
```

**Editing the header only.** `serumfile.py meta FILE FIELD=VALUE ...` sets `presetName`, `presetAuthor`, `presetComment`, `presetDescription` or `url` in place and leaves the body as it was. It refuses a file whose body does not re-encode byte for byte, since rewriting that file would change more than the header. The rewritten file carries a fresh hash and a level-3 zstd frame, which Serum loads. Which of these fields Serum's preset browser displays has not been confirmed.

**Patching a preset.** `serumfile.py patch FILE PATCH.json [OUT]` applies a JSON merge patch ([RFC 7396](https://www.rfc-editor.org/rfc/rfc7396)) of the form `{"header": {...}, "body": {...}}`. Objects merge key by key, `null` removes a key (which resets a parameter to its default), and any other value replaces the old one. Existing keys keep their place and new keys are appended. The header part may touch only the fields `meta` sets plus `tags`. Numbers keep their JSON form, so write `1.0` where Serum stores a float. The same round-trip check as `meta` applies.

**Matrix order.** A preset stores all 64 matrix slots as `ModSlot0` to `ModSlot63`, used rows first and empty slots as `{"plainParams": {}}` (confirmed on presets saved by Serum 2.1.5). Serum keeps rows in the order they were added or moved, so two presets with the same rows can store them differently. `serumfile.py sortmatrix FILE [OUT]` rewrites the rows in a canonical order, destination first: rows whose destination is a macro, then the oscillators (A, B, C, Noise, Sub, each with its wavetable parameters), filters, global voice parameters such as Amp, other modules, and effects in rack order. Within a destination module, rows sort by parameter ID, then source, then aux. Sorting is idempotent. It refuses a preset whose MIDI map targets anything other than macro values (parameter IDs 7000000 + 1000 × macro index, inferred from saved presets), because other targets may name rows by position. Two things are unconfirmed: whether row order ever affects the sound, for example when one row drives a macro that another row reads, and whether DAW automation of a row's parameters follows the row's position. Check both before relying on a sorted preset.

## Wavetables (.wav)

Serum recognizes a WAV as a wavetable without the import dialog when it carries a `clm` chunk (the four-byte chunk ID is "clm" plus a space) containing `<!>2048 00000000 wavetable (www.xferrecords.com)`, which gives the frame size. The Dirichlet Sweep tables are 256 frames × 2048 samples, 32-bit float, mono, 44.1 kHz. `tools/make_sweep.py [outdir]` rebuilds both versions. Each frame is built additively (harmonics 1–1023, so nothing aliases inside the table) as three saws at phases 0, δ and 2δ. The first notch moves geometrically from harmonic 128 at frame 0 (effectively a plain saw) to harmonic 1 at frame 255, where only multiples of 3 survive and the pitch jumps an octave and a fifth. The script's self-check compares a frame against a direct sum of three ramps, and the scrut tests check that a rebuild matches the committed tables to within 1e-6 per sample (FFT output can differ in the last bits across platforms). The tables are committed in `serum/Tables/` as generated artifacts: regenerate them with `tools/make_sweep.py serum/Tables` rather than editing them, and commit the result.

The committed tables were built with `make_sweep.py` and have no C2PA provenance chunk.

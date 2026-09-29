# serumfile.py

Tests for `tools/serumfile.py`. They read the synthetic example preset and curves in `tests/scrut/fixtures/serum/`, which `tests/scrut/fixtures/make_fixtures.py` writes. `REPO_ROOT` is the repository root; `make test-scrut` sets it.

## make_fixtures reproduces the committed fixtures

The fixtures are generated, so rebuilding them must reproduce the committed files byte for byte.

```scrut
$ PYTHONPATH="${REPO_ROOT}/tools" uv run -q --script "${REPO_ROOT}/tests/scrut/fixtures/make_fixtures.py" rebuilt && diff -r rebuilt "${REPO_ROOT}/tests/scrut/fixtures/serum" && echo identical
identical
```

## verify passes on the preset and a curve

```scrut
$ "${REPO_ROOT}/tools/serumfile.py" verify "${REPO_ROOT}/tests/scrut/fixtures/serum/Presets/Example.SerumPreset"
hash ok: True   cbor round-trip identical: True   fmt 2
```

```scrut
$ "${REPO_ROOT}/tools/serumfile.py" verify "${REPO_ROOT}/tests/scrut/fixtures/serum/Curves/S Rise.XferShape"
hash ok: True   cbor round-trip identical: True   fmt 2
```

## verify fails on a corrupted file

A byte appended to the compressed block breaks the hash, and `verify` must exit 1, not just print `False`.

```scrut
$ cp "${REPO_ROOT}/tests/scrut/fixtures/serum/Curves/S Rise.XferShape" corrupt.XferShape && printf x >> corrupt.XferShape && "${REPO_ROOT}/tools/serumfile.py" verify corrupt.XferShape
hash ok: False   cbor round-trip identical: True   fmt 2
[1]
```

## matrix lists every row with UI numbering

Destination macros print 1-based, so the Mod Wheel row reads `Macro2`, and FX slots count from 1 in rack order. A row with no stored amount shows `default`. Lines carry no trailing spaces.

```scrut
$ "${REPO_ROOT}/tools/serumfile.py" matrix "${REPO_ROOT}/tests/scrut/fixtures/serum/Presets/Example.SerumPreset"
 0  ModWheel -> Macro2.Value                       amt   50.00  uni  aux Macro8
 1      Velo -> Global[0].VoiceAmp                 amt  100.00  uni  aux -       curve[1pts] {'MainCurveData': 1.0}
 2      Note -> Oscillator[A].Detune               amt   20.00  bi   aux -       curve[26pts] {'MainCurveData': 1.0}
 3    Macro1 -> FXReverb[2].Wet                    amt   25.00  uni  aux -
 4      LFO1 -> VoiceFilter[0].Freq                amt default  uni  aux -
```

## rowcurves names the curve file in every curve row

Identical curve files are all listed.

```scrut
$ "${REPO_ROOT}/tools/serumfile.py" rowcurves "${REPO_ROOT}/tests/scrut/fixtures/serum/Presets/Example.SerumPreset" "${REPO_ROOT}/tests/scrut/fixtures/serum/Curves"
 1      Velo -> Global[0].VoiceAmp                 Linear Ramp
 2      Note -> Oscillator[A].Detune               S Rise = S Rise (copy)
```

## rowcurves reports rows with no matching file

With an empty curve folder, every curve row says so instead of guessing.

```scrut
$ mkdir -p empty-curves && "${REPO_ROOT}/tools/serumfile.py" rowcurves "${REPO_ROOT}/tests/scrut/fixtures/serum/Presets/Example.SerumPreset" empty-curves
 1      Velo -> Global[0].VoiceAmp                 no curve files found
 2      Note -> Oscillator[A].Detune               no curve files found
```

## rowcurves requires a curve folder

There is no default folder, so a missing argument prints usage and exits 1. Arguments are checked before any file is read, so the preset need not exist.

```scrut
$ "${REPO_ROOT}/tools/serumfile.py" rowcurves missing.SerumPreset > usage.txt; echo "exit $?"; grep 'rowcurves  FILE' usage.txt
exit 1
    serumfile.py rowcurves  FILE CURVE_DIR    name the curve file in CURVE_DIR matching each row
```

## curve lists points with MIDI numbers and grid squares

```scrut
$ "${REPO_ROOT}/tools/serumfile.py" curve "${REPO_ROOT}/tests/scrut/fixtures/serum/Curves/S Rise.XferShape" | head -3
x 0.0000 (MIDI    0.0)  value 0.0000  ( 0.00 squares of 16)
x 0.2000 (MIDI   25.4)  value 0.0000  ( 0.00 squares of 16)
x 0.2250 (MIDI   28.6)  value 0.0043  ( 0.07 squares of 16)
```

## diff of a file against itself is empty

```scrut
$ "${REPO_ROOT}/tools/serumfile.py" diff "${REPO_ROOT}/tests/scrut/fixtures/serum/Presets/Example.SerumPreset" "${REPO_ROOT}/tests/scrut/fixtures/serum/Presets/Example.SerumPreset"
```

## write rebuilds a curve byte for byte

Rebuilding S Rise from its own points with `make_curve` and `write` must reproduce the file exactly, which confirms the encoder and hash are stable. Byte-for-byte agreement with curves saved by Serum itself was established against Serum 2.1.5 files (see `docs/SERUM-FILE-FORMAT.md`); these fixtures are generated, so this test guards against regressions rather than re-establishing that agreement.

```scrut
$ PYTHONPATH="${REPO_ROOT}/tools" uv run -q --script "${REPO_ROOT}/tests/scrut/fixtures/rebuild_curve.py" "${REPO_ROOT}/tests/scrut/fixtures/serum/Curves/S Rise.XferShape" rebuilt.XferShape && cmp rebuilt.XferShape "${REPO_ROOT}/tests/scrut/fixtures/serum/Curves/S Rise.XferShape" && echo identical
identical
```

## an unknown command prints usage and exits 1

```scrut
$ "${REPO_ROOT}/tools/serumfile.py" bogus "${REPO_ROOT}/tests/scrut/fixtures/serum/Presets/Example.SerumPreset" > /dev/null
[1]
```

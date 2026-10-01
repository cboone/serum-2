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

## meta prints a preset's header without its hash

```scrut
$ "${REPO_ROOT}/tools/serumfile.py" meta "${REPO_ROOT}/tests/scrut/fixtures/serum/Presets/Example.SerumPreset" | grep -c -e presetName -e hash
1
```

## meta sets header fields and leaves the body unchanged

The rewritten preset still verifies, and a diff against the original shows only the fields that were set, in the header and in the body's copy.

```scrut
$ cp "${REPO_ROOT}/tests/scrut/fixtures/serum/Presets/Example.SerumPreset" stamped.SerumPreset && "${REPO_ROOT}/tools/serumfile.py" meta stamped.SerumPreset presetComment="Version 1.2.0" presetAuthor="Example Author" && "${REPO_ROOT}/tools/serumfile.py" verify stamped.SerumPreset
hash ok: True   cbor round-trip identical: True   fmt 2
```

```scrut
$ "${REPO_ROOT}/tools/serumfile.py" diff "${REPO_ROOT}/tests/scrut/fixtures/serum/Presets/Example.SerumPreset" stamped.SerumPreset
/header/presetAuthor
    A: ""
    B: "Example Author"
/header/presetComment
    A: ""
    B: "Version 1.2.0"
/presetAuthor
    A: ""
    B: "Example Author"
/presetComment
    A: ""
    B: "Version 1.2.0"
```

## meta keeps the body's copy of a header field in step

Presets saved by Serum repeat the name and other header fields at the top level of the body. Given a preset whose body has a `presetName`, `meta` changes both copies.

```scrut
$ printf '{"body": {"presetName": "Example"}}' > body-name.json && "${REPO_ROOT}/tools/serumfile.py" patch "${REPO_ROOT}/tests/scrut/fixtures/serum/Presets/Example.SerumPreset" body-name.json named.SerumPreset && cp named.SerumPreset renamed.SerumPreset && "${REPO_ROOT}/tools/serumfile.py" meta renamed.SerumPreset presetName=Renamed && "${REPO_ROOT}/tools/serumfile.py" diff named.SerumPreset renamed.SerumPreset | grep '^/'
/header/presetName
/presetName
```

## meta refuses fields outside the allowlist

Container fields such as `fileType` are not settable, and the file is left as it was.

```scrut
$ cp "${REPO_ROOT}/tests/scrut/fixtures/serum/Presets/Example.SerumPreset" guarded.SerumPreset && "${REPO_ROOT}/tools/serumfile.py" meta guarded.SerumPreset fileType=Other 2>&1
error: cannot set fileType; settable: presetName, presetAuthor, presetComment, presetDescription, url
[1]
```

```scrut
$ cmp guarded.SerumPreset "${REPO_ROOT}/tests/scrut/fixtures/serum/Presets/Example.SerumPreset" && echo unchanged
unchanged
```

## meta refuses to print a curve's header

`meta` is for presets in both forms, reading as well as writing.

```scrut
$ "${REPO_ROOT}/tools/serumfile.py" meta "${REPO_ROOT}/tests/scrut/fixtures/serum/Curves/S Rise.XferShape" 2>&1 | sed "s|${REPO_ROOT}/||"
error: tests/scrut/fixtures/serum/Curves/S Rise.XferShape: not a preset
```

## meta refuses a curve and an argument without a value

```scrut
$ cp "${REPO_ROOT}/tests/scrut/fixtures/serum/Curves/S Rise.XferShape" curve.XferShape && "${REPO_ROOT}/tools/serumfile.py" meta curve.XferShape presetName=Other 2>&1
error: curve.XferShape: not a preset
[1]
```

```scrut
$ "${REPO_ROOT}/tools/serumfile.py" meta guarded.SerumPreset presetName 2>&1
error: expected FIELD=VALUE, got 'presetName'
[1]
```

## patch merges changes into the body and header

`null` removes a key, objects merge key by key, and other values replace the old ones. The result still verifies, and a diff shows only the patched keys.

```scrut
$ printf '{"header": {"tags": ["Poly"]}, "body": {"ModSlot1": {"plainParams": {"kParamAmount": 50.0}}, "ModSlot0": {"plainParams": {"kParamAmount": null}}}}' > poly.json && "${REPO_ROOT}/tools/serumfile.py" patch "${REPO_ROOT}/tests/scrut/fixtures/serum/Presets/Example.SerumPreset" poly.json patched.SerumPreset && "${REPO_ROOT}/tools/serumfile.py" verify patched.SerumPreset
hash ok: True   cbor round-trip identical: True   fmt 2
```

```scrut
$ "${REPO_ROOT}/tools/serumfile.py" diff "${REPO_ROOT}/tests/scrut/fixtures/serum/Presets/Example.SerumPreset" patched.SerumPreset | grep '^/'
/header/tags
/ModSlot0/plainParams/kParamAmount
/ModSlot1/plainParams/kParamAmount
/tags
```

## patch refuses container header fields and unknown top-level keys

```scrut
$ printf '{"header": {"fileType": "Other"}}' > bad-header.json && "${REPO_ROOT}/tools/serumfile.py" patch "${REPO_ROOT}/tests/scrut/fixtures/serum/Presets/Example.SerumPreset" bad-header.json refused.SerumPreset 2>&1
error: cannot patch header fileType; patchable: presetName, presetAuthor, presetComment, presetDescription, url, tags
[1]
```

```scrut
$ printf '{"Global0": {}}' > bad-top.json && "${REPO_ROOT}/tools/serumfile.py" patch "${REPO_ROOT}/tests/scrut/fixtures/serum/Presets/Example.SerumPreset" bad-top.json refused.SerumPreset 2>&1; test ! -e refused.SerumPreset && echo "nothing written"
error: a patch has only header and body keys, not Global0
nothing written
```

## patch refuses anything but objects

A patch that is not a JSON object, or whose `header` or `body` is not one, would otherwise replace the whole preset body. Malformed JSON is refused the same way, with no traceback.

```scrut
$ printf '[]' > list.json && "${REPO_ROOT}/tools/serumfile.py" patch "${REPO_ROOT}/tests/scrut/fixtures/serum/Presets/Example.SerumPreset" list.json refused.SerumPreset 2>&1
error: a patch is a JSON object: {"header": {...}, "body": {...}}
[1]
```

```scrut
$ printf '{"body": null}' > null-body.json && "${REPO_ROOT}/tools/serumfile.py" patch "${REPO_ROOT}/tests/scrut/fixtures/serum/Presets/Example.SerumPreset" null-body.json refused.SerumPreset 2>&1
error: a patch's body must be a JSON object
[1]
```

```scrut
$ printf '{"header": "Other"}' > scalar-header.json && "${REPO_ROOT}/tools/serumfile.py" patch "${REPO_ROOT}/tests/scrut/fixtures/serum/Presets/Example.SerumPreset" scalar-header.json refused.SerumPreset 2>&1
error: a patch's header must be a JSON object
[1]
```

```scrut
$ printf '{"body": ' > broken.json && "${REPO_ROOT}/tools/serumfile.py" patch "${REPO_ROOT}/tests/scrut/fixtures/serum/Presets/Example.SerumPreset" broken.json refused.SerumPreset 2>&1 | sed 's/: line .*//'; test ! -e refused.SerumPreset && echo "nothing written"
error: Expecting value
nothing written
```

## editing commands refuse a preset whose body does not round-trip

This copy of the example stores its floats as float64, so it decodes to the same body but re-encoding gives different bytes. Rewriting it would change more than the edit, so `meta`, `patch` and `sortmatrix` all refuse it and leave it as it was.

```scrut
$ PYTHONPATH="${REPO_ROOT}/tools" uv run -q --script "${REPO_ROOT}/tests/scrut/fixtures/widen_floats.py" "${REPO_ROOT}/tests/scrut/fixtures/serum/Presets/Example.SerumPreset" wide.SerumPreset && cp wide.SerumPreset wide-before.SerumPreset && "${REPO_ROOT}/tools/serumfile.py" meta wide.SerumPreset presetName=Other 2>&1
error: wide.SerumPreset: body does not round-trip; not rewriting it
[1]
```

```scrut
$ printf '{}' > empty.json && "${REPO_ROOT}/tools/serumfile.py" patch wide.SerumPreset empty.json 2>&1; "${REPO_ROOT}/tools/serumfile.py" sortmatrix wide.SerumPreset 2>&1; cmp wide.SerumPreset wide-before.SerumPreset && echo unchanged
error: wide.SerumPreset: body does not round-trip; not rewriting it
error: wide.SerumPreset: body does not round-trip; not rewriting it
unchanged
```

## editing leaves no temporary files behind

Each rewrite goes through a uniquely named file beside the target, moved over it at the end.

```scrut
$ mkdir -p edits && cp "${REPO_ROOT}/tests/scrut/fixtures/serum/Presets/Example.SerumPreset" edits/ && "${REPO_ROOT}/tools/serumfile.py" meta edits/Example.SerumPreset presetName=Edited && "${REPO_ROOT}/tools/serumfile.py" sortmatrix edits/Example.SerumPreset && ls -A edits
Example.SerumPreset
```

## sortmatrix puts rows in canonical order

Macro destinations come first, then oscillators, filters, global voice parameters and effects in rack order.

```scrut
$ "${REPO_ROOT}/tools/serumfile.py" sortmatrix "${REPO_ROOT}/tests/scrut/fixtures/serum/Presets/Example.SerumPreset" sorted.SerumPreset && "${REPO_ROOT}/tools/serumfile.py" matrix sorted.SerumPreset
 0  ModWheel -> Macro2.Value                       amt   50.00  uni  aux Macro8
 1      Note -> Oscillator[A].Detune               amt   20.00  bi   aux -       curve[26pts] {'MainCurveData': 1.0}
 2      LFO1 -> VoiceFilter[0].Freq                amt default  uni  aux -
 3      Velo -> Global[0].VoiceAmp                 amt  100.00  uni  aux -       curve[1pts] {'MainCurveData': 1.0}
 4    Macro1 -> FXReverb[2].Wet                    amt   25.00  uni  aux -
```

Sorting a sorted preset reproduces it byte for byte, and nothing outside the matrix changes.

```scrut
$ "${REPO_ROOT}/tools/serumfile.py" sortmatrix sorted.SerumPreset resorted.SerumPreset && cmp sorted.SerumPreset resorted.SerumPreset && "${REPO_ROOT}/tools/serumfile.py" diff "${REPO_ROOT}/tests/scrut/fixtures/serum/Presets/Example.SerumPreset" sorted.SerumPreset | grep '^/' | grep -c -v '^/ModSlot'
0
[1]
```

## sortmatrix refuses a MIDI map that targets other parameters

Such targets may name matrix rows by position, so reordering could break them.

```scrut
$ printf '{"body": {"midiMap": [{"ccNum": 21, "paramIDs": [123]}]}}' > map.json && "${REPO_ROOT}/tools/serumfile.py" patch "${REPO_ROOT}/tests/scrut/fixtures/serum/Presets/Example.SerumPreset" map.json mapped.SerumPreset && "${REPO_ROOT}/tools/serumfile.py" sortmatrix mapped.SerumPreset 2>&1
error: MIDI map targets non-macro parameters [123]; not reordering rows
[1]
```

## an unknown command prints usage and exits 1

```scrut
$ "${REPO_ROOT}/tools/serumfile.py" bogus "${REPO_ROOT}/tests/scrut/fixtures/serum/Presets/Example.SerumPreset" > /dev/null
[1]
```

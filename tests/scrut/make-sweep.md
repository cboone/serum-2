# make_sweep.py

`tools/make_sweep.py` must rebuild the committed Dirichlet Sweep wavetables, since `serum/Tables/` holds its output rather than a pulled copy. The comparison allows a tolerance of 1e-6 per sample, because FFT output can differ in the last bits across platforms and numpy builds. `REPO_ROOT` is the repository root; `make test-scrut` sets it.

## the rebuilt tables match the committed ones

The script also prints its own self-check; only the comparison matters here.

```scrut
$ "${REPO_ROOT}/tools/make_sweep.py" tables > /dev/null && echo built
built
```

```scrut
$ uv run -q --script "${REPO_ROOT}/tests/scrut/fixtures/compare_tables.py" "tables/Dirichlet Sweep (normalized).wav" "${REPO_ROOT}/serum/Tables/Dirichlet Sweep (normalized).wav"
match
```

```scrut
$ uv run -q --script "${REPO_ROOT}/tests/scrut/fixtures/compare_tables.py" "tables/Dirichlet Sweep (raw levels).wav" "${REPO_ROOT}/serum/Tables/Dirichlet Sweep (raw levels).wav"
match
```

## the rebuilt files keep the wavetable marker

Serum recognizes a WAV as a 2048-sample wavetable from its `clm` chunk.

```scrut
$ grep -c 'wavetable (www.xferrecords.com)' "tables/Dirichlet Sweep (normalized).wav"
1
```

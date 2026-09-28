# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy==2.5.3"]
# ///
"""Compare the sample data of two float32 wavetable WAVs within a tolerance.

Usage: compare_tables.py A.wav B.wav

Prints "match" when both files hold the same number of samples and every sample
agrees to within 1e-6, and exits 1 otherwise. A byte comparison would be too
strict: the FFT behind make_sweep.py can differ in the last bits across platforms
and numpy builds (a rebuild on macOS already differed from the installed tables
by about 1e-18 in two samples).
"""

import sys

import numpy as np

TOLERANCE = 1e-6


def samples(path):
    with open(path, "rb") as f:
        data = f.read()
    i = data.index(b"data")
    n = int.from_bytes(data[i + 4 : i + 8], "little")
    return np.frombuffer(data[i + 8 : i + 8 + n], np.float32)


a, b = samples(sys.argv[1]), samples(sys.argv[2])
if len(a) != len(b):
    sys.exit(f"length differs: {len(a)} vs {len(b)}")
worst = float(np.max(np.abs(a - b)))
if worst > TOLERANCE:
    sys.exit(f"max sample difference {worst} exceeds {TOLERANCE}")
print("match")

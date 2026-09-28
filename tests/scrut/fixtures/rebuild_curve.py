# /// script
# requires-python = ">=3.10"
# dependencies = ["cbor2==6.1.4", "zstandard==0.25.0"]
# ///
"""Rebuild a .XferShape curve from its own points and write it to a new path.

Usage: rebuild_curve.py SOURCE.XferShape OUT.XferShape

Run with `uv run --script` and `tools/` on PYTHONPATH, as the scrut tests do. The
pins above match tools/serumfile.py's. A byte-for-byte match with SOURCE confirms
that `make_curve` and `write` still reproduce Serum's own encoding and hash.
"""

import sys

import serumfile as S

_, _, body = S.read(sys.argv[1])
header, rebuilt = S.make_curve(S.curve_points(body))
S.write(sys.argv[2], header, rebuilt)

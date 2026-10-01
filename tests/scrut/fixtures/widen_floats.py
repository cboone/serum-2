# /// script
# requires-python = ">=3.10"
# dependencies = ["cbor2==6.1.4", "zstandard==0.25.0"]
# ///
"""Write a copy of a preset whose CBOR body stores every float as float64.

Usage: widen_floats.py SOURCE.SerumPreset OUT.SerumPreset

Run with `uv run --script` and `tools/` on PYTHONPATH, as the scrut tests do. The
pins above match tools/serumfile.py's. The copy decodes to the same body and
carries a valid hash, but Serum's encoding stores float32-exact values as float32,
so re-encoding the body does not reproduce these bytes. That is the case the
editing commands must refuse.
"""

import hashlib
import json
import struct
import sys

import cbor2
import serumfile as S
import zstandard

header, fmt, body = S.read(sys.argv[1])
raw = cbor2.dumps(body)
if S.encode(body) == raw:
    sys.exit("the widened body still round-trips; pick a source with floats")
comp = zstandard.ZstdCompressor(level=3, write_content_size=True).compress(raw)
header["hash"] = hashlib.md5(comp).hexdigest()
hj = json.dumps(header, separators=(",", ":")).encode()
with open(sys.argv[2], "wb") as f:
    f.write(S.MAGIC + struct.pack("<Q", len(hj)) + hj + struct.pack("<II", len(raw), fmt) + comp)

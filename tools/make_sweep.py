#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy==2.5.3"]
# ///
"""
Dirichlet sweep wavetable (regenerated): three same-frequency saws at phases
(0, d, 2d), with d swept across 256 frames of 2048 samples.

For an evenly stepped phase triple the harmonic gain is
    H(m) = |sin(3*m*d/2) / sin(m*d/2)|   (3-tap comb / Dirichlet kernel)
Exact nulls at harmonics N/3 and 2N/3 (N = 360/d), +9.5 dB at multiples of N.
The lowest notch sits at harmonic 120/d.

Mapping: the FIRST-NOTCH HARMONIC moves geometrically from 128 (frame 0,
effectively a plain saw) down to 1 (frame 255, only multiples of 3 survive:
a saw an octave and a fifth up).  ~37 frames per octave of notch movement.

Frames are built additively (spectrum -> irfft), so each frame holds exactly
harmonics 1..1023 and no baked-in aliasing.
"""

import os
import struct
import sys

import numpy as np

N_SAMPLES, N_FRAMES = 2048, 256
N_HARM = N_SAMPLES // 2 - 1
SR = 44100
FIRST_NOTCH_TOP, FIRST_NOTCH_BOT = 128.0, 1.0


def frame_from_phases(phases_deg):
    n = np.arange(1, N_HARM + 1)
    phi = np.deg2rad(np.asarray(phases_deg, float))[:, None]
    C = np.exp(1j * n[None, :] * phi).sum(axis=0)  # phasor sum per harmonic
    X = np.zeros(N_SAMPLES // 2 + 1, complex)
    X[1 : N_HARM + 1] = 1j * N_SAMPLES * C / (np.pi * n)  # saw: 1/n envelope, true scale
    return np.fft.irfft(X, N_SAMPLES)


def delta_for_frame(i):
    u = i / (N_FRAMES - 1)
    m1 = FIRST_NOTCH_TOP * (FIRST_NOTCH_BOT / FIRST_NOTCH_TOP) ** u
    return 120.0 / m1


def build(normalize_per_frame):
    frames = []
    for i in range(N_FRAMES):
        d = delta_for_frame(i)
        w = frame_from_phases([0.0, d, 2 * d])
        if normalize_per_frame:
            w = w / np.max(np.abs(w))  # constant peak: purely timbral morph
        frames.append(w)
    t = np.concatenate(frames)
    if not normalize_per_frame:
        t = t / np.max(np.abs(t))  # one global scale: keeps real level changes
    return (t * 0.999).astype(np.float32)


def write_wav(path, data):
    audio = data.tobytes()
    clm = b"<!>2048 00000000 wavetable (www.xferrecords.com)\x00"  # Serum frame-size marker
    if len(clm) % 2:
        clm += b"\x00"
    fmt = struct.pack("<HHIIHH", 3, 1, SR, SR * 4, 4, 32)  # 32-bit float mono
    chunks = (
        b"fmt "
        + struct.pack("<I", len(fmt))
        + fmt
        + b"clm "
        + struct.pack("<I", len(clm))
        + clm
        + b"data"
        + struct.pack("<I", len(audio))
        + audio
    )
    with open(path, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", 4 + len(chunks)) + b"WAVE" + chunks)


if __name__ == "__main__":
    # Usage: tools/make_sweep.py [output_dir]   (defaults to the current directory)
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(out, exist_ok=True)
    write_wav(f"{out}/Dirichlet Sweep (normalized).wav", build(True))
    write_wav(f"{out}/Dirichlet Sweep (raw levels).wav", build(False))
    # verification: additive frame vs naive sum of three ramps, away from resets
    d = delta_for_frame(200)
    ph = [0, d, 2 * d]
    t = np.arange(N_SAMPLES) / N_SAMPLES
    naive = sum(2 * ((t + p / 360) % 1) - 1 for p in ph)
    # The additive frame and the naive ramps may differ in sign convention, so align
    # them before comparing.
    s = np.sign(np.dot(frame_from_phases(ph), naive))
    add = s * frame_from_phases(ph)
    mask = np.ones(N_SAMPLES, bool)
    for p in ph:
        c = int(round((-p / 360) % 1 * N_SAMPLES))
        for k in range(-24, 25):
            mask[(c + k) % N_SAMPLES] = False
    print(
        "rel err away from resets:", np.max(np.abs(add[mask] - naive[mask])) / np.max(np.abs(naive))
    )
    print(" frame   delta   1st notch  H1    H2    H3    H4")
    for i in [0, 64, 128, 160, 192, 224, 255]:
        d = delta_for_frame(i)
        n = np.array([1, 2, 3, 4])
        H = np.abs(np.exp(1j * n[None, :] * np.deg2rad([0, d, 2 * d])[:, None]).sum(0))
        print(
            f"  {i:3d} {d:7.2f}   h{120 / d:6.2f}  "
            + " ".join(f"{20 * np.log10(max(v, 1e-3)):+5.1f}" for v in H)
        )

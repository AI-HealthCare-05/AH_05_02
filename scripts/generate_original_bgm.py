"""Generate the original looping BGM used by Carrot Forest.

The score and synthesis are intentionally self-contained so the two release
tracks can be reproduced without carrying third-party music into the build.
"""

from __future__ import annotations

import math
import random
import wave
from array import array
from pathlib import Path

SAMPLE_RATE = 32_000
ASSET_DIR = Path(__file__).resolve().parents[1] / "src" / "frontend" / "assets"


def midi_hz(note: int) -> float:
    return 440.0 * 2 ** ((note - 69) / 12)


def oscillator(kind: str, phase: float) -> float:
    sine = math.sin(phase)
    if kind == "triangle":
        return 2.0 / math.pi * math.asin(sine)
    if kind == "wood":
        return 0.72 * sine + 0.20 * math.sin(2 * phase) + 0.08 * math.sin(3 * phase)
    if kind == "bell":
        return 0.68 * sine + 0.22 * math.sin(2.01 * phase) + 0.10 * math.sin(3.97 * phase)
    return sine


def add_note(
    track: list[float],
    start: float,
    duration: float,
    note: int,
    volume: float,
    *,
    kind: str = "sine",
    attack: float = 0.015,
    release: float = 0.12,
    decay: float = 0.0,
) -> None:
    first = max(0, int(start * SAMPLE_RATE))
    last = min(len(track), int((start + duration) * SAMPLE_RATE))
    frequency = midi_hz(note)
    for index in range(first, last):
        elapsed = index / SAMPLE_RATE - start
        remaining = start + duration - index / SAMPLE_RATE
        envelope = min(1.0, elapsed / max(attack, 1e-4), remaining / max(release, 1e-4))
        if decay:
            envelope *= math.exp(-decay * elapsed)
        track[index] += volume * envelope * oscillator(kind, 2 * math.pi * frequency * elapsed)


def add_shaker(track: list[float], start: float, volume: float, rng: random.Random) -> None:
    first = int(start * SAMPLE_RATE)
    length = int(0.055 * SAMPLE_RATE)
    previous = 0.0
    for offset in range(length):
        index = first + offset
        if index >= len(track):
            break
        noise = rng.uniform(-1.0, 1.0)
        bright = noise - 0.72 * previous
        previous = noise
        envelope = math.exp(-42 * offset / SAMPLE_RATE)
        track[index] += bright * envelope * volume


def add_chord(track: list[float], start: float, duration: float, notes: tuple[int, ...], volume: float) -> None:
    for note in notes:
        add_note(track, start, duration, note, volume / len(notes), kind="wood", attack=0.18, release=0.3)


def normalize_and_write(track: list[float], path: Path) -> None:
    edge = int(0.06 * SAMPLE_RATE)
    for index in range(edge):
        fade = index / edge
        track[index] *= fade
        track[-index - 1] *= fade
    peak = max(max(abs(value) for value in track), 1e-8)
    scale = 0.86 / peak
    pcm = array("h", (round(max(-1.0, min(1.0, value * scale)) * 32767) for value in track))
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        output.writeframes(pcm.tobytes())


def build_forest() -> list[float]:
    bpm = 96
    beat = 60 / bpm
    bars = 16
    track = [0.0] * int(bars * 4 * beat * SAMPLE_RATE)
    rng = random.Random(20260901)
    chords = (
        (60, 64, 67, 71),
        (57, 60, 64, 67),
        (53, 57, 60, 64),
        (55, 60, 62, 67),
        (52, 55, 59, 64),
        (57, 60, 64, 69),
        (50, 53, 57, 62),
        (55, 59, 62, 67),
    )
    bass = (36, 33, 29, 31, 28, 33, 26, 31)
    motif = (
        (0.0, 67, 0.5),
        (0.75, 69, 0.25),
        (1.0, 71, 0.5),
        (1.75, 72, 0.25),
        (2.0, 76, 0.5),
        (2.75, 72, 0.25),
        (3.0, 71, 0.5),
        (3.5, 69, 0.5),
    )
    answer = (
        (0.0, 64, 0.5),
        (0.5, 67, 0.5),
        (1.25, 69, 0.5),
        (2.0, 72, 0.5),
        (2.75, 71, 0.25),
        (3.0, 69, 0.5),
        (3.5, 67, 0.5),
    )
    for bar in range(bars):
        start = bar * 4 * beat
        add_chord(track, start, 4 * beat, chords[bar % len(chords)], 0.30)
        for pulse in range(4):
            add_note(track, start + pulse * beat, 0.72 * beat, bass[bar % len(bass)], 0.13, kind="triangle")
        phrase = motif if bar % 4 in (0, 1) else answer
        transpose = 0 if bar < 8 else 12
        for offset, note, length in phrase:
            add_note(
                track,
                start + offset * beat,
                length * beat,
                note + transpose,
                0.18,
                kind="bell",
                release=0.16,
                decay=1.8,
            )
        for eighth in range(8):
            add_shaker(track, start + eighth * beat / 2, 0.018 if eighth % 2 == 0 else 0.012, rng)
    return track


def build_avatar() -> list[float]:
    bpm = 120
    beat = 60 / bpm
    bars = 16
    track = [0.0] * int(bars * 4 * beat * SAMPLE_RATE)
    rng = random.Random(20260902)
    chords = (
        (53, 57, 60, 64),
        (55, 59, 62, 67),
        (52, 55, 59, 64),
        (57, 60, 64, 69),
    )
    bass = (41, 43, 40, 45)
    melody = (
        (0.0, 72, 0.25),
        (0.5, 76, 0.25),
        (1.0, 79, 0.5),
        (1.75, 76, 0.25),
        (2.0, 74, 0.25),
        (2.5, 77, 0.25),
        (3.0, 81, 0.5),
        (3.75, 79, 0.25),
    )
    for bar in range(bars):
        start = bar * 4 * beat
        chord = chords[bar % 4]
        for pulse in range(8):
            chord_note = chord[pulse % len(chord)] + (12 if pulse % 2 else 0)
            add_note(
                track, start + pulse * beat / 2, 0.32 * beat, chord_note, 0.10, kind="wood", release=0.06, decay=2.2
            )
        for pulse in range(4):
            add_note(track, start + pulse * beat, 0.55 * beat, bass[bar % 4], 0.12, kind="triangle", release=0.08)
        for offset, note, length in melody:
            variation = 2 if bar % 4 == 3 and offset >= 2 else 0
            add_note(
                track,
                start + offset * beat,
                length * beat,
                note + variation,
                0.18,
                kind="bell",
                release=0.08,
                decay=2.6,
            )
        for eighth in range(8):
            add_shaker(track, start + eighth * beat / 2, 0.022 if eighth in (2, 6) else 0.010, rng)
    return track


def main() -> None:
    normalize_and_write(build_forest(), ASSET_DIR / "carrot-forest-original.wav")
    normalize_and_write(build_avatar(), ASSET_DIR / "avatar-studio-original.wav")


if __name__ == "__main__":
    main()

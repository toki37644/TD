from pathlib import Path
import subprocess

import numpy as np


FFMPEG = r'C:\Program Files\Derivative\TouchDesigner\bin\ffmpeg.exe'
ROOT = Path(__file__).parent
RATE = 12000
SIZE = 1024
HOP = 256
FREQUENCIES = np.fft.rfftfreq(SIZE, 1 / RATE)
LOW = (FREQUENCIES >= 25) & (FREQUENCIES <= 130)
HIGH = (FREQUENCIES >= 1800) & (FREQUENCIES <= 6000)
WINDOW = np.hanning(SIZE)


def db(amplitude):
    return 20 * np.log10(np.maximum(amplitude, 1e-10))


def describe(path):
    samples = subprocess.check_output([
        FFMPEG, '-v', 'error', '-i', str(path), '-vn', '-ac', '1',
        '-ar', str(RATE), '-f', 'f32le', '-'
    ])
    signal = np.frombuffer(samples, dtype=np.float32)
    print(f'\n{path.stem}: {len(signal) / RATE:.1f}s')
    for start in range(0, min(240, len(signal) // RATE - 8), 12):
        segment = signal[start * RATE:(start + 12) * RATE]
        frames = np.lib.stride_tricks.sliding_window_view(segment, SIZE)[::HOP]
        amplitudes = np.abs(np.fft.rfft(frames * WINDOW)) / (SIZE / 2)
        rms = db(np.sqrt(np.mean(segment ** 2)))
        bass = db(np.sqrt(np.sum(amplitudes[:, LOW] ** 2, axis=1)))
        treble = db(np.sqrt(np.sum(amplitudes[:, HIGH] ** 2, axis=1)))
        attack = np.maximum(0, np.diff(treble))
        print(f'{start:3d} {rms:5.1f} {np.median(bass):5.1f} {np.percentile(bass, 90) - np.median(bass):4.1f} {np.median(treble):6.1f} {np.percentile(attack, 95):4.1f}')


print('START RMS BASS BASS RANGE TREBLE ATTACK (dB)')
for name in ('overview', 'sun', 'mercury', 'venus', 'earth', 'mars'):
    describe(ROOT / f'{name}.mp3')

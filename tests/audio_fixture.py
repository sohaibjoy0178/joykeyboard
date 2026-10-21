"""Decode test/benchmark audio only; no decoder dependency in the shipped app."""
import av
import numpy as np


def decode_audio(source, sampling_rate=16000):
    arrays = []
    with av.open(source) as container:
        resampler = av.AudioResampler(format="fltp", layout="mono", rate=sampling_rate)
        for frame in container.decode(audio=0):
            arrays.extend(item.to_ndarray().reshape(-1) for item in resampler.resample(frame))
        arrays.extend(item.to_ndarray().reshape(-1) for item in resampler.resample(None))
    return np.concatenate(arrays).astype(np.float32) if arrays else np.empty(0, dtype=np.float32)

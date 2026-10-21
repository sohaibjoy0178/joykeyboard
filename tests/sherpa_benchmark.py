"""Opt-in Windows benchmark; models/runtime stay in ignored artifacts until the gate passes."""
import argparse
import ctypes
import hashlib
import importlib.util
import json
import os
import platform
import sys
import time
import unicodedata
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if importlib.util.find_spec("sherpa_onnx") is None:
    sys.path.insert(0, str(ROOT / "artifacts/sherpa-runtime"))


def normalise(text):
    text = unicodedata.normalize("NFC", text.lower())
    return " ".join("".join(" " if unicodedata.category(c).startswith("P") else c
                            for c in text if unicodedata.category(c) != "Cf").split())


def distance(a, b):
    row = list(range(len(b) + 1))
    for i, left in enumerate(a, 1):
        nxt = [i]
        for j, right in enumerate(b, 1):
            nxt.append(min(nxt[-1] + 1, row[j] + 1, row[j - 1] + (left != right)))
        row = nxt
    return row[-1]


class Memory(ctypes.Structure):
    _fields_ = [("cb", ctypes.c_ulong), ("faults", ctypes.c_ulong),
                *[(name, ctypes.c_size_t) for name in (
                    "peak_ws", "ws", "peak_paged", "paged", "peak_nonpaged", "nonpaged",
                    "pagefile", "peak_pagefile", "private")]]


def memory():
    result = Memory()
    result.cb = ctypes.sizeof(result)
    query = ctypes.windll.psapi.GetProcessMemoryInfo
    query.argtypes = (ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong)
    assert query(ctypes.c_void_p(-1), ctypes.byref(result), result.cb)
    return {"working_set_mib": result.ws / 2**20, "private_mib": result.private / 2**20,
            "process_peak_working_set_mib": result.peak_ws / 2**20}


def run(args):
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("OMP_NUM_THREADS", "2")
    import numpy as np

    import voice

    samples = json.loads(args.fixtures.read_text(encoding="utf-8"))["samples"]
    report = {"engine": args.engine, "method": args.method, "threads": 1,
              "realtime_replay": args.realtime, "machine": platform.machine(),
              "logical_cpus": os.cpu_count(), "baseline_memory": memory(), "samples": []}
    started, cpu = time.perf_counter(), time.process_time()
    if args.engine == "sherpa":
        import sherpa_onnx
        model = args.model_dir
        recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
            encoder=str(model / "encoder.onnx"), decoder=str(model / "decoder.onnx"),
            joiner=str(model / "joiner.onnx"), tokens=str(model / "tokens.txt"),
            num_threads=1, decoding_method=args.method, max_active_paths=4,
            model_type="zipformer2", provider="cpu", enable_endpoint_detection=False,
        )
        report["sherpa_version"] = sherpa_onnx.__version__
    else:
        recognizer = voice.Recognizer(ROOT / "artifacts/empty-model-cache")
    report["load_seconds"] = time.perf_counter() - started
    report["load_cpu_seconds"] = time.process_time() - cpu
    report["loaded_memory"] = memory()
    if args.engine == "sherpa":
        report["model_sha256"] = {}
        for path in model.iterdir():
            if path.is_file():
                with path.open("rb") as file:
                    report["model_sha256"][path.name] = hashlib.file_digest(file, "sha256").hexdigest()
    for sample in samples:
        path = ROOT / Path(sample["path"]).with_suffix(".pcm.wav")
        with wave.open(str(path), "rb") as wav:
            assert wav.getnchannels() == 1 and wav.getsampwidth() == 2
            rate, pcm = wav.getframerate(), wav.readframes(wav.getnframes())
        audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768
        duration, events = len(audio) / rate, []
        started, cpu = time.perf_counter(), time.process_time()
        if args.engine == "sherpa":
            stream = recognizer.create_stream()
            previous = ""
            step = rate // 10
            for offset in range(0, len(audio), step):
                end = min(len(audio), offset + step)
                if args.realtime:
                    time.sleep(max(0, started + end / rate - time.perf_counter()))
                stream.accept_waveform(rate, audio[offset:end])
                while recognizer.is_ready(stream):
                    recognizer.decode_stream(stream)
                text = recognizer.get_result(stream)
                if text and text != previous:
                    events.append({"audio_seconds": end / rate,
                                   "wall_seconds": time.perf_counter() - started, "text": text})
                    previous = text
            stream.accept_waveform(rate, np.zeros(rate // 2, dtype=np.float32))
            stream.input_finished()
            while recognizer.is_ready(stream):
                recognizer.decode_stream(stream)
            text = recognizer.get_result(stream)
        else:
            text = recognizer.transcribe(pcm, rate, "bn-BD", "google")
        elapsed, used_cpu = time.perf_counter() - started, time.process_time() - cpu
        reference = sample["row"][2]
        ref, hyp = normalise(reference), normalise(text)
        ref_chars, hyp_chars = ref.replace(" ", ""), hyp.replace(" ", "")
        row = {"file": path.name, "reference": reference, "text": text, "audio_seconds": duration,
               "wall_seconds": elapsed, "cpu_seconds": used_cpu,
               "one_core_percent": used_cpu / elapsed * 100,
               "cpu_seconds_per_audio_second": used_cpu / duration,
               "word_errors": distance(ref.split(), hyp.split()), "reference_words": len(ref.split()),
               "character_errors": distance(ref_chars, hyp_chars), "reference_characters": len(ref_chars),
               "first_partial_seconds": events[0]["wall_seconds"] if events else None,
               "finish_after_audio_seconds": elapsed - duration if args.realtime else None,
               "partials": events, "memory": memory()}
        report["samples"].append(row)
        print(json.dumps({k: v for k, v in row.items() if k != "partials"}, ensure_ascii=True), flush=True)
    report["aggregate_wer"] = sum(x["word_errors"] for x in report["samples"]) / sum(x["reference_words"] for x in report["samples"])
    report["aggregate_cer"] = sum(x["character_errors"] for x in report["samples"]) / sum(x["reference_characters"] for x in report["samples"])
    report["warm_memory"] = memory()
    started, cpu = time.perf_counter(), time.process_time()
    time.sleep(5)
    seconds, used_cpu = time.perf_counter() - started, time.process_time() - cpu
    report["loaded_idle"] = {"seconds": seconds, "one_core_percent": used_cpu / seconds * 100, **memory()}
    report["peak_working_set_mib"] = memory()["process_peak_working_set_mib"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(args.output), "wer": report["aggregate_wer"], "cer": report["aggregate_cer"],
                      "loaded_memory": report["loaded_memory"], "peak_working_set_mib": report["peak_working_set_mib"]}, ensure_ascii=True))


if __name__ == "__main__":
    assert distance("abc", "adc") == 1 and distance([], [1, 2]) == 2
    assert normalise("  HELLO, world!  ") == "hello world"
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", choices=("google", "sherpa"), required=True)
    parser.add_argument("--method", choices=("greedy_search", "modified_beam_search"), default="greedy_search")
    parser.add_argument("--realtime", action="store_true")
    parser.add_argument("--fixtures", type=Path, default=ROOT / "tests/fixtures/sherpa-bengali.json")
    parser.add_argument("--model-dir", type=Path, default=ROOT / "artifacts/sherpa-bn-model")
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())

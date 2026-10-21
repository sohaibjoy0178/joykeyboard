# Speech pause detector

speech_vad.py contains only the Silero VAD options, timestamp segmentation and CPU inference adapter from faster-whisper 1.2.1 (MIT), https://github.com/SYSTRAN/faster-whisper/blob/v1.2.1/faster_whisper/vad.py . Unused transcription/chunk mapping helpers are omitted; the model path points to assets/vad. Retained license: FASTER-WHISPER-VAD-LICENSE.txt.

assets/vad/silero_vad_v6.onnx is the unchanged Silero VAD v6 model distributed with that release, adapted upstream from https://github.com/snakers4/silero-vad (MIT). This detector identifies speech/silence only; it does not transcribe speech or include Whisper weights/runtime.

Silero model SHA-256: 4cbf549b8326f60f80f2536d9eefeb450a9abe83365a098031c89719f1be17d2. Silero license: SILERO-LICENSE.txt.

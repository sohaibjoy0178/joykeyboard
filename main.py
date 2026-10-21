"""JoyKeyboard executable entry point."""
import argparse
import multiprocessing
import os
import sys
import traceback


def main():
    multiprocessing.freeze_support()
    # Avoid numerical-library thread pools competing with the keyboard/UI on small PCs.
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("OMP_NUM_THREADS", "2")
    parser = argparse.ArgumentParser(description="JoyKeyboard desktop voice keyboard")
    parser.add_argument("--smoke-test", metavar="PNG", help="Render UI, save screenshot and exit")
    parser.add_argument("--check-audio", metavar="WAV", help=argparse.SUPPRESS)
    parser.add_argument("--check-output", metavar="JSON", help=argparse.SUPPRESS)
    parser.add_argument("--check-engine", choices=("google", "sherpa"), default="google", help=argparse.SUPPRESS)
    parser.add_argument("--check-language", choices=("bn-BD", "en-US"), default="en-US", help=argparse.SUPPRESS)
    parser.add_argument("--check-auto-pause", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.check_audio and not args.check_output:
        parser.error("--check-audio requires --check-output")
    try:
        if args.check_audio:
            from pathlib import Path

            from diagnostics import check_audio
            check_audio(Path(args.check_audio), args.check_engine, Path(args.check_output), args.check_language, auto_pause=args.check_auto_pause)
            return 0
        from app import run
        return run(args.smoke_test)
    except Exception:
        from pathlib import Path

        from core import data_directory
        directory = data_directory()
        directory.mkdir(parents=True, exist_ok=True)
        error = traceback.format_exc()
        (directory / "startup-error.log").write_text(error, encoding="utf-8")
        if sys.stderr:
            print(error, file=sys.stderr)
        if sys.platform == "win32" and not (args.check_audio or args.smoke_test):
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, f"JoyKeyboard could not start. Details saved in:\n{Path(directory / 'startup-error.log')}", "JoyKeyboard", 0x10)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

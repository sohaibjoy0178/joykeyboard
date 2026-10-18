"""Measure the same visible, idle source window before and after changes."""
import ctypes
import json
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["LOCALAPPDATA"] = tempfile.mkdtemp(prefix="joy-idle-")

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from app import JoyWindow


class Memory(ctypes.Structure):
    _fields_ = [("cb", ctypes.c_ulong), ("faults", ctypes.c_ulong),
                *[(name, ctypes.c_size_t) for name in
                  ("peak_ws", "ws", "peak_paged", "paged", "peak_nonpaged", "nonpaged", "pagefile", "peak_pagefile", "private")]]


application = QApplication([])
application.setQuitOnLastWindowClosed(False)
window = JoyWindow(smoke=True)
window.show_compact()
window.poll.start(40)
started = []


def begin():
    started.extend((time.perf_counter(), time.process_time()))


def finish():
    elapsed, cpu = time.perf_counter() - started[0], time.process_time() - started[1]
    memory = Memory()
    memory.cb = ctypes.sizeof(memory)
    ctypes.windll.kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    ctypes.windll.psapi.GetProcessMemoryInfo.argtypes = (ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong)
    assert ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(memory), memory.cb)
    result = dict(seconds=round(elapsed, 2), cpu_seconds=round(cpu, 4),
                  one_core_percent=round(cpu / elapsed * 100, 3),
                  working_set_mib=round(memory.ws / 2**20, 2), private_mib=round(memory.private / 2**20, 2),
                  peak_working_set_mib=round(memory.peak_ws / 2**20, 2),
                  bar_size=[window.compact.width(), window.compact.height()])
    Path(sys.argv[1]).write_text(json.dumps(result, indent=2), encoding="utf-8")
    window.close()
    application.quit()


QTimer.singleShot(1500, begin)
QTimer.singleShot(11500, finish)
application.exec()

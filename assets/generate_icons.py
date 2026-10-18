"""Render the original SVG and verify the Windows ICO directory."""
import os
import struct
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QRectF
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


def main():
    _application = QGuiApplication.instance() or QGuiApplication([])
    directory = Path(__file__).resolve().parent
    renderer = QSvgRenderer(str(directory / "joykeyboard.svg"))
    assert renderer.isValid(), "Invalid source SVG"
    frames = []
    sizes = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)
    for size in (*sizes, 1024):
        image = QImage(size, size, QImage.Format.Format_ARGB32)
        image.fill(0)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(painter, QRectF(0, 0, size, size))
        painter.end()
        assert image.pixelColor(0, 0).alpha() == 0
        assert image.pixelColor(size // 2, size // 2).alpha() == 255
        if size == 1024:
            assert image.save(str(directory / "joykeyboard.png"))
        else:
            data = QByteArray()
            buffer = QBuffer(data)
            buffer.open(QIODevice.OpenModeFlag.WriteOnly)
            assert image.save(buffer, "PNG")
            frames.append(bytes(data))
    offset = 6 + len(frames) * 16
    entries = []
    for size, data in zip(sizes, frames):
        entries.append(struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(data), offset))
        offset += len(data)
    icon = struct.pack("<HHH", 0, 1, len(frames)) + b"".join(entries + frames)
    (directory / "joykeyboard.ico").write_bytes(icon)
    assert struct.unpack_from("<HHH", icon) == (0, 1, len(sizes))
    for index, size in enumerate(sizes):
        width, height, _, _, planes, depth, length, start = struct.unpack_from("<BBBBHHII", icon, 6 + index * 16)
        assert (width or 256, height or 256, planes, depth) == (size, size, 1, 32)
        decoded = QImage.fromData(icon[start:start + length], "PNG")
        assert (decoded.width(), decoded.height()) == (size, size)
    print(f"Validated PNG 1024×1024 and ICO sizes {sizes}")


if __name__ == "__main__":
    main()

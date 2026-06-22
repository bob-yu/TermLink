import struct
import sys
from pathlib import Path

from PyQt5.QtCore import QByteArray, QBuffer, QIODevice, QRectF, Qt
from PyQt5.QtGui import QGuiApplication, QImage, QPainter
from PyQt5.QtSvg import QSvgRenderer


ROOT = Path(__file__).resolve().parents[1]
SVG_PATH = ROOT / "ui" / "resources" / "icons" / "app.svg"
ASSETS_DIR = ROOT / "assets"
ICO_PATH = ASSETS_DIR / "app-icon.ico"
PNG_PATH = ASSETS_DIR / "app-icon.png"


def render_png(size: int) -> bytes:
    renderer = QSvgRenderer(str(SVG_PATH))
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing, True)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()

    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(data)


def write_ico(images):
    header = struct.pack("<HHH", 0, 1, len(images))
    entries = []
    payload = bytearray()
    offset = 6 + 16 * len(images)

    for size, png_data in images:
        width = 0 if size >= 256 else size
        height = 0 if size >= 256 else size
        entries.append(struct.pack(
            "<BBBBHHII",
            width,
            height,
            0,
            0,
            1,
            32,
            len(png_data),
            offset,
        ))
        payload.extend(png_data)
        offset += len(png_data)

    with ICO_PATH.open("wb") as fh:
        fh.write(header)
        for entry in entries:
            fh.write(entry)
        fh.write(payload)


def main():
    if not SVG_PATH.exists():
        raise FileNotFoundError(SVG_PATH)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    _ = app
    sizes = [16, 24, 32, 48, 64, 128, 256]
    png_images = [(size, render_png(size)) for size in sizes]
    write_ico(png_images)
    PNG_PATH.write_bytes(render_png(256))
    print(f"Generated {ICO_PATH}")
    print(f"Generated {PNG_PATH}")


if __name__ == "__main__":
    main()

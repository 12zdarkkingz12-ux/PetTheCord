"""
petpet_gen.py
-------------
توليد الـ petpet GIF بشكل مستقل باستخدام Pillow فقط.
يقرأ الـ frames من assets/images/pet_frames/ (مبنية في المشروع).
"""
from collections import defaultdict
from itertools import chain
from io import BytesIO
from pathlib import Path
from random import randrange
from typing import List, Tuple, Union

from PIL import Image
from PIL.Image import Image as PILImage

# ── مسار الـ frames ────────────────────────────────────────────────────────────
_FRAMES_DIR = Path(__file__).parent / "assets" / "images" / "pet_frames"
_FRAME_COUNT = 10
_RESOLUTION  = (128, 128)
_DELAY_MS    = 20


# ── Transparent GIF Helper (من مصدر petpetgif الأصلي) ─────────────────────────

class _TransparentGifConverter:
    _PALETTE_SLOTS = set(range(256))

    def __init__(self, img_rgba: PILImage, alpha_threshold: int = 0):
        self._img_rgba       = img_rgba
        self._alpha_threshold = alpha_threshold

    def _process_pixels(self):
        self._transparent_pixels = {
            idx for idx, alpha in enumerate(
                self._img_rgba.getchannel("A").getdata()
            ) if alpha <= self._alpha_threshold
        }

    def _set_parsed_palette(self):
        palette = self._img_p.getpalette()
        self._used = {
            idx for pal_idx, idx in enumerate(self._img_p_data)
            if pal_idx not in self._transparent_pixels
        }
        self._parsed = {idx: tuple(palette[idx*3:idx*3+3]) for idx in self._used}

    def _get_similar_idx(self):
        old = self._parsed[0]
        dist = defaultdict(list)
        for idx in range(1, 256):
            c = self._parsed[idx]
            if c == old:
                return idx
            dist[sum(abs(a-b) for a, b in zip(old, c))].append(idx)
        return dist[sorted(dist)[0]][0]

    def _remap_zero(self):
        free = self._PALETTE_SLOTS - self._used
        new = free.pop() if free else self._get_similar_idx()
        self._used.add(new)
        self._replaces["from"].append(0)
        self._replaces["to"].append(new)
        self._parsed[new] = self._parsed[0]
        del self._parsed[0]

    def _unused_color(self):
        used = set(self._parsed.values())
        while True:
            c = (randrange(256), randrange(256), randrange(256))
            if c not in used:
                return c

    def _process_palette(self):
        self._set_parsed_palette()
        if 0 in self._used:
            self._remap_zero()
        self._parsed[0] = self._unused_color()

    def _adjust_pixels(self):
        if self._replaces["from"]:
            table = bytearray.maketrans(
                bytes(self._replaces["from"]), bytes(self._replaces["to"])
            )
            self._img_p_data = self._img_p_data.translate(table)
        for idx in self._transparent_pixels:
            self._img_p_data[idx] = 0
        self._img_p.frombytes(bytes(self._img_p_data))

    def _adjust_palette(self):
        unused = self._unused_color()
        final  = chain.from_iterable(self._parsed.get(x, unused) for x in range(256))
        self._img_p.putpalette(final)

    def process(self) -> PILImage:
        self._img_p      = self._img_rgba.convert("P")
        self._img_p_data = bytearray(self._img_p.tobytes())
        self._replaces   = {"from": [], "to": []}
        self._process_pixels()
        self._process_palette()
        self._adjust_pixels()
        self._adjust_palette()
        self._img_p.info["transparency"] = 0
        self._img_p.info["background"]   = 0
        return self._img_p


def _to_palette_frames(images: List[PILImage]) -> List[PILImage]:
    result = []
    for frame in images:
        thumb = frame.copy().convert("RGBA")
        thumb.thumbnail(frame.size, reducing_gap=3.0)
        result.append(_TransparentGifConverter(thumb).process())
    return result


# ── الدالة الرئيسية ────────────────────────────────────────────────────────────

def make_petpet(avatar_bytes: bytes) -> bytes:
    """
    تأخذ bytes صورة الأفاتار وترجع bytes الـ GIF المتحرك.
    لا تحتاج أي مكتبة خارجية غير Pillow.
    """
    base = Image.open(BytesIO(avatar_bytes)).convert("RGBA").resize(_RESOLUTION)
    frames: List[PILImage] = []

    for i in range(_FRAME_COUNT):
        squeeze  = i if i < _FRAME_COUNT / 2 else _FRAME_COUNT - i
        width    = 0.8 + squeeze * 0.02
        height   = 0.8 - squeeze * 0.05
        offset_x = (1 - width)  * 0.5 + 0.1
        offset_y = (1 - height) - 0.08

        canvas = Image.new("RGBA", _RESOLUTION, (0, 0, 0, 0))
        resized = base.resize((
            round(width  * _RESOLUTION[0]),
            round(height * _RESOLUTION[1]),
        ))
        canvas.paste(resized, (
            round(offset_x * _RESOLUTION[0]),
            round(offset_y * _RESOLUTION[1]),
        ))

        hand_path = _FRAMES_DIR / f"pet{i}.gif"
        hand = Image.open(hand_path).convert("RGBA").resize(_RESOLUTION)
        canvas.paste(hand, mask=hand)
        frames.append(canvas)

    palette_frames = _to_palette_frames(frames)
    out = BytesIO()
    palette_frames[0].save(
        out,
        format="GIF",
        save_all=True,
        append_images=palette_frames[1:],
        duration=_DELAY_MS,
        disposal=2,
        loop=0,
        optimize=False,
    )
    out.seek(0)
    return out.read()

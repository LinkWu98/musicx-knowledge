"""Reproduce the original pitch-position diagram; no third-party artwork."""
from pathlib import Path
from PIL import Image, ImageDraw, PngImagePlugin

image = Image.new('RGB', (1200, 460), 'white')
draw = ImageDraw.Draw(image)
for y in [100, 145, 190, 235, 280]:
    draw.line((110, y, 1090, y), fill='#202522', width=3)
for x, y in [(340, 325), (610, 302), (880, 280)]:
    draw.ellipse((x-24, y-16, x+24, y+16), fill='#202522')
    draw.line((x+22, y, x+22, y-115), fill='#202522', width=5)
draw.line((290, 325, 390, 325), fill='#202522', width=3)
metadata = PngImagePlugin.PngInfo()
metadata.add_text('Source', 'Original geometric pitch-position diagram drawn by scripts/make_staff.py for MusicX, 2026-10-02. Middle C, D, E on treble staff; no rhythmic meaning.')
image.save(Path(__file__).resolve().parents[1] / 'assets/notation/staff.png', pnginfo=metadata)

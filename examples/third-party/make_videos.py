#!/usr/bin/env python3
"""make_videos.py -- render each case's recorded run as an animated GIF and an MP4.

Reads examples/third-party/demo/scenes.json, which demo.py writes from the real
checker output, and draws it as a terminal session: each command is typed, its
output appears, and the final screen holds. Writes demo/<case>.gif (shown inline in
DEMO.md) and demo/<case>.mp4. Needs Pillow and ffmpeg; nothing is downloaded.
"""
import json, os, shutil, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo")
FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 15)
W, LH, PAD, TOP, COLS = 1120, 22, 18, 46, 118
COL = {"cmd": (230, 237, 243), "dim": (139, 148, 158), "del": (255, 123, 114), "ok": (63, 185, 80),
       "bad": (248, 81, 73), "out": (201, 209, 217), "head": (210, 168, 255), "warn": (227, 179, 65)}
BG, FRAME_MS, TYPE_CHARS = (13, 17, 23), 60, 4


def cut(t):
    return t if len(t) <= COLS else t[:COLS - 1] + "…"


def frame(title, shown, height):
    im = Image.new("RGB", (W, height), BG)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, W - 1, height - 1], 10, outline=(48, 54, 61), width=2)
    for i, c in enumerate([(255, 95, 87), (254, 188, 46), (40, 200, 64)]):
        d.ellipse([16 + i * 20, 12, 28 + i * 20, 24], fill=c)
    d.text((84, 10), title, font=FONT, fill=COL["dim"])
    for i, (kind, text) in enumerate(shown):
        d.text((PAD, TOP + i * LH), cut(text), font=FONT, fill=COL[kind])
    return im


def render(scene):
    lines = scene["lines"]; height = TOP + len(lines) * LH + PAD
    frames, shown = [], []
    for kind, text in lines:
        if kind == "cmd":                       # typed
            for n in range(0, len(cut(text)) + 1, TYPE_CHARS):
                frames.append((frame(scene["title"], shown + [(kind, text[:n] + "▌")], height), FRAME_MS))
            shown.append((kind, text)); frames.append((frame(scene["title"], shown, height), 350))
        else:                                   # printed
            shown.append((kind, text)); frames.append((frame(scene["title"], shown, height), 260))
    frames.append((frame(scene["title"], shown, height), 6000))
    return frames


def main():
    scenes = json.load(open(os.path.join(HERE, "scenes.json")))
    for sc in scenes:
        frames = render(sc)
        gif = os.path.join(HERE, sc["file"] + ".gif")
        pal = [f.convert("P", palette=Image.ADAPTIVE, colors=32) for f, _ in frames]
        pal[0].save(gif, save_all=True, append_images=pal[1:], duration=[ms for _, ms in frames], loop=0, optimize=True)
        tmp = tempfile.mkdtemp()
        try:
            listing = []
            for i, (f, ms) in enumerate(frames):
                p = os.path.join(tmp, f"{i:05d}.png"); f.save(p)
                listing += [f"file '{p}'", f"duration {ms / 1000:.3f}"]
            listing.append(f"file '{p}'")
            open(os.path.join(tmp, "list.txt"), "w").write("\n".join(listing))
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", os.path.join(tmp, "list.txt"),
                            "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2,fps=25", "-pix_fmt", "yuv420p", "-c:v", "libx264",
                            "-movflags", "+faststart", os.path.join(HERE, sc["file"] + ".mp4")], check=True)
        finally:
            shutil.rmtree(tmp)
        print(sc["file"], len(frames), "frames", os.path.getsize(gif) // 1024, "KB gif",
              os.path.getsize(os.path.join(HERE, sc["file"] + ".mp4")) // 1024, "KB mp4")


if __name__ == "__main__":
    main()

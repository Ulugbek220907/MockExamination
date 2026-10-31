"""
The pictures and the video for a post, drawn in TestDay's look (warm paper, deep ink, Schibsted Grotesk).

card.jpg   1080x1350 (4:5)  for Instagram, Facebook and Threads
video.mp4  1080x1920 (9:16) for YouTube Shorts, TikTok, Instagram Reels and Facebook Reels

ffmpeg comes from the imageio-ffmpeg package, so nothing needs installing on the server.
"""

import os
import shutil
import subprocess
import tempfile
import time

from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(BASE_DIR, "assets", "fonts", "SchibstedGrotesk-Variable.ttf")
GROUND = (233, 232, 226)
INK = (15, 26, 48)
MUTED = (96, 106, 124)
HAIRLINE = (200, 199, 192)
MUTED_ON_INK = (160, 169, 186)
FPS = 30
FADE = 0.4  # seconds of cross-fade between scenes


def font(size, weight=400):
    f = ImageFont.truetype(FONT, size)
    f.set_variation_by_axes([weight])
    return f


def wrap(draw, text, fnt, width):
    """Lines of `text` that each fit in `width` pixels (words are never split)."""
    lines = []
    for paragraph in text.split("\n"):
        line = ""
        for word in paragraph.split():
            trial = f"{line} {word}".strip()
            if line and draw.textlength(trial, font=fnt) > width:
                lines.append(line)
                line = word
            else:
                line = trial
        lines.append(line)
    return lines


def fit(draw, text, width, height, start, low, weight, spacing=1.18):
    """The biggest size, between `start` and `low`, at which the wrapped text fits the box."""
    size = start
    while True:
        fnt = font(size, weight)
        lines = wrap(draw, text, fnt, width)
        if len(lines) * size * spacing <= height or size <= low:
            return fnt, lines, size
        size -= 2


def fit_paragraphs(draw, paragraphs, width, height, start, low):
    """Like fit(), for a list of paragraphs: the biggest size at which all of them, with gaps, fit the box."""
    size = start
    while True:
        fnt = font(size, 400)
        wrapped = [wrap(draw, p, fnt, width) for p in paragraphs]
        used = sum(len(w) for w in wrapped) * size * 1.3 + (len(wrapped) - 1) * size * 0.42
        if used <= height or size <= low:
            return fnt, wrapped, size
        size -= 2


def spaced(draw, xy, text, fnt, fill, tracking):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += draw.textlength(ch, font=fnt) + tracking


def draw_canvas(size, kicker, headline, lines, dark=False, wordmark=True, footer_pill="Five free tests in every module"):
    w, h = size
    bg, fg, soft = (INK, GROUND, MUTED_ON_INK) if dark else (GROUND, INK, MUTED)
    img = Image.new("RGB", size, bg)
    d = ImageDraw.Draw(img)
    m = round(w * 0.078)            # side margin
    inner = w - 2 * m
    scale = w / 1080
    tall = h > 1500                 # the 9:16 video frame; the 4:5 card is shorter
    # top: the wordmark
    if wordmark:
        d.text((m, round(m * 0.9)), "TestDay", font=font(round(44 * scale), 700), fill=fg)
    # the text block (kicker, headline, body) sits in the middle zone, a little above the centre
    zone_top, zone_bottom = round(h * 0.15), round(h * 0.82)
    zone = zone_bottom - zone_top
    kicker_h = round(30 * scale) + round(40 * scale)
    gap = round(48 * scale)
    head_max = round(zone * (0.5 if lines else 0.8)) - kicker_h
    hf, hl, hs = fit(d, headline, inner, head_max, round((150 if tall else 118) * scale), round(54 * scale), 700, 1.08)
    head_h = round(len(hl) * hs * 1.08)
    body = None
    if lines:
        body_max = zone - kicker_h - head_h - gap
        bf, paragraphs, bs = fit_paragraphs(d, lines, inner, body_max, round((64 if tall else 54) * scale), round(30 * scale))
        body_h = round(sum(len(p) for p in paragraphs) * bs * 1.3 + (len(paragraphs) - 1) * bs * 0.42)
        body = (bf, paragraphs, bs, body_h)
    block = kicker_h + head_h + (gap + body[3] if body else 0)
    y = zone_top + round(max(0, zone - block) * 0.42)
    spaced(d, (m, y), kicker, font(round(30 * scale), 600), soft, round(4 * scale))
    y += kicker_h
    for line in hl:
        d.text((m, y), line, font=hf, fill=fg)
        y += round(hs * 1.08)
    if body:
        bf, paragraphs, bs, _ = body
        y += gap
        for lines_of_paragraph in paragraphs:
            for line in lines_of_paragraph:
                d.text((m, y), line, font=bf, fill=fg)
                y += round(bs * 1.3)
            y += round(bs * 0.42)
    # bottom: a hairline, the address and a pill
    base = h - round(h * 0.105)
    d.line((m, base - round(34 * scale), w - m, base - round(34 * scale)), fill=(70, 80, 100) if dark else HAIRLINE, width=2)
    d.text((m, base), "testday.uz", font=font(round(40 * scale), 700), fill=fg)
    if footer_pill:
        pf = font(round(30 * scale), 600)
        tw = d.textlength(footer_pill, font=pf)
        pw, ph = tw + round(52 * scale), round(64 * scale)
        x0 = w - m - pw
        d.rounded_rectangle((x0, base - round(8 * scale), x0 + pw, base - round(8 * scale) + ph), radius=ph // 2,
                            fill=GROUND if dark else INK)
        d.text((x0 + round(26 * scale), base - round(8 * scale) + round(15 * scale)), footer_pill, font=pf, fill=INK if dark else GROUND)
    return img


def render_card(post, path):
    """The 4:5 picture for the day's post (JPEG, as Instagram accepts only JPEG)."""
    img = draw_canvas((1080, 1350), post.kicker, post.headline, post.lines)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, "JPEG", quality=92, optimize=True)
    return path


def render_scene(scene, path):
    img = draw_canvas((1080, 1920), scene.kicker, scene.headline, scene.lines, dark=scene.dark, footer_pill="")
    img.save(path, "PNG")
    return path


def ffmpeg_exe():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def render_video(post, path):
    """The 9:16 video: one picture per scene, slowly zooming, cross-fading, with a silent soundtrack."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    work = tempfile.mkdtemp(prefix="scenes-")
    try:
        pngs = [render_scene(s, os.path.join(work, f"scene{i}.png")) for i, s in enumerate(post.scenes)]
        seconds = [s.seconds for s in post.scenes]
        n = len(pngs)
        cmd = [ffmpeg_exe(), "-y", "-hide_banner", "-loglevel", "error"]
        for png in pngs:
            cmd += ["-i", png]
        cmd += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]
        parts = []
        for i in range(n):
            frames = round((seconds[i] + FADE) * FPS)
            parts.append(f"[{i}:v]scale=1620:2880,zoompan=z='min(1+0.0004*on,1.06)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                         f":d={frames}:s=1080x1920:fps={FPS},setsar=1,format=yuv420p[v{i}]")
        last, offset = "v0", 0.0
        for i in range(1, n):
            offset += seconds[i - 1]
            out = f"x{i}"
            parts.append(f"[{last}][v{i}]xfade=transition=fade:duration={FADE}:offset={offset:.2f}[{out}]")
            last = out
        total = sum(seconds) + FADE
        cmd += ["-filter_complex", ";".join(parts), "-map", f"[{last}]", "-map", f"{n}:a",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", "-r", str(FPS),
                "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-t", f"{total:.2f}", "-movflags", "+faststart", path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0 or not os.path.exists(path):
            raise RuntimeError(f"ffmpeg failed: {result.stderr[-400:]}")
        return path
    finally:
        shutil.rmtree(work, ignore_errors=True)


def render_day(post, folder):
    """Make the day's card and video in `folder` (kept if they already exist) and return their paths."""
    os.makedirs(folder, exist_ok=True)
    card, video = os.path.join(folder, "card.jpg"), os.path.join(folder, "video.mp4")
    if not os.path.exists(card):
        render_card(post, card)
    if not os.path.exists(video):
        render_video(post, video)
    return {"card": card, "video": video}


def cleanup(media_dir, keep_days):
    """Delete the folders of days older than `keep_days`."""
    if not os.path.isdir(media_dir):
        return
    cutoff = time.time() - keep_days * 86400
    for name in os.listdir(media_dir):
        path = os.path.join(media_dir, name)
        if os.path.isdir(path) and os.path.getmtime(path) < cutoff:
            shutil.rmtree(path, ignore_errors=True)

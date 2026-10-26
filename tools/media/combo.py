#!/usr/bin/env python3
"""Combined capture: a terminal cast and the browser, side by side, in sync.

depictio has casts and screenshots but nothing that shows both at once; for
Spectio the interesting moments are exactly the hand-overs ("the CLI stops at
the gate" -> "the review opens in the browser"), so this records them together.

How it works
- A local HTML page plays the cast with asciinema-player (copy installed in
  tools/media/node_modules by `npm ci`) in the left pane, and shows a browser
  frame in the right pane.
- The right pane switches between screenshots (tools/media/shots.py names, or
  image paths) at the cast times given in the YAML. The page polls the player's
  own clock, so the panes stay in sync whatever the machine speed.
- Playwright records the page (record_video_dir) to WebM; ffmpeg trims the
  page-load lead-in and writes an MP4 (H.264, faststart) and a GIF preview
  (palette, 10 fps) in tools/media/out/ (not committed).

    python3 tools/media/combo.py tools/media/combos/gate-review.yaml
    python3 tools/media/combo.py tools/media/combos/gate-review.yaml --html-only   # inspect the page

YAML (tools/media/combos/*.yaml):

    title: ...
    cast: docs/assets/casts/synthetic-gate.cast
    size: [1280, 720]
    terminal_fraction: 0.5
    gif_width: 960
    scenes:
      - {at: 0,  shot: run-detail, url: "spectio.example/runs/42", caption: "1 · ..."}
      - {at: 14, image: docs/assets/diagrams/gate-resume_light.png, caption: "..."}
"""

from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sanitize  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
PLAYER = Path(__file__).resolve().parent / "node_modules" / "asciinema-player" / "dist" / "bundle"
SHOTS = REPO / "docs" / "assets" / "shots"
OUT = REPO / "docs" / "assets" / "media"          # the MP4 (committed)
GIF_OUT = Path(__file__).resolve().parent / "out"  # the GIF preview: PR bodies only, generated on demand, not committed
MAX_SECONDS = 30                                   # documentation-system.md §5.3

PAGE = """<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="{player_css}">
<link rel="stylesheet" href="{theme_css}">
<style>
  html,body{{margin:0;width:{w}px;height:{h}px;overflow:hidden;background:#171a2e;
    font-family:Inter,system-ui,-apple-system,'Segoe UI',sans-serif}}
  .stage{{display:flex;gap:14px;padding:14px;box-sizing:border-box;height:{stage_h}px}}
  .term{{width:{term_w}px;flex:none;border-radius:10px;overflow:hidden;background:#0f1020;
    display:flex;flex-direction:column}}
  .bar{{height:28px;flex:none;display:flex;align-items:center;gap:7px;padding:0 12px;background:#22253a;
    color:#9a9eb0;font-size:12px}}
  .dot{{width:10px;height:10px;border-radius:50%}}
  #cast{{flex:1;display:flex;align-items:flex-start}}
  #cast .ap-wrapper,#cast .ap-player{{width:100%}}
  .browser{{flex:1;border-radius:10px;overflow:hidden;background:#fff;display:flex;flex-direction:column}}
  .browser .bar{{background:#eeeff5;color:#4d5065}}
  .url{{margin-left:10px;flex:1;background:#fff;border-radius:6px;padding:3px 10px;font-size:12px;color:#4d5065}}
  .view{{position:relative;flex:1;background:#f7f7fb}}
  .view img{{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;object-position:top center;
    opacity:0;transition:opacity .45s ease}}
  .view img.on{{opacity:1}}
  .caption{{height:{cap_h}px;display:flex;align-items:center;justify-content:center;color:#f7f7fb;
    font-size:21px;letter-spacing:.01em}}
  .caption b{{color:#a580f8;font-weight:600;margin-right:10px}}
  .note{{flex:none;font-size:11px;color:#6e7287}}
</style></head><body>
<div class="stage">
  <div class="term"><div class="bar"><span class="dot" style="background:#ff8787"></span>
    <span class="dot" style="background:#ffd43b"></span><span class="dot" style="background:#69db7c"></span>
    <span style="margin-left:8px">terminal</span></div><div id="cast"></div></div>
  <div class="browser"><div class="bar"><span class="dot" style="background:#ff8787"></span>
    <span class="dot" style="background:#ffd43b"></span><span class="dot" style="background:#69db7c"></span>
    <span class="url" id="url"></span><span class="note">{note}</span></div><div class="view">{imgs}</div></div>
</div>
<div class="caption" id="caption"></div>
<script src="{player_js}"></script>
<script>
  const scenes = {scenes};
  const player = AsciinemaPlayer.create({cast_src}, document.getElementById('cast'),
    {{fit: 'width', theme: 'spectio', idleTimeLimit: {idle}, speed: {speed}, autoPlay: false, controls: false}});
  let current = -1;
  function show(i) {{
    if (i === current) return;
    current = i;
    document.querySelectorAll('.view img').forEach((im, k) => im.classList.toggle('on', k === i));
    document.getElementById('url').textContent = scenes[i].url || '';
    const c = scenes[i].caption || '';
    const m = c.match(/^(\\d+ ·)\\s*(.*)$/);
    document.getElementById('caption').innerHTML = m ? '<b>' + m[1] + '</b>' + m[2] : c;
  }}
  show(0);
  window.__state = {{started: false, ended: false, t0: null}};
  player.addEventListener('ended', () => {{ window.__state.ended = true; }});
  window.__start = async () => {{
    await player.play();
    window.__state.started = true; window.__state.t0 = performance.now();
    setInterval(async () => {{
      const t = await player.getCurrentTime();
      let i = 0; scenes.forEach((s, k) => {{ if (t >= s.at) i = k; }});
      show(i);
    }}, 100);
  }};
</script></body></html>
"""


def build_page(spec: dict, workdir: Path) -> Path:
    w, h = spec.get("size", [1280, 720])
    cap_h = 64
    stage_h = h - cap_h
    term_w = int((w - 14 * 3) * float(spec.get("terminal_fraction", 0.5)))
    imgs, scenes = [], []
    for s in spec["scenes"]:
        img = (SHOTS / f"{s['shot']}_light.webp") if "shot" in s else (REPO / s["image"])
        if not img.exists():
            sys.exit(f"missing image {img} (run tools/media/shots.py run --shot {s.get('shot')})")
        imgs.append(f'<img src="{img.resolve().as_uri()}" alt="{html.escape(s.get("caption", ""))}">')
        scenes.append({"at": float(s["at"]), "caption": s.get("caption", ""), "url": s.get("url", "")})
    page = PAGE.format(
        w=w, h=h, stage_h=stage_h, cap_h=cap_h, term_w=term_w,
        player_css=(PLAYER / "asciinema-player.css").as_uri(),
        theme_css=(REPO / "docs/stylesheets/asciinema.css").as_uri(),
        player_js=(PLAYER / "asciinema-player.min.js").as_uri(),
        # inline: fetch() of a file:// URL is refused by Chromium
        cast_src=json.dumps({"data": (REPO / spec["cast"]).read_text(encoding="utf-8")}),
        idle=float(spec.get("idle_time_limit", 1.5)), speed=float(spec.get("speed", 1.0)),
        imgs="".join(imgs), scenes=json.dumps(scenes), note=html.escape(spec.get("note", "")),
    )
    out = workdir / "combo.html"
    out.write_text(page, encoding="utf-8")
    return out


def record(page: Path, spec: dict, video_dir: Path) -> tuple[Path, float, float]:
    """Record the page; return (webm, seconds to trim at the start, playback length)."""
    from playwright.sync_api import sync_playwright

    w, h = spec.get("size", [1280, 720])
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": w, "height": h}, record_video_dir=str(video_dir),
                                  record_video_size={"width": w, "height": h})
        t_ctx = time.monotonic()
        pg = ctx.new_page()
        pg.goto(page.as_uri())
        pg.wait_for_function("typeof AsciinemaPlayer !== 'undefined'")
        pg.wait_for_timeout(1200)  # player mounted, first frame and first image painted
        lead = time.monotonic() - t_ctx
        pg.evaluate("window.__start()")
        t_play = time.monotonic()
        limit = float(spec.get("max_seconds", 120))
        while not pg.evaluate("window.__state.ended") and time.monotonic() - t_play < limit:
            pg.wait_for_timeout(250)
        pg.wait_for_timeout(int(float(spec.get("tail_seconds", 2.0)) * 1000))
        length = time.monotonic() - t_play
        # hygiene: what is visible in the recorded page (captions, URL bar, terminal rows, image alt text)
        text = pg.evaluate("document.body.innerText + '\\n' + [...document.querySelectorAll('[alt],[title]')]"
                           ".map(e => (e.alt || '') + ' ' + (e.title || '')).join('\\n')")
        found = sanitize.leaks(text)
        if found:
            ctx.close(); browser.close()
            sys.exit(f"forbidden term visible in the recorded page: {found}")
        print("hygiene ok: no forbidden term in the recorded page text")
        video = pg.video.path()
        ctx.close()
        browser.close()
    return Path(video), lead, length


def encode(webm: Path, name: str, lead: float, length: float, spec: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    GIF_OUT.mkdir(parents=True, exist_ok=True)
    mp4, gif = OUT / f"{name}.mp4", GIF_OUT / f"{name}.gif"
    ff = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{lead:.2f}", "-t", f"{length:.2f}", "-i", str(webm)]
    subprocess.run(ff + ["-c:v", "libx264", "-preset", "slow", "-crf", str(spec.get("crf", 30)), "-pix_fmt", "yuv420p",
                         "-movflags", "+faststart", "-an", str(mp4)], check=True)
    gw = int(spec.get("gif_width", 960))
    fps = int(spec.get("gif_fps", 10))
    vf = f"fps={fps},scale={gw}:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle"
    subprocess.run(ff + ["-vf", vf, "-loop", "0", str(gif)], check=True)
    for f in (mp4, gif):
        print(f"-> {f.relative_to(REPO)}  ({f.stat().st_size / 1e6:.2f} MB)")
    if gif.stat().st_size > 4e6:
        sys.exit("GIF preview over 4 MB")
    if mp4.stat().st_size > 3e6:
        sys.exit("MP4 over 3 MB")


def main() -> None:
    ap = argparse.ArgumentParser(description="Record a terminal + browser capture")
    ap.add_argument("spec", type=Path)
    ap.add_argument("--html-only", action="store_true", help="write the page to the current directory and stop")
    a = ap.parse_args()
    spec = yaml.safe_load(a.spec.read_text())
    name = spec.get("name", a.spec.stem)
    with tempfile.TemporaryDirectory(prefix="spectio-combo-") as tmp:
        page = build_page(spec, Path(tmp))
        if a.html_only:
            dst = Path.cwd() / f"{name}.html"
            shutil.copy(page, dst)
            print(f"-> {dst}")
            return
        webm, lead, length = record(page, spec, Path(tmp) / "video")
        print(f"recorded {length:.1f} s (lead-in {lead:.1f} s trimmed)")
        if length > MAX_SECONDS:
            sys.exit(f"video is {length:.1f} s, over the {MAX_SECONDS} s limit: raise `speed` or shorten the cast")
        encode(webm, name, lead, length, spec)


if __name__ == "__main__":
    main()

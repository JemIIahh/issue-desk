#!/usr/bin/env python3
"""Cut the recording into video/out/issue-desk-demo.mp4 (under 3:00) and video/out/readme.gif.

    python3 video/cut.py [out-dir]

Reads <out>/frames/frames.json, <out>/actions.json (written by record.mjs) and optional Console stills
<out>/console-rooms.png and <out>/console-room.png (written by console-shots.mjs). Agent waits are sped up
and labelled; the typing-and-approving counter is summed from the logged maintainer actions.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent / "out").resolve()
HERE = Path(__file__).parent.resolve()
REPO = HERE.parent
FPS = 30
VID_W, VID_H, VID_X, VID_Y = 1340, 995, 40, 40
MAX_SECONDS = 175.0  # the hard limit is 3:00

STEPS = {
    3: ("1 · SWEEP", "Ask the desk what's hot.", "desk lists the issues drawing the most claims and PRs, then opens a room for the one you pick."),
    4: ("2 · A ROOM PER ISSUE", "Each hot issue gets its own room, opened by an agent from a template.", "run_template and link_rooms: desk builds the room, scout and bench join it."),
    5: ("3 · SCOUT", "Scout reads every claim and checks it against the real code.", "Bare requests versus plans, files that exist (✓) or don't (✗), near-duplicates."),
    6: ("4 · YOU DECIDE", "Nothing reaches GitHub until you say so.", "“post it” raises an approval card. You answer it in the thread: allow once, or decline."),
    7: ("5 · BENCH", "A second agent compares the competing PRs, safely.", "Each PR's tests run in a sealed box: no network, no credentials."),
    8: ("6 · YOUR CALL", "You make the call. The agents write it up.", "Polite review notes, each posted only through its own approval card."),
    9: ("7 · DIGEST", "What came in, what was decided, what is waiting on you.", ""),
}


def sh(*cmd, **kw):
    return subprocess.run([str(c) for c in cmd], check=True, capture_output=True, text=True, **kw)


def fmt_time(seconds):
    s = int(round(seconds))
    return f"{s // 60}m {s % 60:02d}s"


def load():
    frames = json.loads((OUT / "frames" / "frames.json").read_text())
    data = json.loads((OUT / "actions.json").read_text())
    return frames, data


frames, data = load()
actions = data["actions"]
marks = {a["row"]: a["start"] for a in actions if a["kind"] == "mark"}
waits = [a for a in actions if a["kind"] == "wait"]
skips = [a for a in actions if a["kind"] == "skip"]  # stretches of the recording that are not shown at all
acts = [a for a in actions if a["kind"] == "act"]
t_first, t_last = frames[0]["t"], frames[-1]["t"] + 3.0
rows = sorted(marks)
row_end = {r: (marks[rows[i + 1]] if i + 1 < len(rows) else t_last) for i, r in enumerate(rows)}


def your_time_until(t):
    return sum(max(0.0, min(a["end"], t) - a["start"]) for a in acts)


def plan(scale):
    """Segments of (src_a, src_b, out_len, speed). A wait is squeezed to clamp(real/10, 3, 12) * scale seconds."""
    cuts = sorted({t_first, t_last, *[w["start"] for w in waits], *[w["end"] for w in waits], *[k["start"] for k in skips], *[k["end"] for k in skips]})
    segs = []
    for a, b in zip(cuts, cuts[1:]):
        inside = any(w["start"] <= a and b <= w["end"] for w in waits)
        real = b - a
        if any(k["start"] <= a and b <= k["end"] for k in skips):
            segs.append((a, b, 0.0, 0.0))
        elif inside and real > 8:
            out = max(2.0 * scale, min(12.0, real / 10.0) * scale)
            segs.append((a, b, out, real / out))
        else:
            segs.append((a, b, real, 1.0))
    return segs


def src_to_out(segs, t):
    total = 0.0
    for a, b, out, _ in segs:
        if t >= b:
            total += out
        elif t > a:
            total += out * (t - a) / (b - a)
            break
        else:
            break
    return total


def intro_outro_len():
    return 10 + 7 + 8 + 5 + 9  # counts, title, two console stills, github card, end card (upper bound)


scale = float(sys.argv[2]) if len(sys.argv) > 2 else 1.7  # waits shown longer when there is room under the cap
while True:
    segs = plan(scale)
    main_len = src_to_out(segs, t_last)
    if main_len + intro_outro_len() <= MAX_SECONDS or scale < 0.2:
        break
    scale *= 0.85
print(f"wait scale {scale:.2f}; main part {main_len:.0f}s")

# ---------- facts for the cards ----------
def counts():
    try:
        text = sh("uv", "run", "issue-desk", "sweep", "sandbox-quantum/switch", "--label", "hackathon", cwd=REPO).stdout
        issues = int(re.search(r"(\d+) hot issues", text).group(1))
        comments = sum(int(m.group(1)) for m in re.finditer(r"^\|\s*#\d+\s*\|[^|]*\|\s*(\d+)\s*\|", text, re.M))
        return {"issues": issues, "comments": comments}
    except Exception as err:  # the card still renders, with a plain note
        print("counts failed:", err)
        return {"issues": "?", "comments": "?"}


c = counts()
c.update(source="sandbox-quantum/switch, label “hackathon”", note="Read-only counts on the day of recording. No names, no claims judged.")
gh = dict(data.get("github", {"issue": data.get("issue"), "before": "?", "after": "?", "head": ""}))
head = gh.get("head", "").replace("**", "")
if len(head) > 300:  # cut at a word, not mid-word
    head = head[:300].rsplit(" ", 1)[0] + " …"
gh["head"] = head
agent_wait = sum(w["end"] - w["start"] for w in waits)
yours = sum(a["end"] - a["start"] for a in acts)
measured = f"Typing and approving took {fmt_time(yours)} (deciding time not counted; the typing here is scripted). The agents worked about {round(agent_wait / 60)} min (sped up here)."

panels, speeds = [], {}
for r in rows:
    step, caption, detail = STEPS[r]
    panels.append({"file": f"panel{r}", "row": r, "step": step, "caption": caption, "detail": detail, "yourTime": fmt_time(your_time_until(row_end[r]))})
seg_labels = []
for a, b, out, sp in segs:
    if out > 0 and sp > 1.5:
        label = f"×{round(sp)} speed"
        speeds[label] = f"speed{len(speeds)}"
        seg_labels.append((a, b, label))
spec = {
    "counts": c, "github": gh, "end": {"repo": "github.com/JemIIahh/issue-desk", "measured": measured},
    "panels": panels, "speeds": [{"label": k, "file": v} for k, v in speeds.items()],
    "stills": [],
}
for name, caption in (("console-rooms", "Switch Console: the hub room and the issue room it opened."), ("console-room", "The issue room: built from a template, with desk, scout and bench in it.")):
    if (OUT / f"{name}.png").exists():
        spec["stills"].append({"file": name.replace("console-", "still_"), "src": str(OUT / f"{name}.png"), "caption": caption})
(OUT / "cards.json").write_text(json.dumps(spec, indent=1))
sh("node", HERE / "cards.mjs", OUT / "cards.json")
CARDS = OUT / "cards"

# ---------- encode ----------
ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS), "-an"]


def card_clip(png, seconds, name):
    out = OUT / f"{name}.mp4"
    sh("ffmpeg", "-y", "-loop", "1", "-t", seconds, "-i", png, "-vf", f"scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x0b0b0c,format=yuv420p,fps={FPS}", *ENC, out)
    return out


def part_clip(src_a, src_b, name):
    """Encode frames in [src_a, src_b) on the canvas with the caption panels and speed labels. Returns (mp4, row windows)."""
    base = src_to_out(segs, src_a)
    lst = OUT / f"{name}.txt"
    lines, last = [], None
    for i, f in enumerate(frames):
        nxt = frames[i + 1]["t"] if i + 1 < len(frames) else t_last
        s, e = max(f["t"], src_a), min(nxt, src_b)
        if e <= s:
            continue
        d = src_to_out(segs, e) - src_to_out(segs, s)
        if d <= 0:
            continue
        lines.append(f"file '{OUT / 'frames' / f['file']}'\nduration {d:.4f}")
        last = f
    if last is None:  # nothing changed on screen: hold the frame that was showing
        f = [x for x in frames if x["t"] <= src_a][-1]
        lines.append(f"file '{OUT / 'frames' / f['file']}'\nduration {src_to_out(segs, src_b) - base:.4f}")
        last = f
    lines.append(f"file '{OUT / 'frames' / last['file']}'")
    lst.write_text("\n".join(lines) + "\n")

    overlays = []  # (png, start, end) in part time
    windows = {}
    for r in rows:
        a, b = max(marks[r], src_a), min(row_end[r], src_b)
        if b > a:
            windows[r] = (src_to_out(segs, a) - base, src_to_out(segs, b) - base)
            overlays.append((CARDS / f"panel{r}.png", *windows[r]))
    for a, b, label in seg_labels:
        a2, b2 = max(a, src_a), min(b, src_b)
        if b2 > a2:
            overlays.append((CARDS / f"{speeds[label]}.png", src_to_out(segs, a2) - base, src_to_out(segs, b2) - base))
    inputs = ["-f", "concat", "-safe", "0", "-i", lst, "-f", "lavfi", "-i", f"color=c=0x0b0b0c:s=1920x1080:r={FPS}"]
    chain = f"[0:v]fps={FPS},scale={VID_W}:{VID_H}:flags=lanczos,format=yuv420p[v];[1:v][v]overlay={VID_X}:{VID_Y}:shortest=1[b0]"
    for i, (png, a, b) in enumerate(overlays):
        inputs += ["-i", png]
        chain += f";[b{i}][{i + 2}:v]overlay=enable='between(t,{a:.3f},{b:.3f})'[b{i + 1}]"
    out = OUT / f"{name}.mp4"
    # -t: ffmpeg's concat demuxer repeats the previous hold for the last entry, which would double the final frame's time
    length = src_to_out(segs, src_b) - base
    sh("ffmpeg", "-y", *inputs, "-filter_complex", chain, "-map", f"[b{len(overlays)}]", "-t", f"{length:.3f}", *ENC, out)
    return out, windows


clips = []
clips.append(card_clip(CARDS / "counts.png", 9, "c_counts"))
clips.append(card_clip(CARDS / "title.png", 7, "c_title"))
split4, split7 = marks[4], marks[7]
p1, _ = part_clip(t_first, split4, "p1")
clips.append(p1)
for still in spec["stills"]:
    clips.append(card_clip(CARDS / f"{still['file']}.png", 4, f"c_{still['file']}"))
p2, w2 = part_clip(split4, split7, "p2")
clips.append(p2)
clips.append(card_clip(CARDS / "github.png", 6, "c_github"))
p3, _ = part_clip(split7, t_last, "p3")
clips.append(p3)
clips.append(card_clip(CARDS / "end.png", 9, "c_end"))

final = OUT / "issue-desk-demo.mp4"
(OUT / "all.txt").write_text("".join(f"file '{c}'\n" for c in clips))
sh("ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", OUT / "all.txt", "-c", "copy", final)
dur = float(sh("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", final).stdout)
print(f"{final.name}: {dur:.1f}s ({fmt_time(dur)})")

# ---------- README gif: ~15 s from rows 5-6 (scout's draft, post it, the approval card) ----------
start = max(0.0, w2.get(6, (0, 0))[0] - 4.0)
gif = OUT / "readme.gif"
palette = OUT / "palette.png"
vf = f"fps=10,scale=960:-1:flags=lanczos"
sh("ffmpeg", "-y", "-ss", f"{start:.2f}", "-t", "15", "-i", p2, "-vf", f"{vf},palettegen=stats_mode=diff", palette)
sh("ffmpeg", "-y", "-ss", f"{start:.2f}", "-t", "15", "-i", p2, "-i", palette, "-lavfi", f"{vf}[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=4", gif)
print(f"readme.gif: {gif.stat().st_size / 1e6:.1f} MB")

# Live status of the Claude labeling run, written to logs/STATUS.md every few seconds.
# Runs next to run_claude_code.py (it only reads the log and the label file, it never touches the labeling).
# Open logs/STATUS.md in VS Code (editor or Markdown preview): the file refreshes by itself while the run goes on.
#
#   python progress_status.py              refresh every 15 seconds until the run writes DONE
#   python progress_status.py --every 5    refresh every 5 seconds

import argparse
import os
import re
import time
from datetime import datetime

import pandas as pd

import label_reviews as lr

LOG_DIR = os.path.join(lr.HERE, "logs")
LOG = os.path.join(LOG_DIR, "progress.log")
STATUS = os.path.join(LOG_DIR, "STATUS.md")
PROGRESS = re.compile(r"^(\S+ \S+) \| ([\d,]+) / ([\d,]+) labeled \(([\d.]+)%\).*?\| (\d+) reviews/min \| ETA ([^ ]+)")


def last_run_lines():
    """Log lines of the latest run (from its last START line)."""
    with open(LOG, encoding="utf8") as f:
        lines = f.read().splitlines()
    start = max((i for i, line in enumerate(lines) if "| START " in line), default=0)
    return lines[start:]


def read_labels():
    for _ in range(3):  # the labeling script may be writing the file at this moment: retry
        try:
            return pd.read_csv(lr.LLM_OUT)
        except Exception:
            time.sleep(1)
    return None


def bar(pct, width=30):
    filled = int(round(pct / 100 * width))
    return "█" * filled + "░" * (width - filled)


def build_status():
    lines = last_run_lines()
    progress = [m for m in (PROGRESS.match(line) for line in lines) if m]
    problems = [line for line in lines if any(w in line for w in ("| WAIT", "| ERROR", "| SKIP"))]
    done = any("| DONE" in line for line in lines)

    if progress:
        when, n_done, n_total, pct, rate, eta = progress[-1].groups()
        n_done, n_total, pct = int(n_done.replace(",", "")), int(n_total.replace(",", "")), float(pct)
    else:
        when, n_done, n_total, pct, rate, eta = lines[0][:19] if lines else "-", 0, 0, 0.0, "-", "-"

    if done:
        state = "✅ SELESAI"
    elif problems and problems[-1] > (progress[-1].string if progress else ""):
        state = "⏸️ MENUNGGU / ADA MASALAH (lihat bagian Masalah)"
    else:
        state = "▶️ BERJALAN"

    out = [
        "# Status Labeling Ulasan Buruk (Claude)",
        "",
        f"_Diperbarui otomatis: {datetime.now():%d %b %Y %H:%M:%S}_",
        "",
        f"**Status:** {state}",
        "",
        f"`{bar(pct)}` **{pct:.1f}%**",
        "",
        "| | |",
        "|---|---|",
        f"| Sudah dilabel | **{n_done:,} / {n_total:,}** ulasan |",
        f"| Kecepatan | {rate} ulasan/menit |",
        f"| Perkiraan sisa waktu | {eta if not done else '0'} (belum termasuk jeda limit) |",
        f"| Update terakhir dari log | {when} |",
        f"| Masalah (WAIT / ERROR / SKIP) | {len(problems)} |",
        "",
    ]

    labels = read_labels()
    if labels is not None and len(labels):
        for col in ["Pain Points", "Blame Target", "Review Stage"]:
            share = labels[col].value_counts()
            out += [f"## {col} (sementara)", "", "| Label | Jumlah | Persen |", "|---|---|---|"]
            out += [f"| {k} | {v:,} | {v / len(labels) * 100:.1f}% |" for k, v in share.items()]
            out.append("")

    out += ["## Masalah", ""]
    out += [f"- `{line}`" for line in problems[-10:]] or ["- Tidak ada"]
    out += ["", "## 5 baris log terakhir", "", "```"] + lines[-5:] + ["```", ""]
    return "\n".join(out), done


def write(text):
    tmp = STATUS + ".tmp"
    with open(tmp, "w", encoding="utf8") as f:
        f.write(text)
    os.replace(tmp, STATUS)  # replace in one step so the editor never shows a half-written file


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--every", type=int, default=15, help="seconds between refreshes")
    args = parser.parse_args()
    while True:
        text, done = build_status()
        write(text)
        if done:
            break
        time.sleep(args.every)


if __name__ == "__main__":
    main()

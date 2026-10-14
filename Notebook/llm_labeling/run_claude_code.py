# Labeling Olist review comments with Claude through Claude Code (`claude -p`), using the Claude Pro
# subscription instead of the paid API. Same context, codebook, labels and output file as label_reviews.py.
# One chunk of reviews per call; results are saved after every chunk (safe to stop and restart), the
# script waits when the Pro usage limit is reached, and progress is written live to logs/progress.log.
# Bad reviews (low stars) are labeled first, so the most important rows are done even if the run stops early.
#
#   python run_claude_code.py --limit 50                       test run on the first 50 reviews
#   python run_claude_code.py --sample 400 --skip-kaggle-check pressure test on 400 random reviews (80 per star)
#   python run_claude_code.py --model claude-sonnet-5-5        label every review that has no label yet
#   python run_claude_code.py --model claude-sonnet-5-5 --scope low   only the bad reviews (1-2 stars) used in the notebook
#   Get-Content logs\progress.log -Wait                        follow the progress live (PowerShell)

import argparse
import json
import os
import shutil
import subprocess
import time
from datetime import datetime, timedelta

import pandas as pd

import label_reviews as lr

LOG_DIR = os.path.join(lr.HERE, "logs")
LOG = os.path.join(LOG_DIR, "progress.log")
SYSTEM_FILE = os.path.join(LOG_DIR, "system_prompt.txt")
LIMIT_WAIT_MIN = 15  # minutes to wait before retrying after the Pro usage limit is hit
LIMIT_WORDS = ("limit", "quota", "rate", "overloaded", "529", "429")


def claude_exe():
    shim = shutil.which("claude")
    if shim is None:
        raise SystemExit("Claude Code (claude) is not installed or not on PATH")
    native = os.path.join(os.path.dirname(shim), "node_modules", "@anthropic-ai", "claude-code", "bin", "claude.exe")
    return native if os.path.exists(native) else shim  # call the exe directly: .cmd shims mangle JSON quotes


def log(msg):
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S} | {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf8") as f:
        f.write(line + "\n")


def call_claude(texts, model):
    """One `claude -p` call for a chunk of reviews. Returns (results or None, error message, usage)."""
    items = [{"id": f"r{i}", "text": t} for i, t in enumerate(texts, start=1)]
    cmd = [claude_exe(), "-p", "--model", model, "--safe-mode", "--output-format", "json", "--tools", "",
           "--no-session-persistence", "--effort", "low", "--system-prompt-file", SYSTEM_FILE,
           "--json-schema", json.dumps(lr.SCHEMA)]
    prompt = "Label these reviews:\n" + json.dumps(items, ensure_ascii=False)
    proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8",
                          cwd=lr.HERE, timeout=600)
    try:
        out = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None, (proc.stdout + proc.stderr).strip()[:300] or f"exit code {proc.returncode}", {}
    if out.get("is_error") or not out.get("structured_output"):
        return None, str(out.get("result") or out.get("api_error_status") or out.get("subtype"))[:300], out.get("usage", {})
    return out["structured_output"]["results"], "", out.get("usage", {})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=lr.DEFAULT_MODEL)
    parser.add_argument("--chunk", type=int, default=lr.CHUNK)
    parser.add_argument("--limit", type=int, help="label at most this many reviews (test run)")
    parser.add_argument("--sample", type=int, help="test on a random sample of N reviews, same count per star score")
    parser.add_argument("--skip-kaggle-check", action="store_true", help="timing tests only, not for the real run")
    parser.add_argument("--scope", choices=["all", "low"], default="all",
                        help="low = only the valid bad reviews (1-2 stars) of the notebook's order-level table")
    args = parser.parse_args()

    os.makedirs(LOG_DIR, exist_ok=True)
    with open(SYSTEM_FILE, "w", encoding="utf8") as f:
        f.write(_prompt_without_kaggle() if args.skip_kaggle_check else lr.system_prompt())
    # timing tests write to their own file so they never end up in the real results
    out_path = os.path.join(LOG_DIR, "test_labels.csv") if args.skip_kaggle_check else lr.LLM_OUT

    reviews = lr.load_reviews()
    if args.scope == "low":
        reviews = reviews[reviews["review_id"].isin(lr.low_review_ids())].reset_index(drop=True)
    if args.sample:  # representative test: random reviews of every length, equal number per star score
        reviews = lr.stratified_sample(reviews, args.sample, seed=123)
    reviews = reviews.sort_values("review_score", kind="stable").reset_index(drop=True)
    done = set(pd.read_csv(out_path)["review_id"]) if os.path.exists(out_path) else set()
    todo = reviews[~reviews["review_id"].isin(done)]
    if args.limit:
        todo = todo.head(args.limit)
    total, start_done = len(reviews), len(done)
    log(f"START model={args.model} chunk={args.chunk} | already labeled {start_done}/{total} | this run: {len(todo)} reviews")

    t0, labeled_now = time.time(), 0
    for start in range(0, len(todo), args.chunk):
        chunk = todo.iloc[start:start + args.chunk]
        for attempt in range(1, 4):
            t = time.time()
            results, error, usage = call_claude(chunk["text"].tolist(), args.model)
            if results is not None:
                break
            if any(w in error.lower() for w in LIMIT_WORDS):  # Pro usage limit / overload: wait, then try again
                log(f"WAIT usage limit or overload: {error} | retry at "
                    f"{datetime.now() + timedelta(minutes=LIMIT_WAIT_MIN):%H:%M}")
                time.sleep(LIMIT_WAIT_MIN * 60)
                continue
            log(f"ERROR chunk at {start} attempt {attempt}: {error}")
        else:
            log(f"SKIP chunk at {start} after 3 failed attempts (left unlabeled, picked up by the next run)")
            continue
        if results is None:
            continue
        rows = lr.to_rows(results, chunk["review_id"].tolist())
        lr.save_labels(rows, out_path)
        labeled_now += len(rows)
        done_total = start_done + labeled_now
        rate = labeled_now / max(time.time() - t0, 1) * 60
        eta = timedelta(minutes=(len(todo) - start - len(chunk)) / max(rate, 1e-9))
        log(f"{done_total:,} / {total:,} labeled ({done_total / total:.1%}) | chunk {len(rows)}/{len(chunk)} in "
            f"{time.time() - t:.0f}s | {rate:.0f} reviews/min | ETA {str(eta).split('.')[0]} (without limit waits) | "
            f"tokens in {usage.get('input_tokens', 0) + usage.get('cache_read_input_tokens', 0) + usage.get('cache_creation_input_tokens', 0)} "
            f"out {usage.get('output_tokens', 0)}")
    log(f"DONE this run: {labeled_now} reviews labeled | total {start_done + labeled_now:,} / {total:,}")


def _prompt_without_kaggle():
    """System prompt without the Kaggle description - only for --skip-kaggle-check timing tests."""
    def read(name):
        with open(os.path.join(lr.HERE, name), encoding="utf8") as f:
            return f.read().strip()
    return ("You label customer review comments for a data analysis project about the Olist marketplace.\n\n"
            + read("problem_statement.md") + "\n\n" + read("codebook.md") + "\n\n"
            "Return one entry per review id in the same order, using only the allowed values.")


if __name__ == "__main__":
    main()

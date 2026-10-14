# Labeling Olist review comments with Claude (Anthropic API, Message Batches).
# Every review gets exactly one value for 6 labels defined in codebook.md. Claude receives one system
# prompt (cached) = problem_statement.md + kaggle_description.md + codebook.md, and 25 reviews per request.
#
# Steps:
#   python label_reviews.py pilot --n 200         small synchronous run: check the labels + measure the real cost
#   python label_reviews.py submit                send all reviews as one batch (50% cheaper, done within 24h)
#   python label_reviews.py collect               download batch results -> Dataset/review_labels_llm.csv
#   python label_reviews.py submit --missing      resend only reviews that have no label yet
#   python label_reviews.py merge                 write the labels into Dataset/review_sentiment.csv
#   python label_reviews.py qa-export --n 150     QA sheet for a manual check (Google Sheets + GOOGLETRANSLATE)
#   python label_reviews.py qa-export --n 150 --source llm --labels "Pain Points" "Blame Target" "Review Stage"
#                                                 QA sheet of the Claude labels, only the labels used in the notebook
#   python label_reviews.py qa-score FILE.csv     accuracy per label from the filled QA sheet
# Needs: pip install anthropic pandas ; ANTHROPIC_API_KEY set in the environment.

import argparse
import functools
import json
import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(os.path.dirname(HERE)), "Dataset")
REVIEWS = os.path.join(DATA, "review_sentiment.csv")
LLM_OUT = os.path.join(DATA, "review_labels_llm.csv")
RULE_BASED = os.path.join(DATA, "review_labels_rule_based.csv")
ORDER_LEVEL = os.path.join(DATA, "olist_order_level.csv")
STATE = os.path.join(HERE, "batch_state.json")
PILOT_OUT = os.path.join(HERE, "pilot_results.csv")

DEFAULT_MODEL = "claude-opus-5-5"
CHUNK = 25  # reviews per request: the system prompt and the request overhead are shared by 25 reviews
DROP_COLUMNS = ["Buying Motivations", "Emotional Drivers"]  # not related to the main business question

# USD per 1M tokens: input, output, cache read, cache write (5 min). Batch requests cost 50% of this.
PRICES = {
    "claude-opus-5-5": (4.00, 20.00, 0.20, 5.00),
    "claude-sonnet-5-5": (2.00, 10.00, 0.20, 2.50),
    "claude-haiku-4-5": (1.00, 5.00, 0.10, 1.25),
}

# JSON key -> (column name in review_sentiment.csv, {code Claude returns: value written to the file})
LABELS = {
    "user_sentiment": ("User Sentiment", {"positive": "Positive", "negative": "Negative", "neutral": "Neutral"}),
    "pain_points": ("Pain Points", {
        "delivery_time": "Delivery Time", "wrong_missing_item": "Wrong / Missing Item",
        "product_quality": "Product Quality", "packaging": "Packaging", "delivery_process": "Delivery Process",
        "cost_billing": "Cost & Billing", "seller_service": "Seller Service", "others": "Others",
        "not_relevant": "Not Relevant"}),
    "review_stage": ("Review Stage", {
        "not_received_yet": "Not Received Yet", "partially_received": "Partially Received", "received": "Received",
        "received_not_used": "Received, Not Used Yet", "used_tested": "Used / Tested", "not_mentioned": "Not Mentioned"}),
    "blame_target": ("Blame Target", {
        "seller": "Seller", "marketplace": "Marketplace / Platform", "carrier": "Logistics / Carrier",
        "customer": "Customer", "not_mentioned": "Not Mentioned", "not_relevant": "Not Relevant"}),
    "customer_request": ("Customer Request", {
        "refund": "Refund", "exchange_return": "Exchange / Return", "send_missing_item": "Send Missing / Correct Item",
        "cancellation": "Cancellation", "delivery_update": "Delivery Update", "contact_response": "Contact / Response",
        "others": "Others", "no_request": "No Request"}),
    "repurchase_intent": ("Repurchase Intent", {
        "will_buy_again": "Will Buy Again / Recommend", "will_not_buy_again": "Will Not Buy Again",
        "not_mentioned": "Not Mentioned"}),
}
LABEL_COLUMNS = [col for col, _ in LABELS.values()]

SCHEMA = {
    "type": "object",
    "properties": {"results": {"type": "array", "items": {
        "type": "object",
        "properties": {"id": {"type": "string"},
                       **{key: {"type": "string", "enum": list(values)} for key, (_, values) in LABELS.items()}},
        "required": ["id", *LABELS],
        "additionalProperties": False,
    }}},
    "required": ["results"],
    "additionalProperties": False,
}


@functools.lru_cache
def system_prompt():
    def read(name):
        with open(os.path.join(HERE, name), encoding="utf8") as f:
            return f.read().strip()
    kaggle = read("kaggle_description.md")
    if "PASTE_KAGGLE_DESCRIPTION_HERE" in kaggle:
        raise SystemExit("kaggle_description.md still has the placeholder - paste the Kaggle description first.")
    return ("You label customer review comments for a data analysis project about the Olist marketplace.\n\n"
            + read("problem_statement.md") + "\n\n" + kaggle + "\n\n" + read("codebook.md") + "\n\n"
            "Return one entry per review id in the same order, using only the allowed values.")


def build_params(texts, model):
    items = [{"id": f"r{i}", "text": t} for i, t in enumerate(texts, start=1)]
    output_config = {"format": {"type": "json_schema", "schema": SCHEMA}}
    if not model.startswith("claude-haiku"):  # Haiku 4.5 has no effort setting
        output_config["effort"] = "low"  # simple classification: low effort keeps thinking (and cost) small
    return {
        "model": model,
        "max_tokens": 8000,
        "system": [{"type": "text", "text": system_prompt(), "cache_control": {"type": "ephemeral"}}],
        "messages": [{"role": "user", "content": "Label these reviews:\n" + json.dumps(items, ensure_ascii=False)}],
        "output_config": output_config,
    }


def parse_message(msg, review_ids):
    """Rows of labels for the reviews Claude answered; reviews it skipped are simply absent (resent later)."""
    if msg.stop_reason != "end_turn":  # refusal or max_tokens: resend this chunk later
        return []
    text = next(b.text for b in msg.content if b.type == "text")
    return to_rows(json.loads(text)["results"], review_ids)


def to_rows(results, review_ids):
    """Map Claude's answer (ids r1..rN in chunk order) back to review_id + readable label values."""
    by_id = {r["id"]: r for r in results}
    rows = []
    for i, review_id in enumerate(review_ids, start=1):
        r = by_id.get(f"r{i}")
        if r is not None:
            rows.append({"review_id": review_id, **{col: values[r[key]] for key, (col, values) in LABELS.items()}})
    return rows


def cost(usage, model, batch):
    p_in, p_out, p_read, p_write = PRICES[model]
    usd = (usage.input_tokens * p_in + usage.output_tokens * p_out
           + (usage.cache_read_input_tokens or 0) * p_read + (usage.cache_creation_input_tokens or 0) * p_write) / 1e6
    return usd * (0.5 if batch else 1.0)


def load_reviews():
    df = pd.read_csv(REVIEWS)
    return df.drop_duplicates("review_id")[["review_id", "review_score", "text"]].reset_index(drop=True)


def low_review_ids():
    """review_id of the valid bad reviews (1-2 stars) in the notebook's order-level table (same scope as the analysis)."""
    order = pd.read_csv(ORDER_LEVEL, usecols=["review_id", "is_valid_review", "is_low_review"])
    valid_low = order["is_valid_review"].astype(bool) & (order["is_low_review"].astype(str) == "True")
    return set(order.loc[valid_low, "review_id"])


def stratified_sample(df, n, seed):
    """Same number of reviews per star score, so bad reviews are not drowned out by the many 5-star ones."""
    per_score = n // df["review_score"].nunique()
    return df.groupby("review_score").sample(n=per_score, random_state=seed).reset_index(drop=True)


def save_labels(rows, path=LLM_OUT):
    new = pd.DataFrame(rows)
    if os.path.exists(path):
        new = pd.concat([pd.read_csv(path), new]).drop_duplicates("review_id", keep="last")
    new.to_csv(path, index=False)
    return new


def client():
    import anthropic
    return anthropic.Anthropic(max_retries=5)


def cmd_pilot(args):
    sample = stratified_sample(load_reviews(), args.n, seed=42)
    api, rows, total = client(), [], 0.0
    for start in range(0, len(sample), CHUNK):
        chunk = sample.iloc[start:start + CHUNK]
        msg = api.messages.create(**build_params(chunk["text"].tolist(), args.model))
        rows += parse_message(msg, chunk["review_id"].tolist())
        total += cost(msg.usage, args.model, batch=False)
        print(f"  {start + len(chunk)}/{len(sample)} reviews, stop={msg.stop_reason}, usage={msg.usage}")
    out = sample.merge(pd.DataFrame(rows), on="review_id", how="left")
    out.to_csv(PILOT_OUT, index=False, encoding="utf-8-sig")
    n_all = len(load_reviews())
    print(f"\nlabeled {len(rows)}/{len(sample)} reviews -> {PILOT_OUT}")
    print(f"pilot cost: ${total:.3f}  |  projected full run as batch ({n_all} reviews): "
          f"${total * 0.5 * n_all / len(sample):.2f}")


def cmd_submit(args):
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request

    df = load_reviews()
    if args.missing and os.path.exists(LLM_OUT):
        df = df[~df["review_id"].isin(pd.read_csv(LLM_OUT)["review_id"])].reset_index(drop=True)
    state = json.load(open(STATE)) if os.path.exists(STATE) else {"batches": []}
    n_prev = sum(len(b["chunks"]) for b in state["batches"])
    chunks, requests = {}, []
    for start in range(0, len(df), CHUNK):
        chunk = df.iloc[start:start + CHUNK]
        custom_id = f"c{n_prev + len(chunks):05d}"
        chunks[custom_id] = chunk["review_id"].tolist()
        requests.append(Request(custom_id=custom_id, params=MessageCreateParamsNonStreaming(
            **build_params(chunk["text"].tolist(), args.model))))
    batch = client().messages.batches.create(requests=requests)
    state["batches"].append({"batch_id": batch.id, "model": args.model, "chunks": chunks})
    with open(STATE, "w") as f:
        json.dump(state, f)
    print(f"submitted batch {batch.id}: {len(requests)} requests, {len(df)} reviews, model {args.model}")


def cmd_collect(args):
    api = client()
    state = json.load(open(STATE))
    for b in state["batches"]:
        if b.get("collected"):
            continue
        batch = api.messages.batches.retrieve(b["batch_id"])
        if batch.processing_status != "ended":
            print(f"{b['batch_id']}: {batch.processing_status} {batch.request_counts} - run collect again later")
            continue
        rows, usd, failed = [], 0.0, 0
        for result in api.messages.batches.results(b["batch_id"]):  # results come in any order: key by custom_id
            if result.result.type == "succeeded":
                msg = result.result.message
                rows += parse_message(msg, b["chunks"][result.custom_id])
                usd += cost(msg.usage, b["model"], batch=True)
            else:
                failed += 1
        labeled = save_labels(rows) if rows else pd.read_csv(LLM_OUT)
        b["collected"] = True
        print(f"{b['batch_id']}: {len(rows)} reviews labeled, {failed} failed requests, cost ${usd:.2f}")
        print(f"total labeled so far: {len(labeled)} / {len(load_reviews())}")
    with open(STATE, "w") as f:
        json.dump(state, f)


def cmd_merge(args):
    llm = pd.read_csv(LLM_OUT).set_index("review_id")
    full = pd.read_csv(REVIEWS)
    if not os.path.exists(RULE_BASED):
        print("WARNING: no rule-based baseline file; run theme_analysis.py first to keep it for comparison")
    missing = (~full["review_id"].isin(llm.index)).sum()
    for col in LABEL_COLUMNS:
        full[col] = full["review_id"].map(llm[col])
    full = full.drop(columns=[c for c in DROP_COLUMNS if c in full.columns])
    full.to_csv(REVIEWS, index=False)
    print(f"wrote {len(LABEL_COLUMNS)} label columns into {REVIEWS}; rows without a Claude label: {missing}")

    if os.path.exists(RULE_BASED):  # how often Claude agrees with the earlier keyword rules
        rule = pd.read_csv(RULE_BASED).set_index("review_id")
        both = llm.index.intersection(rule.index)
        for col in LABEL_COLUMNS:
            if col in rule.columns:
                print(f"  agreement with keyword rules - {col:18s}: {(llm.loc[both, col] == rule.loc[both, col]).mean():.1%}")


def cmd_qa_export(args):
    if args.source == "llm":  # check Claude's labels (text from the review file, labels from the Claude output)
        full = load_reviews().merge(pd.read_csv(LLM_OUT), on="review_id")
    else:
        full = pd.read_csv(REVIEWS).drop_duplicates("review_id")
    columns = args.labels or LABEL_COLUMNS
    sample = stratified_sample(full, args.n, seed=7)
    out = pd.DataFrame({"review_id": sample["review_id"], "review_score": sample["review_score"], "text": sample["text"]})
    # text is column C; Google Sheets evaluates the formula when the CSV is imported
    out["translation (id)"] = [f'=GOOGLETRANSLATE(C{i + 2},"pt","id")' for i in range(len(out))]
    for col in columns:
        out[col] = sample[col].values
        out[f"{col} OK? (Y/N)"] = ""
        out[f"{col} correct label"] = ""
    path = os.path.join(HERE, "qa_sample.csv")
    out.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"QA sheet with {len(out)} reviews -> {path}")


def cmd_qa_score(args):
    qa = pd.read_csv(args.file)
    rows = []
    for col in [c for c in LABEL_COLUMNS if f"{c} OK? (Y/N)" in qa.columns]:
        # Y/N typed by hand, or TRUE/FALSE from a Google Sheets checkbox
        mark = qa[f"{col} OK? (Y/N)"].astype(str).str.strip().str.upper().replace({"TRUE": "Y", "FALSE": "N"})
        checked = mark.isin(["Y", "N"])
        rows.append({"label": col, "checked": checked.sum(), "correct": (mark == "Y").sum(),
                     "accuracy": (mark == "Y").sum() / max(checked.sum(), 1)})
    print(pd.DataFrame(rows).to_string(index=False, formatters={"accuracy": "{:.1%}".format}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pilot"); p.add_argument("--n", type=int, default=200); p.add_argument("--model", default=DEFAULT_MODEL)
    p = sub.add_parser("submit"); p.add_argument("--model", default=DEFAULT_MODEL); p.add_argument("--missing", action="store_true")
    sub.add_parser("collect")
    sub.add_parser("merge")
    p = sub.add_parser("qa-export"); p.add_argument("--n", type=int, default=150)
    p.add_argument("--source", choices=["file", "llm"], default="file", help="llm = check the Claude labels")
    p.add_argument("--labels", nargs="+", help='only these label columns, e.g. "Pain Points" "Blame Target"')
    p = sub.add_parser("qa-score"); p.add_argument("file")
    args = parser.parse_args()
    {"pilot": cmd_pilot, "submit": cmd_submit, "collect": cmd_collect, "merge": cmd_merge,
     "qa-export": cmd_qa_export, "qa-score": cmd_qa_score}[args.cmd](args)

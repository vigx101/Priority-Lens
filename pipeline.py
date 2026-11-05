"""pipeline.py - Load feedback from Excel/CSV -> clean -> label (category + sentiment) -> RICE."""
import os
import re
import sys

import pandas as pd

from generator import SAMPLE_EXCEL, generate

# ------------------------------------------------------------------
# STEP 0: LOAD FEEDBACK FROM AN EXCEL / CSV FILE
# ------------------------------------------------------------------
TEXT_COLUMN_NAMES = ["raw_feedback_text", "feedback", "feedback_text", "text",
                     "comment", "comments", "review", "message"]


def load_feedback_file(file):
    """Read an Excel (.xlsx) or CSV file (a path or an uploaded file)."""
    if hasattr(file, "seek"):
        file.seek(0)
    name = getattr(file, "name", str(file)).lower()
    return pd.read_csv(file) if name.endswith(".csv") else pd.read_excel(file)


def prepare_columns(df):
    """Make column names consistent and add any optional columns that are missing."""
    df = df.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    text_column = next((c for c in TEXT_COLUMN_NAMES if c in df.columns), None)
    if text_column is None:
        raise ValueError("Could not find the feedback text column. Name it 'raw_feedback_text' "
                         "(or feedback, text, comment, review, message).")
    df = df.rename(columns={text_column: "raw_feedback_text"})
    if "source" not in df.columns:
        df["source"] = "Unknown"
    if "feedback_id" not in df.columns:
        df["feedback_id"] = [f"FB-{i + 1:04d}" for i in range(len(df))]
    return df


# ------------------------------------------------------------------
# STEP 1: CLEAN THE TEXT
# ------------------------------------------------------------------
TYPO_FIXES = {"plz": "please", "sloww": "slow"}


def clean_text(text):
    if pd.isna(text):                                # missing value
        return ""
    text = text.lower()                              # lowercase
    text = re.sub(r"[^a-z0-9\s.,!?']", " ", text)    # remove emojis / special characters
    for typo, fix in TYPO_FIXES.items():             # fix typos
        text = text.replace(typo, fix)
    return " ".join(text.split())                    # remove extra spaces


# ------------------------------------------------------------------
# STEP 2: LABEL THE FEEDBACK (simulated LLM using keywords)
# ------------------------------------------------------------------
PERFORMANCE_WORDS = ["slow", "lag", "load", "battery"]
BUG_WORDS = ["crash", "error", "fail", "broken", "never", "stuck", "nothing"]
FEATURE_WORDS = ["please add", "would love", "wish", "need a way"]
NEGATIVE_WORDS = PERFORMANCE_WORDS + BUG_WORDS + ["confusing", "cluttered", "terrible",
                                                  "hurt", "freez", "unclear", "buried", "twice", "hard"]
POSITIVE_WORDS = ["great", "thanks", "awesome"]


def has_any(text, words):
    return any(word in text for word in words)


def categorize(text):
    """Returns (category, sentiment) for one piece of feedback."""
    if has_any(text, PERFORMANCE_WORDS):
        category = "Performance Issue"
    elif has_any(text, BUG_WORDS):
        category = "Bug"
    elif has_any(text, FEATURE_WORDS):
        category = "Feature Request"
    else:
        category = "UX Friction"

    score = sum(w in text for w in POSITIVE_WORDS) - sum(w in text for w in NEGATIVE_WORDS)
    if score > 0:
        sentiment = "Positive"
    elif score < 0:
        sentiment = "Negative"
    else:
        sentiment = "Neutral"
    return category, sentiment


# ------------------------------------------------------------------
# STEP 3: RICE PRIORITIZATION
# ------------------------------------------------------------------
# Assumptions you can edit:
REACH = {"App Store": 4000, "Survey": 1500, "Support Ticket": 600}        # users affected per mention (other sources: 500)
CONFIDENCE = {"Support Ticket": 0.9, "Survey": 0.8, "App Store": 0.6}     # how much we trust the source (other: 0.5)
IMPACT = {"Bug": 3.0, "Performance Issue": 2.5, "UX Friction": 1.5, "Feature Request": 2.0}
EFFORT = {"Bug": 2, "Performance Issue": 5, "UX Friction": 3, "Feature Request": 5}  # person-weeks

THEMES = {
    "Notifications": ["notification"],
    "Login & Auth": ["log in", "login", "password", "account"],
    "Checkout & Payments": ["checkout", "payment", "apple pay"],
    "Search": ["search"],
    "Export & Reports": ["export", "report", "pdf"],
    "Dark Mode": ["dark mode"],
    "Onboarding & Navigation": ["onboarding", "settings", "menu"],
    "App Speed": ["dashboard", "scroll", "battery", "lag", "load"],
}


def find_theme(text):
    for theme, words in THEMES.items():
        if has_any(text, words):
            return theme
    return "General"


def rice_score(reach, impact, confidence, effort):
    return reach * impact * confidence / effort


def build_backlog(df):
    """Group feedback by theme + category, then rank by RICE score."""
    backlog = df.groupby(["theme", "category"]).agg(
        mentions=("feedback_id", "count"),
        reach=("reach", "sum"),
        impact=("impact", "mean"),
        confidence=("confidence", "mean"),
        effort=("effort", "mean"),
    ).reset_index()
    backlog["rice_score"] = rice_score(backlog["reach"], backlog["impact"],
                                       backlog["confidence"], backlog["effort"])
    backlog["backlog_item"] = backlog["theme"] + " - " + backlog["category"]
    backlog = backlog.sort_values("rice_score", ascending=False).reset_index(drop=True)
    backlog.insert(0, "rank", backlog.index + 1)
    columns = ["rank", "backlog_item", "category", "mentions", "reach",
               "impact", "confidence", "effort", "rice_score"]
    return backlog[columns].round(2)


# ------------------------------------------------------------------
# RUN ALL STEPS
# ------------------------------------------------------------------
def process_feedback(raw_df):
    """Takes the raw feedback table and returns it cleaned, labelled and RICE-ready."""
    df = prepare_columns(raw_df)
    df["source"] = df["source"].fillna("Unknown")

    # Step 1: clean (and drop rows with no text)
    df["clean_text"] = df["raw_feedback_text"].apply(clean_text)
    df = df[df["clean_text"] != ""].reset_index(drop=True)

    # Step 2: label
    df[["category", "sentiment"]] = [categorize(t) for t in df["clean_text"]]

    # Step 3: RICE inputs for every item
    df["theme"] = df["clean_text"].apply(find_theme)
    df["reach"] = df["source"].map(REACH).fillna(500)
    df["impact"] = df["category"].map(IMPACT) + (df["sentiment"] == "Negative") * 0.5
    df["confidence"] = df["source"].map(CONFIDENCE).fillna(0.5)
    df["effort"] = df["category"].map(EFFORT)
    return df


if __name__ == "__main__":
    # Usage:  python pipeline.py                 (uses the sample Excel file)
    #         python pipeline.py my_feedback.xlsx
    path = sys.argv[1] if len(sys.argv) > 1 else SAMPLE_EXCEL
    if path == SAMPLE_EXCEL and not os.path.exists(path):
        generate()
    data = process_feedback(load_feedback_file(path))
    print(f"Processed {len(data)} feedback items from {path}\n")
    print(build_backlog(data).head(8).to_string(index=False))

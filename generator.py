"""generator.py - Creates a SAMPLE Excel file with 100 messy feedback rows (use it as a template)."""
import os
import random
from datetime import date, timedelta

import pandas as pd

SAMPLE_EXCEL = "data/sample_feedback.xlsx"

SAMPLE_FEEDBACK = [
    "app crashes every time i log in with google",
    "payment fails with error 500 at checkout, charged twice!",
    "push notifications never arrive on my phone",
    "export to pdf button does nothing, totally broken",
    "password reset email never comes, stuck out of my account",
    "checkout has too many steps, so confusing",
    "cant find the settings page, menu is cluttered",
    "onboarding is unclear, no idea where to start",
    "search filters are hard to use and confusing",
    "notification settings are buried too deep in the app",
    "please add dark mode, my eyes hurt at night",
    "would love an option to export reports to excel",
    "wish you had apple pay support at checkout",
    "need a way to schedule notifications",
    "great app, thanks! please add saved searches",
    "dashboard is super slow to load, takes forever",
    "app lags badly when scrolling long lists",
    "search is slow, takes 20 seconds",
    "checkout page freezes and loads slowly on wifi",
    "battery drain is terrible since the last update",
    "awesome app, thanks! would love apple pay support",
    "thanks, great support team, search works well now",
]
SOURCES = ["App Store", "Support Ticket", "Survey"]
EMOJIS = ["😡", "😤", "👎", "🙏", "🔥", "😭"]


def make_messy(text):
    """Add typos, emojis, CAPS and extra spaces to look like real feedback."""
    if random.random() < 0.3:
        text = text.replace("slow", "sloww")
    if random.random() < 0.3:
        text = text.replace("please", "plz")
    if random.random() < 0.1:
        text = text.upper()
    if random.random() < 0.4:
        text = text + " " + random.choice(EMOJIS)
    return "   " + text + "   "


def generate(n=100):
    random.seed(7)  # same data every time
    rows = []
    for i in range(1, n + 1):
        rows.append({
            "feedback_id": f"FB-{i:04d}",
            "customer_id": f"CUST-{random.randint(1000, 1400)}",
            "raw_feedback_text": make_messy(random.choice(SAMPLE_FEEDBACK)),
            "source": random.choice(SOURCES),
            "date": date(2026, 7, 1) + timedelta(days=random.randint(0, 90)),
        })
    df = pd.DataFrame(rows)
    df.loc[[5, 40], "raw_feedback_text"] = None    # missing values
    df.loc[[20, 70], "raw_feedback_text"] = "   "   # blank values
    os.makedirs("data", exist_ok=True)
    df.to_excel(SAMPLE_EXCEL, index=False)
    return df


if __name__ == "__main__":
    generate()
    print("Created", SAMPLE_EXCEL)

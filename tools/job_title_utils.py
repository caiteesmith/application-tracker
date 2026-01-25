# tools/job_title_utils.py
from __future__ import annotations

import re

# Canonical buckets we care about
SOFTWARE = "Software Engineer/Developer"
WEB = "Web Developer"
FRONTEND = "Front End Developer"
BACKEND = "Back End Developer"
FULLSTACK = "Full Stack Developer"
DATA = "Data/Analytics"
OTHER = "Other"


def normalize_job_title(raw: str) -> str:
    """
    Clean up a job title and optionally bucket it into broad categories.

    - Software roles get grouped (Software Engineer / Developer, Front End Developer, etc.)
    - Non-software roles keep a cleaned, de-fluffed version of the original title.
    """
    if not raw:
        return "Other"

    original = raw.strip()
    t = original.lower()

    # Strip common fluff words / levels / prefixes
    fluff_words = [
        "senior", "sr.", "sr",
        "junior", "jr.", "jr",
        "lead", "principal", "staff",
        "early career", "entry level", "mid-level", "mid level",
        "ii", "iii", "iv",
        "level",
    ]
    for w in fluff_words:
        t = t.replace(w, " ")

    # Remove parenthetical tech stacks or notes: "(.NET/Azure)", "(Remote)", etc.
    t = re.sub(r"[\(\[].*?[\)\]]", " ", t)

    # Normalize whitespace / punctuation
    t = re.sub(r"[^a-z\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()

    # --- Software-y buckets ---
    if "full stack" in t and ("engineer" in t or "developer" in t):
        return "Full Stack Developer"
    if "front end" in t or "frontend" in t or "ui engineer" in t:
        return "Front End Developer"
    if "back end" in t or "backend" in t:
        return "Back End Developer"
    if "web" in t and "developer" in t:
        return "Web Developer"
    if "software" in t and ("engineer" in t or "developer" in t):
        return "Software Engineer/Developer"
    if ("engineer" in t or "developer" in t) and ("data" not in t):
        return "Software Engineer/Developer"

    # --- Data-ish roles ---
    if "data" in t and ("engineer" in t or "scientist" in t or "analyst" in t):
        return "Data / Analytics"

    # --- Non-software ---
    if t:
        # Capitalize nicely, e.g. "marketing manager" -> "Marketing Manager"
        return t.title()

    return original or "Other"
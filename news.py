import feedparser
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import pytz
import html
import os
import re
import time

# -----------------------------
# CONFIG
# -----------------------------

NEWS_FEEDS = [
    "https://www.searchenginejournal.com/feed/",
    "https://searchengineland.com/feed/",
    "https://techcrunch.com/feed/"
]

EMAIL_SENDER = "udaykumar.venkatesh@joytechnologies.com"

EMAIL_RECEIVERS = [
    "udaykumar.venkatesh@joytechnologies.com",
    "gokulapriya.ravi@joytechnologies.com",
    "selvadharshini.subramanian@joytechnologies.com",
    "saranya.hari@joytechnologies.com",
    "sowmiya.nagappan@joytechnologies.com",
    "nivethitha.subramani@joytechnologies.com"
]

EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

MODEL = "gemini-2.5-flash"

MAX_API_CALLS = 3
api_calls_made = 0

BRIEF_FIELDS = [
    ("update", "Update"),
    ("what_changed", "What changed"),
    ("why_it_matters", "Why it matters"),
]

BRIEF_ALIASES = {
    "update": ["update", "headline", "summary"],
    "what_changed": ["what changed", "what is the update", "change", "changes"],
    "why_it_matters": ["why it matters", "impact", "why this matters"],
}

PROMO_WORDS = ["services", "agency", "press release", "sponsored", "advertising"]

def is_promotional(title):
    return any(word in title.lower() for word in PROMO_WORDS)

def normalize_whitespace(text):
    return re.sub(r"\s+", " ", text).strip()

def shorten_sentence(text, max_chars=180):
    text = normalize_whitespace(text)
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    trimmed = text[:max_chars].rsplit(" ", 1)[0].rstrip(",;:-")
    return f"{trimmed}..."

def ensure_sentence(text, fallback):
    cleaned = shorten_sentence(text or fallback)
    if not cleaned:
        cleaned = fallback
    if cleaned[-1] not in ".!?":
        cleaned += "."
    return cleaned

def parse_brief(raw_brief):
    sections = {key: "" for key, _ in BRIEF_FIELDS}
    current_key = None
    extras = []

    for raw_line in raw_brief.splitlines():
        line = normalize_whitespace(re.sub(r"^[\-\*\u2022\u2192\u2013\u2014]+\s*", "", raw_line).strip())
        if not line:
            continue

        matched = False
        lower_line = line.lower()

        for key, aliases in BRIEF_ALIASES.items():
            for alias in aliases:
                prefix = f"{alias}:"
                if lower_line.startswith(prefix):
                    sections[key] = normalize_whitespace(line[len(prefix):].strip())
                    current_key = key
                    matched = True
                    break
            if matched:
                break

        if matched:
            continue

        if current_key and not sections[current_key]:
            sections[current_key] = line
        else:
            extras.append(line)

    for key, _ in BRIEF_FIELDS:
        if not sections[key] and extras:
            sections[key] = extras.pop(0)

    return {
        "update": ensure_sentence(sections["update"], "A notable industry change was reported."),
        "what_changed": ensure_sentence(sections["what_changed"], sections["update"]),
        "why_it_matters": ensure_sentence(sections["why_it_matters"], "This could affect SEO priorities."),
    }

def get_article_text(url):
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        return " ".join(p.get_text() for p in soup.find_all("p"))
    except:
        return ""

def get_articles(limit=2):
    selected = []
    for feed_url in NEWS_FEEDS:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            if is_promotional(entry.title):
                continue
            text = get_article_text(entry.link)
            if len(text) > 500:
                selected.append(text[:1500])
            if len(selected) >= limit:
                return selected
    return selected

print("Fetching articles...")
articles = get_articles()

if not articles:
    print("No articles found.")
    raise SystemExit

# ✅ TIME FIX HERE
print("UTC Time:", datetime.utcnow())
ist = pytz.timezone("Asia/Kolkata")
print("IST Time:", datetime.now(ist))

date = datetime.now(ist).strftime("%A, %B %d, %Y - %I:%M %p IST")

html_content = f"""
<h2>Morning SEO Intelligence Brief</h2>
<p>{date}</p>
"""

print("Sending email...")

msg = MIMEText(html_content, "html")
msg["Subject"] = "Morning SEO Intelligence Brief"
msg["From"] = EMAIL_SENDER
msg["To"] = ", ".join(EMAIL_RECEIVERS)

server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
server.login(EMAIL_SENDER, EMAIL_PASSWORD)
server.sendmail(EMAIL_SENDER, EMAIL_RECEIVERS, msg.as_string())
server.quit()

print("Email Sent Successfully")

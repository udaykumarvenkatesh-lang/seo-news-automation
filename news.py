import feedparser
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
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

# RATE LIMIT CONTROL
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

# -----------------------------
# FILTER
# -----------------------------

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

    fallback_update = ensure_sentence(
        sections["update"],
        "A notable industry change was reported.",
    )
    fallback_change = ensure_sentence(
        sections["what_changed"],
        fallback_update,
    )
    fallback_impact = ensure_sentence(
        sections["why_it_matters"],
        "This could affect SEO priorities, reporting, or campaign planning.",
    )

    return {
        "update": fallback_update,
        "what_changed": fallback_change,
        "why_it_matters": fallback_impact,
    }


def format_question(question):
    cleaned = normalize_whitespace(question)

    if cleaned.lower().startswith("question:"):
        cleaned = cleaned.split(":", 1)[1].strip()

    return ensure_sentence(cleaned, "What should marketers change first based on this update?")


def build_brief_rows(brief_data):
    items = ""

    for key, label in BRIEF_FIELDS:
        items += f"""
            <li style="margin-bottom:12px;">
                <span style="font-weight:700;color:#0f172a;">— {html.escape(label)}:</span>
                <span style="color:#334155;"> {html.escape(brief_data[key])}</span>
            </li>
        """

    return f"""
    <ul style="margin:0;padding-left:18px;list-style:none;color:#334155;font-size:14px;line-height:1.7;">
    {items}
    </ul>
    """


# -----------------------------
# GET ARTICLE TEXT
# -----------------------------

def get_article_text(url):
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        return " ".join(p.get_text() for p in soup.find_all("p"))
    except Exception:
        return ""


# -----------------------------
# GET ARTICLES
# -----------------------------

def get_articles(limit=2):
    selected = []

    for feed_url in NEWS_FEEDS:
        feed = feedparser.parse(feed_url)

        for entry in feed.entries:
            if is_promotional(entry.title):
                continue

            text = get_article_text(entry.link)

            if len(text) > 500:
                selected.append(text[:1500])  # limit input size

            if len(selected) >= limit:
                return selected

    return selected


# -----------------------------
# GEMINI CALL (SAFE)
# -----------------------------

def call_gemini(prompt):
    global api_calls_made

    if api_calls_made >= MAX_API_CALLS:
        return "API limit reached. Skipping insight."

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={GEMINI_API_KEY}"

        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }

        response = requests.post(url, json=payload, timeout=30)

        api_calls_made += 1

        data = response.json()

        if "candidates" in data and data["candidates"]:
            return data["candidates"][0]["content"]["parts"][0]["text"]

        if "error" in data:
            print("API Error:", data["error"])
            return "Insight unavailable due to API issue."

        return "No valid response from AI."

    except Exception as e:
        print("Exception:", str(e))
        return "AI generation failed."


# -----------------------------
# RETRY WRAPPER
# -----------------------------

def call_with_retry(prompt, retries=2):
    for _ in range(retries):
        result = call_gemini(prompt)

        if "failed" not in result.lower() and "error" not in result.lower():
            return result

        time.sleep(3)

    return "Final fallback: Unable to generate insight."


# -----------------------------
# GENERATE BRIEF
# -----------------------------

def generate_brief(text):
    prompt = f"""
    You are an expert in SEO and digital marketing.

    Summarize this into exactly three lines using this exact format:

    Update: <one sentence only, max 180 characters>
    What changed: <one sentence only, max 180 characters>
    Why it matters: <one sentence only, max 180 characters>

    Rules:
    - One sentence per line.
    - No bullets.
    - No markdown.
    - No extra intro or closing text.
    - Keep each line clear, compact, and easy to scan.

    Content:
    {text}
    """
    return parse_brief(call_with_retry(prompt))


# -----------------------------
# GENERATE QUESTION
# -----------------------------

def generate_question(text):
    prompt = f"""
    Based on this content, create one simple but thought-provoking
    question for digital marketers.

    Rules:
    - Return one sentence only.
    - Keep it under 18 words.
    - Do not add bullets or labels.

    Content:
    {text}
    """
    return format_question(call_with_retry(prompt))


# -----------------------------
# MAIN FLOW
# -----------------------------

print("Fetching articles...")
articles = get_articles()

if not articles:
    print("No articles found. Exiting.")
    raise SystemExit

print("Articles fetched:", len(articles))

print("Generating briefs...")
briefs = [generate_brief(article) for article in articles]

print("Generating question...")
question = generate_question(articles[0])

date = datetime.now().strftime("%A, %B %d, %Y")

# -----------------------------
# BUILD HTML
# -----------------------------

updates_html = ""

for i, brief in enumerate(briefs):
    updates_html += f"""
    <div style="margin-bottom:16px;border:1px solid #dbe4f0;border-radius:12px;background:#f8fafc;">
    <div style="padding:16px 18px;">
    <h2 style="margin:0 0 10px;color:#1d4ed8;font-size:17px;font-weight:700;">
    <strong>Update {i + 1}</strong>
    </h2>

    {build_brief_rows(brief)}
    </div>
    </div>
    """

html_content = f"""
<html>
<head>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&display=swap" rel="stylesheet">
</head>

<body style="margin:0;background:#eef1f5;font-family:'Montserrat',Arial,sans-serif;">

<div style="max-width:760px;margin:24px auto;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 12px rgba(15,23,42,0.08);">

<div style="background:linear-gradient(135deg,#1d4ed8,#4f46e5);color:white;padding:26px 24px;text-align:center;">
<h1 style="margin:0;font-size:24px;font-weight:700;">
Morning SEO Intelligence Brief
</h1>
<p style="margin:8px 0 0;font-size:14px;opacity:0.92;">
{date}
</p>
</div>

<div style="padding:22px;">

{updates_html}

<div style="margin-top:20px;">
<h2 style="margin:0 0 10px;color:#1d4ed8;font-size:17px;font-weight:700;">
Thinking Question
</h2>

<div style="background:#f8fafc;padding:16px 18px;border-left:4px solid #4f46e5;border-radius:10px;">
<p style="margin:0;color:#111827;font-size:14px;line-height:1.45;">
{html.escape(question)}
</p>
</div>
</div>

</div>

<div style="text-align:center;padding:20px;font-size:12px;color:#6b7280;">
Sent via Automated SEO Intelligence System
</div>

</div>

</body>
</html>
"""

# -----------------------------
# SEND EMAIL
# -----------------------------

print("Sending email...")

msg = MIMEText(html_content, "html")
msg["Subject"] = "Morning SEO Intelligence Brief"
msg["From"] = EMAIL_SENDER
msg["To"] = ", ".join(EMAIL_RECEIVERS)

try:
    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    server.login(EMAIL_SENDER, EMAIL_PASSWORD)

    server.sendmail(
        EMAIL_SENDER,
        EMAIL_RECEIVERS,
        msg.as_string()
    )

    server.quit()

    print("Email Sent Successfully")

except Exception as e:
    print("Email failed:", str(e))

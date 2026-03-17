import feedparser
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import os
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
    "udayff034@gmail.com"
]

EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

MODEL = "gemini-2.5-flash"

# RATE LIMIT CONTROL
MAX_API_CALLS = 3
api_calls_made = 0

# -----------------------------
# FILTER
# -----------------------------

PROMO_WORDS = ["services", "agency", "press release", "sponsored", "advertising"]

def is_promotional(title):
    return any(word in title.lower() for word in PROMO_WORDS)

# -----------------------------
# GET ARTICLE TEXT
# -----------------------------

def get_article_text(url):
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        return " ".join(p.get_text() for p in soup.find_all("p"))
    except:
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

        response = requests.post(url, json=payload)

        api_calls_made += 1

        data = response.json()

        if "candidates" in data and data["candidates"]:
            return data["candidates"][0]["content"]["parts"][0]["text"]

        elif "error" in data:
            print("API Error:", data["error"])
            return "Insight unavailable due to API issue."

        else:
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

    Summarize this into:

    What is the update:
    Why this update:
    Why it matters:

    Keep it concise and practical.

    Content:
    {text}
    """
    return call_with_retry(prompt)

# -----------------------------
# GENERATE QUESTION
# -----------------------------

def generate_question(text):
    prompt = f"""
    Based on this content, create ONE simple but thought-provoking
    question for digital marketers.

    Content:
    {text}
    """
    return call_with_retry(prompt)

# -----------------------------
# MAIN FLOW
# -----------------------------

print("Fetching articles...")
articles = get_articles()

if not articles:
    print("No articles found. Exiting.")
    exit()

print("Articles fetched:", len(articles))

print("Generating briefs...")
briefs = [generate_brief(a) for a in articles]

print("Generating question...")
question = generate_question(articles[0])

date = datetime.now().strftime("%A, %B %d, %Y")

# -----------------------------
# BUILD HTML
# -----------------------------

updates_html = ""

for i, brief in enumerate(briefs):
    formatted_brief = brief.replace("\n", "<br>")

    updates_html += f"""
    <div style="margin-bottom:25px;">
    
    <h2 style="color:#1d4ed8;font-size:20px;font-weight:700;margin-bottom:10px;">
    📌 Update {i+1}
    </h2>

    <div style="background:#f9fafb;padding:18px;border-radius:10px;border:1px solid #e5e7eb;">
    <p style="margin:0;color:#111827;font-size:15px;line-height:1.7;">
    {formatted_brief}
    </p>
    </div>

    </div>
    """

formatted_question = question.replace("\n", "<br>")

html_content = f"""
<html>
<head>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&display=swap" rel="stylesheet">
</head>

<body style="margin:0;background:#eef1f5;font-family:'Montserrat',Arial,sans-serif;">

<div style="max-width:720px;margin:40px auto;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 12px rgba(0,0,0,0.08);">

<div style="background:linear-gradient(135deg,#1d4ed8,#4f46e5);color:white;padding:35px;text-align:center;">
<h1 style="margin:0;font-size:26px;font-weight:700;">
🚀 Morning SEO Intelligence Brief
</h1>
<p style="margin-top:10px;font-size:14px;opacity:0.9;">
{date}
</p>
</div>

<div style="padding:30px;">

{updates_html}

<div style="margin-top:30px;">
<h2 style="color:#1d4ed8;font-size:20px;font-weight:700;">
💡 Thinking Question
</h2>

<div style="background:#f9fafb;padding:18px;border-left:5px solid #4f46e5;border-radius:8px;">
<p style="margin:0;color:#111827;font-size:15px;line-height:1.6;">
{formatted_question}
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
msg["Subject"] = "🚀 Morning SEO Intelligence Brief"
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

    print("✅ Email Sent Successfully")

except Exception as e:
    print("❌ Email failed:", str(e))

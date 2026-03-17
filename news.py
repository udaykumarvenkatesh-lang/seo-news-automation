import feedparser
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import os
import re

# -----------------------------
# CONFIG
# -----------------------------

NEWS_FEEDS = [
    "https://www.searchenginejournal.com/feed/",
    "https://searchengineland.com/feed/",
    "https://techcrunch.com/feed/"
]

EMAIL_SENDER = "udaykumar.venkatesh@joytechnologies.com"
EMAIL_RECEIVER = "udaykumar.venkatesh@joytechnologies.com"

EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# -----------------------------
# FILTER
# -----------------------------

PROMO_WORDS = [
    "services", "agency", "press release",
    "sponsored", "advertising"
]

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
# PICK 2 BEST ARTICLES
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
                selected.append(text)

            if len(selected) >= limit:
                return selected

    return selected

# -----------------------------
# GEMINI CALL
# -----------------------------

def call_gemini(prompt):

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    response = requests.post(url, json=payload)
    data = response.json()

    return data["candidates"][0]["content"]["parts"][0]["text"]

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
    {text[:3000]}
    """

    return call_gemini(prompt)

# -----------------------------
# GENERATE QUESTION
# -----------------------------

def generate_question(text):

    prompt = f"""
    Based on this content, create ONE simple but thought-provoking
    question for SEO or digital marketing professionals.

    Content:
    {text[:2000]}
    """

    return call_gemini(prompt)

# -----------------------------
# MAIN FLOW
# -----------------------------

articles = get_articles()

briefs = [generate_brief(a) for a in articles]

question = generate_question(articles[0])

date = datetime.now().strftime("%A, %B %d, %Y")

# -----------------------------
# HTML BUILD
# -----------------------------

updates_html = ""

for i, brief in enumerate(briefs):
    updates_html += f"""
    <h2>Update {i+1}</h2>
    <div style="background:#f5f5f5;padding:15px;border-radius:8px;margin-bottom:25px;line-height:1.6;">
    {brief.replace('\n', '<br>')}
    </div>
    """

html_content = f"""
<html>
<body style="margin:0;background:#f2f2f2;font-family:Arial;">

<div style="max-width:720px;margin:auto;background:white;">

<div style="background:#1d213f;color:white;text-align:center;padding:40px;">
<h1>Digital Intelligence Brief</h1>
<p>{date}</p>
</div>

<div style="padding:30px;">

{updates_html}

<h2>Thinking Question</h2>
<p style="font-style:italic;background:#fafafa;padding:15px;border-left:4px solid #1d213f;">
{question}
</p>

</div>

</div>

</body>
</html>
"""

# -----------------------------
# SEND EMAIL
# -----------------------------

msg = MIMEText(html_content, "html")

msg["Subject"] = "Digital Intelligence Brief"
msg["From"] = EMAIL_SENDER
msg["To"] = EMAIL_RECEIVER

server = smtplib.SMTP_SSL("smtp.gmail.com", 465)

server.login(EMAIL_SENDER, EMAIL_PASSWORD)

server.sendmail(
    EMAIL_SENDER,
    EMAIL_RECEIVER,
    msg.as_string()
)

server.quit()

print("✅ Daily Brief Sent")

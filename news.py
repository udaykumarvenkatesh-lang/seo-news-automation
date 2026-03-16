import feedparser
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import random
import re
import os

# -----------------------------
# RSS SOURCES
# -----------------------------

NEWS_FEEDS = [
    "https://www.searchenginejournal.com/feed/",
    "https://searchengineland.com/feed/",
    "https://techcrunch.com/feed/"
]

RESEARCH_FEEDS = [
    "https://blog.hubspot.com/marketing/rss.xml",
    "https://moz.com/blog/rss",
    "https://ahrefs.com/blog/feed/"
]

# -----------------------------
# EMAIL SETTINGS
# -----------------------------

EMAIL_SENDER = "udaykumar.venkatesh@joytechnologies.com"
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = "udaykumar.venkatesh@joytechnologies.com"

# -----------------------------
# FILTER PROMOTIONAL ARTICLES
# -----------------------------

PROMO_WORDS = [
    "services",
    "agency",
    "press release",
    "sponsored",
    "advertising",
    "company announces"
]

def is_promotional(title):

    title = title.lower()

    for word in PROMO_WORDS:
        if word in title:
            return True

    return False


# -----------------------------
# GET ARTICLE TEXT
# -----------------------------

def get_article_text(url):

    try:

        headers = {"User-Agent": "Mozilla/5.0"}

        r = requests.get(url, headers=headers, timeout=10)

        soup = BeautifulSoup(r.text, "html.parser")

        paragraphs = soup.find_all("p")

        text = " ".join(p.get_text() for p in paragraphs)

        return text

    except:
        return ""


# -----------------------------
# CREATE SUMMARY
# -----------------------------

def summarize(text):

    sentences = re.split(r'(?<=[.!?]) +', text)

    for s in sentences:

        s = s.strip()

        if 120 < len(s) < 220 and "subscribe" not in s.lower():

            return s

    return "Summary unavailable."


# -----------------------------
# TOP INDUSTRY NEWS
# -----------------------------

def get_top_news():

    for feed_url in NEWS_FEEDS:

        feed = feedparser.parse(feed_url)

        for entry in feed.entries:

            title = entry.title

            if is_promotional(title):
                continue

            text = get_article_text(entry.link)

            summary = summarize(text)

            if summary != "Summary unavailable.":

                return title, summary

    return "No major update today.", "No summary available."


# -----------------------------
# GOOGLE ALGORITHM WATCH
# -----------------------------

def detect_algorithm_news():

    for feed_url in NEWS_FEEDS:

        feed = feedparser.parse(feed_url)

        for entry in feed.entries:

            title = entry.title.lower()

            if (
                "google update" in title
                or "algorithm update" in title
                or "ranking volatility" in title
                or "core update" in title
            ):

                return entry.title

    return "No significant Google ranking volatility detected today."


# -----------------------------
# EXTRACT INSIGHTS
# -----------------------------

INSIGHT_KEYWORDS = [
    "data",
    "study",
    "research",
    "increase",
    "improve",
    "conversion",
    "ranking",
    "traffic",
    "marketers",
    "seo strategy",
    "search results",
    "users",
    "ai tools",
    "algorithm",
    "content strategy"
]

def get_insights():

    insights = []

    for feed_url in RESEARCH_FEEDS:

        feed = feedparser.parse(feed_url)

        for entry in feed.entries[:3]:

            text = get_article_text(entry.link)

            sentences = re.split(r'(?<=[.!?]) +', text)

            for sentence in sentences:

                sentence = sentence.strip()

                if len(sentence) < 90 or len(sentence) > 200:
                    continue

                if any(word in sentence.lower() for word in INSIGHT_KEYWORDS):

                    if "subscribe" not in sentence.lower():

                        insights.append(sentence)

    random.shuffle(insights)

    return insights[:5]


# -----------------------------
# FETCH CONTENT
# -----------------------------

news_title, news_summary = get_top_news()

algorithm_watch = detect_algorithm_news()

insights = get_insights()

date = datetime.now().strftime("%A, %B %d, %Y")

# -----------------------------
# BUILD INSIGHTS HTML
# -----------------------------

insights_html = ""

for insight in insights:

    insights_html += f"<li style='margin-bottom:10px;'>{insight}</li>"


# -----------------------------
# HTML NEWSLETTER
# -----------------------------

html_content = f"""
<html>
<body style="margin:0;background:#f2f2f2;font-family:Arial;">

<div style="max-width:720px;margin:auto;background:white;">

<div style="background:#1d213f;color:white;text-align:center;padding:40px;">

<h1 style="margin:0;">SEO Intelligence Brief</h1>

<p style="margin-top:10px;font-size:15px;">
{date}
</p>

</div>

<div style="padding:35px;">

<h2>Top Industry Update</h2>

<h3 style="color:#222;">{news_title}</h3>

<div style="
background:#f5f5f5;
border:1px solid #e2e2e2;
padding:18px;
border-radius:8px;
line-height:1.6;
margin-bottom:35px;">

{news_summary}

</div>

<h2>Google Algorithm Watch</h2>

<p style="line-height:1.6;">
{algorithm_watch}
</p>

<h2 style="margin-top:35px;">SEO / AI / Marketing Insights</h2>

<ul style="line-height:1.7;padding-left:20px;">
{insights_html}
</ul>

</div>

</div>

</body>
</html>
"""

# -----------------------------
# SEND EMAIL
# -----------------------------

msg = MIMEText(html_content, "html")

msg["Subject"] = "SEO Intelligence Brief"
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

print("SEO Intelligence newsletter sent.")

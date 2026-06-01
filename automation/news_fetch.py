import feedparser
import json
import os
import re
import time
import html
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ============================================================
# CONFIGURATION
# ============================================================

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"

MAX_PER_CATEGORY = 4
DAYS_TO_KEEP = 7  # Keep 7 days of news history

SOURCES = {
    "ai-at-work": [
        {"name": "TechCrunch", "url": "https://techcrunch.com/category/artificial-intelligence/feed"},
        {"name": "VentureBeat", "url": "https://venturebeat.com/category/ai/feed"},
        {"name": "SiliconAngle", "url": "https://siliconangle.com/feed"},
    ],
    "tools-tech": [
        {"name": "ZDNet", "url": "https://zdnet.com/news/rss.xml"},
        {"name": "CIO.com", "url": "https://cio.com/index.rss"},
        {"name": "Computerworld", "url": "https://computerworld.com/feed"},
    ],
    "digital-culture": [
        {"name": "Fast Company", "url": "https://fastcompany.com/work-life/rss"},
        {"name": "WorkLife", "url": "https://worklife.news/feed"},
        {"name": "Wired", "url": "https://wired.com/feed/category/business/rss"},
    ],
    "industry-news": [
        {"name": "TechRepublic", "url": "https://www.techrepublic.com/rssfeeds/articles/"},
        {"name": "ITPro", "url": "https://www.itpro.com/feeds.xml"},
        {"name": "Computer Weekly", "url": "https://www.computerweekly.com/rss/All-ComputerWeekly-News.xml"},
    ],
}

RELEVANCE_KEYWORDS = [
    "workplace", "work", "employee", "enterprise", "productivity", "collaboration",
    "remote", "hybrid", "microsoft", "slack", "teams", "zoom", "google workspace",
    "servicenow", "jira", "itsm", "helpdesk", "service desk", "intranet", "sharepoint",
    "copilot", "ai", "artificial intelligence", "automation", "digital workplace",
    "workforce", "human resources", "hr", "saas", "cloud", "software", "platform",
    "leadership", "management", "future of work", "return to office",
    "cybersecurity", "data breach", "enterprise software", "cio", "cto",
    "digital transformation", "technology", "tech"
]

# ============================================================
# FUNCTIONS
# ============================================================

def is_relevant(title, excerpt):
    text = (title + " " + excerpt).lower()
    matches = sum(1 for kw in RELEVANCE_KEYWORDS if kw in text)
    return matches >= 2


def fetch_feed(source):
    try:
        feed = feedparser.parse(source["url"])
        items = []
        for entry in feed.entries[:10]:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            excerpt = entry.get("summary", entry.get("description", "")).strip()
            excerpt = re.sub(r'<[^>]+>', '', excerpt)
            excerpt = html.unescape(excerpt)
            excerpt = re.sub(r'\s+', ' ', excerpt).strip()[:400]
            title = html.unescape(re.sub(r'<[^>]+>', '', title)).strip()
            if title and link:
                items.append({
                    "title": title,
                    "url": link,
                    "excerpt": excerpt,
                    "source": source["name"]
                })
        return items
    except Exception as e:
        print(f"Error fetching {source['name']}: {e}")
        return []


def generate_take(title, excerpt, source):
    if not ANTHROPIC_API_KEY:
        print("No Anthropic API key found — skipping AI generation")
        return excerpt[:200]

    prompt = (
        "You are DWP Insider, a digital workplace expert with 30 years of experience. "
        "You write punchy, opinionated takes on digital workplace news for centerofthesandwich.com. "
        "Your style is direct, occasionally humorous, grounded in real experience, never uses hype or corporate speak. "
        "You never use em dashes. Plain conversational English. Complete sentences always.\n\n"
        "Write a 3 sentence response about this article:\n"
        "Sentence 1: What happened, stated plainly and factually.\n"
        "Sentence 2: Why it matters to digital workplace professionals.\n"
        "Sentence 3: Your DWP Insider opinion or a touch of humor.\n\n"
        "Keep under 100 words. No bullet points. No headers. Just three sentences as a paragraph.\n\n"
        f"Article title: {title}\n"
        f"Source: {source}\n"
        f"Excerpt: {excerpt}"
    )

    try:
        response = requests.post(
            ANTHROPIC_URL,
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01"
            },
            json={
                "model": ANTHROPIC_MODEL,
                "max_tokens": 300,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30
        )
        print(f"    Anthropic status: {response.status_code}")
        data = response.json()
        if "content" in data:
            time.sleep(2)
            return data["content"][0]["text"].strip()
        else:
            print(f"    Anthropic response: {data}")
            time.sleep(2)
            return excerpt[:200]
    except Exception as e:
        print(f"Anthropic API error: {e}")
        return excerpt[:200]


def load_existing_urls():
    seen_file = Path("_data/seen_urls.json")
    if seen_file.exists():
        return set(json.load(open(seen_file)))
    return set()


def save_seen_urls(urls):
    seen_file = Path("_data/seen_urls.json")
    seen_file.parent.mkdir(exist_ok=True)
    url_list = list(urls)[-500:]
    with open(seen_file, "w") as f:
        json.dump(url_list, f)


def load_news_history():
    """Load existing news history file."""
    history_file = Path("_data/news_history.json")
    if history_file.exists():
        return json.loads(history_file.read_text())
    return []


def save_news_data(todays_stories, history):
    """Save today's news and updated history."""
    data_dir = Path("_data")
    data_dir.mkdir(exist_ok=True)

    # Save today's news for homepage takes
    today_output = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "categories": todays_stories
    }
    with open(data_dir / "news.json", "w") as f:
        json.dump(today_output, f, indent=2)

    # Save accumulated history for news page
    with open(data_dir / "news_history.json", "w") as f:
        json.dump(history, f, indent=2)

    total_today = sum(len(v) for v in todays_stories.values())
    print(f"Saved {total_today} new stories. History has {len(history)} total stories.")


# ============================================================
# MAIN
# ============================================================

def main():
    print(f"Starting news fetch at {datetime.now().isoformat()}")

    seen_urls = load_existing_urls()
    history = load_news_history()

    # Remove stories older than DAYS_TO_KEEP
    cutoff = datetime.now(timezone.utc) - timedelta(days=DAYS_TO_KEEP)
    history = [
        s for s in history
        if datetime.fromisoformat(s["date"].replace("Z", "+00:00")) > cutoff
    ]
    print(f"Loaded {len(history)} stories from last {DAYS_TO_KEEP} days")

    todays_stories = {}
    new_urls = set()

    for category, sources in SOURCES.items():
        print(f"\nProcessing category: {category}")
        category_stories = []

        for source in sources:
            print(f"  Fetching {source['name']}...")
            items = fetch_feed(source)

            for item in items:
                if item["url"] in seen_urls:
                    continue
                if not is_relevant(item["title"], item["excerpt"]):
                    continue

                print(f"    Generating take for: {item['title'][:60]}...")
                take = generate_take(item["title"], item["excerpt"], item["source"])

                story = {
                    "title": item["title"],
                    "url": item["url"],
                    "source": item["source"],
                    "category": category,
                    "excerpt": item["excerpt"][:200],
                    "dwp_take": take,
                    "date": datetime.now(timezone.utc).isoformat()
                }

                category_stories.append(story)
                history.append(story)
                new_urls.add(item["url"])

                if len(category_stories) >= MAX_PER_CATEGORY:
                    break

            if len(category_stories) >= MAX_PER_CATEGORY:
                break

        todays_stories[category] = category_stories
        print(f"  Found {len(category_stories)} stories for {category}")

    save_news_data(todays_stories, history)
    save_seen_urls(seen_urls | new_urls)

    print(f"\nDone. Total new stories today: {sum(len(v) for v in todays_stories.values())}")


if __name__ == "__main__":
    main()

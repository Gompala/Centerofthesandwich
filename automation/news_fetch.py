import feedparser
import json
import os
import re
import time
import html
import requests
from datetime import datetime, timezone
from pathlib import Path

# ============================================================
# CONFIGURATION
# ============================================================

# Anthropic API key — loaded from environment variable, never hardcoded
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"

# Max stories per category
MAX_PER_CATEGORY = 4

# RSS sources by category
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

# Keywords that indicate digital workplace relevance
# Requires at least 2 matches - keeping these specific to avoid off-topic articles
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
    """Check if article is relevant to digital workplace topics."""
    text = (title + " " + excerpt).lower()
    matches = sum(1 for kw in RELEVANCE_KEYWORDS if kw in text)
    return matches >= 2


def fetch_feed(source):
    """Fetch and parse an RSS feed safely."""
    try:
        feed = feedparser.parse(source["url"])
        items = []
        for entry in feed.entries[:10]:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            excerpt = entry.get("summary", entry.get("description", "")).strip()
            # Strip HTML tags
            excerpt = re.sub(r'<[^>]+>', '', excerpt)
            # Decode HTML entities like &ldquo; &nbsp; &rsquo;
            excerpt = html.unescape(excerpt)
            # Clean up whitespace
            excerpt = re.sub(r'\s+', ' ', excerpt).strip()[:400]
            # Clean title the same way
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
    """Call Anthropic API to write a DWP Insider summary and take."""
    if not ANTHROPIC_API_KEY:
        print("No Anthropic API key found — skipping AI generation")
        return excerpt[:200]

    prompt = (
        "You are DWP Insider, a digital workplace expert with 30 years of experience. "
        "You write punchy, opinionated takes on digital workplace news for your blog centerofthesandwich.com. "
        "Your style is direct, occasionally humorous, grounded in real experience, and never uses hype or corporate speak. "
        "You cut through noise and tell IT leaders and digital workplace professionals what actually matters. "
        "You never use em dashes. You write in plain conversational English. You always write in complete sentences.\n\n"
        "Write a 3 sentence response about this article:\n"
        "Sentence 1: What happened, stated plainly and factually.\n"
        "Sentence 2: Why it matters to digital workplace professionals.\n"
        "Sentence 3: Your DWP Insider opinion or a touch of humor.\n\n"
        "Keep the total response under 100 words. Do not use bullet points. Do not use headers. "
        "Just write the three sentences as a paragraph. Do not start with the words DWP Insider.\n\n"
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
                "messages": [
                    {"role": "user", "content": prompt}
                ]
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
    """Load URLs already published to avoid duplicates."""
    seen_file = Path("_data/seen_urls.json")
    if seen_file.exists():
        with open(seen_file) as f:
            return set(json.load(f))
    return set()


def save_seen_urls(urls):
    """Save seen URLs to avoid future duplicates."""
    seen_file = Path("_data/seen_urls.json")
    seen_file.parent.mkdir(exist_ok=True)
    # Keep only last 500 URLs to prevent file growing too large
    url_list = list(urls)[-500:]
    with open(seen_file, "w") as f:
        json.dump(url_list, f)


def save_news_data(news_by_category):
    """Save curated news as a JSON data file for Eleventy to use."""
    data_file = Path("_data/news.json")
    data_file.parent.mkdir(exist_ok=True)

    output = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "categories": news_by_category
    }

    with open(data_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Saved {sum(len(v) for v in news_by_category.values())} stories to {data_file}")


# ============================================================
# MAIN
# ============================================================

def main():
    print(f"Starting news fetch at {datetime.now().isoformat()}")

    seen_urls = load_existing_urls()
    news_by_category = {}
    new_urls = set()

    for category, sources in SOURCES.items():
        print(f"\nProcessing category: {category}")
        category_stories = []

        for source in sources:
            print(f"  Fetching {source['name']}...")
            items = fetch_feed(source)

            for item in items:
                # Skip if already seen
                if item["url"] in seen_urls:
                    continue

                # Check relevance
                if not is_relevant(item["title"], item["excerpt"]):
                    continue

                # Generate DWP Insider take
                print(f"    Generating take for: {item['title'][:60]}...")
                take = generate_take(item["title"], item["excerpt"], item["source"])

                category_stories.append({
                    "title": item["title"],
                    "url": item["url"],
                    "source": item["source"],
                    "excerpt": item["excerpt"][:200],
                    "dwp_take": take,
                    "date": datetime.now(timezone.utc).isoformat()
                })

                new_urls.add(item["url"])

                # Stop once we have enough for this category
                if len(category_stories) >= MAX_PER_CATEGORY:
                    break

            if len(category_stories) >= MAX_PER_CATEGORY:
                break

        news_by_category[category] = category_stories
        print(f"  Found {len(category_stories)} stories for {category}")

    # Save results
    save_news_data(news_by_category)
    save_seen_urls(seen_urls | new_urls)

    print(f"\nDone. Total new stories: {sum(len(v) for v in news_by_category.values())}")


if __name__ == "__main__":
    main()

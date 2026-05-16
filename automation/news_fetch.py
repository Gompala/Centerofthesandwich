import feedparser
import json
import os
import requests
from datetime import datetime, timezone
from pathlib import Path

# ============================================================
# CONFIGURATION
# ============================================================

# Your Gemini API key — loaded from environment variable, never hardcoded
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# Max stories per category to keep API costs minimal
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
        {"name": "Wired", "url": "https://wired.com/feed/rss"},
    ],
    "industry-news": [
        {"name": "HR Dive", "url": "https://hrdive.com/feeds/news/"},
        {"name": "Forbes Innovation", "url": "https://forbes.com/innovation/feed2"},
        {"name": "The Register", "url": "https://theregister.com/headlines.atom"},
    ],
}

# Keywords that indicate digital workplace relevance
RELEVANCE_KEYWORDS = [
    "workplace", "work", "employee", "enterprise", "productivity", "collaboration",
    "remote", "hybrid", "office", "microsoft", "slack", "teams", "zoom", "google",
    "servicenow", "jira", "itsm", "helpdesk", "service desk", "intranet", "sharepoint",
    "copilot", "ai", "automation", "digital", "workforce", "hr", "human resources",
    "saas", "cloud", "software", "platform", "tool", "app", "technology", "tech",
    "leadership", "management", "culture", "future of work", "return to office"
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
        for entry in feed.entries[:10]:  # Only look at latest 10 per source
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            excerpt = entry.get("summary", entry.get("description", "")).strip()
            # Strip HTML tags from excerpt
            import re
            excerpt = re.sub(r'<[^>]+>', '', excerpt)[:400]
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
    """Call Gemini API to write a DWP Guy summary and take."""
    if not GEMINI_API_KEY:
        print("No Gemini API key found — skipping AI generation")
        return excerpt[:200]

    prompt = f"""You are DWP Guy, a digital workplace expert with 30 years of experience. 
You write short, punchy, opinionated takes on digital workplace news. 
Your style is direct, occasionally humorous, and always grounded in real-world experience.
You cut through hype and focus on what actually matters to IT leaders and digital workplace professionals.
You never use em dashes. You write in plain conversational English.

Write a 2-3 sentence summary and take on this article. 
Start with a brief factual summary of what happened, then add your DWP Guy perspective.
Keep it under 60 words total.

Article title: {title}
Source: {source}
Excerpt: {excerpt}

Write only the summary and take. No introduction, no "DWP Guy here", just the content."""

    try:
        response = requests.post(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 150
                }
            },
            timeout=15
        )
        print(f"    Gemini status: {response.status_code}")
        data = response.json()
        if "candidates" in data:
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        else:
            print(f"    Gemini response: {data}")
            return excerpt[:200]
    except Exception as e:
        print(f"Gemini API error: {e}")
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

                # Generate DWP Guy take
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

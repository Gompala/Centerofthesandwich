import os
import re
import json
import requests
from datetime import datetime, timezone
from pathlib import Path

# ============================================================
# CONFIGURATION
# ============================================================

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"

TOPIC_FILE = Path("_data/article_topic.txt")
NEWS_FILE = Path("_data/news.json")
POSTS_DIR = Path("_posts")

# ============================================================
# FUNCTIONS
# ============================================================

def get_topic():
    """Get today's article topic — from file or pick from news with category rotation."""
    if TOPIC_FILE.exists():
        lines = [l.strip() for l in TOPIC_FILE.read_text().splitlines() if l.strip()]
        if lines:
            topic = lines[0]
            # Remove the first line, keep the rest for future days
            remaining = '\n'.join(lines[1:])
            TOPIC_FILE.write_text(remaining)
            print(f"Using suggested topic: {topic}")
            print(f"Remaining queued topics: {len(lines)-1}")
            return topic, None

    # Rotate categories by day of week to ensure variety
    # Mon=ai-at-work, Tue=tools-tech, Wed=digital-culture, Thu=strategy,
    # Fri=industry-news, Sat=ai-at-work, Sun=tools-tech
    day = datetime.now(timezone.utc).weekday()
    rotation = {
        0: "ai-at-work",
        1: "tools-tech",
        2: "digital-culture",
        3: "strategy",
        4: "industry-news",
        5: "ai-at-work",
        6: "tools-tech",
    }
    preferred_cat = rotation[day]
    print(f"Today is day {day}, targeting category: {preferred_cat}")

    # Fallback topics by category if news is empty
    fallback_topics = {
        "ai-at-work": "How to measure real AI adoption in your workplace beyond license counts",
        "tools-tech": "The honest guide to choosing between Microsoft Teams and Slack in 2026",
        "digital-culture": "Why hybrid work policies keep failing and what actually works",
        "strategy": "Building a digital workplace roadmap that survives contact with reality",
        "industry-news": "What the latest enterprise tech consolidation means for IT leaders",
    }

    if NEWS_FILE.exists():
        news = json.loads(NEWS_FILE.read_text())
        categories = news.get("categories", {})

        # First try preferred category
        stories = categories.get(preferred_cat, [])
        if stories:
            story = stories[0]
            print(f"Auto-picking topic from {preferred_cat}: {story['title']}")
            return story["title"], story

        # Then try any other category
        for cat in ["ai-at-work", "tools-tech", "digital-culture", "strategy", "industry-news"]:
            if cat == preferred_cat:
                continue
            stories = categories.get(cat, [])
            if stories:
                story = stories[0]
                print(f"Fallback to {cat}: {story['title']}")
                return story["title"], story

    # No news available — use fallback topic for today's category
    fallback = fallback_topics.get(preferred_cat, "The state of digital workplace technology in 2026")
    print(f"Using fallback topic: {fallback}")
    return fallback, None


def generate_article(topic, source_story=None):
    """Call Anthropic API to write a full DWP Insider article."""
    if not ANTHROPIC_API_KEY:
        print("No Anthropic API key — skipping article generation")
        return None

    context = ""
    if source_story:
        context = f"\nThis is inspired by a news story: {source_story['title']}\nExcerpt: {source_story['excerpt']}\nSource: {source_story['source']}\n"

    prompt = f"""You are DWP Insider, a digital workplace expert with 30 years of experience writing for centerofthesandwich.com.

Write a complete blog article on this topic: {topic}
{context}

You write like a real person, not a consultant.

Here is the voice to aim for: imagine someone who has been in IT for 30 years, has seen every trend, survived every reorganization, and still genuinely loves this industry. They tell stories. They laugh at themselves occasionally. They get excited when something actually works. They roll their eyes at buzzwords but they are not cynical — they are realistic and hopeful at the same time. They talk to you like a peer, not a student.

Specific rules:

NEVER say these things:
- "I've seen this a thousand times"
- "You need to fix this"
- "Here's what you need to do"
- "It's worth noting"
- "It's important to remember"
- "In conclusion"
- "At the end of the day"
- "In my X years of experience"
- "Let me be direct"
- "Here's the thing"
- "The bottom line is"
- "Make no mistake"

DO write like this instead:
- Share a specific observation or small story that makes the reader nod
- Acknowledge that things are messy and complicated without being doom and gloom
- Find the funny angle — what's absurd about this situation? What would make a tired IT manager smile?
- Be hopeful and specific about what good looks like, not just what bad looks like
- End with something that makes the reader think or smile, not a summary of what you just said

Tone examples:
- BAD: "Organizations frequently fail to implement AI effectively due to poor change management."
- GOOD: "Most AI rollouts fail for the same reason most diets fail — everyone's excited in January and exhausted by March."

- BAD: "You need to ensure your service desk team is properly trained before deployment."
- GOOD: "Dropping a new AI tool on your service desk team without training is like handing someone car keys and saying good luck — technically possible, probably fine, definitely going to end badly."

Format rules:
- No em dashes ever
- Vary sentence length — short punchy ones mixed with longer flowing ones
- Paragraphs should feel like conversation, not a report
- One or two genuinely funny lines per article, not forced — if it does not feel natural, leave it out
- End with a single thought that feels like the last thing you would say before walking out of the room


Category guide — pick the BEST fit:
- ai-at-work: AI tools, copilots, automation, machine learning in workplace contexts
- tools-tech: Specific software tools, platforms, vendors, tech comparisons (Teams, Slack, ServiceNow, Jira, Microsoft 365, etc.)
- digital-culture: Remote work, hybrid work, employee experience, workplace culture, return to office, burnout, people management
- industry-news: Regulatory changes, market moves, acquisitions, industry trends, research reports
- strategy: IT strategy, digital transformation, budgeting, leadership, change management, roadmaps
- personal: Personal opinions, career lessons, 30 years experience stories, advice columns

The article must be returned as JSON with exactly these fields:
{{
  "title": "A compelling article title (not the topic verbatim)",
  "excerpt": "A 1-2 sentence summary for the homepage card (under 200 chars)",
  "category": "pick the single best category from the list above",
  "readtime": 6,
  "body": "The full article in markdown format, 600-900 words, with ## subheadings"
}}

Return ONLY the JSON object. No preamble, no explanation, no markdown code fences."""

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
                "max_tokens": 2000,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=60
        )
        print(f"Anthropic status: {response.status_code}")
        data = response.json()
        
        if "content" not in data:
            print(f"Anthropic error: {data}")
            return None
            
        text = data["content"][0]["text"].strip()
        # Strip any accidental markdown fences
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        
        article = json.loads(text)
        print(f"Generated article: {article['title']}")
        return article
        
    except Exception as e:
        print(f"Article generation error: {e}")
        return None


def save_article(article):
    """Save article as a markdown file in _posts/."""
    POSTS_DIR.mkdir(exist_ok=True)
    
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # Create slug from title
    slug = re.sub(r'[^a-z0-9]+', '-', article['title'].lower()).strip('-')[:60]
    filename = f"{today}-{slug}.md"
    filepath = POSTS_DIR / filename
    
    # Don't overwrite if already exists
    if filepath.exists():
        print(f"Article already exists for today: {filename}")
        return False
    
    frontmatter = f"""---
title: "{article['title']}"
date: {datetime.now(timezone.utc).isoformat()}
category: "{article['category']}"
excerpt: "{article['excerpt']}"
readtime: {article['readtime']}
featured: true
layout: article.njk
tags:
  - digital workplace
  - {article['category']}
---

{article['body']}
"""
    
    filepath.write_text(frontmatter)
    print(f"Saved article: {filepath}")
    return True


# ============================================================
# MAIN
# ============================================================

def main():
    print(f"Starting article generation at {datetime.now().isoformat()}")
    
    topic, source_story = get_topic()
    article = generate_article(topic, source_story)
    
    if article:
        saved = save_article(article)
        if saved:
            print("Article generation complete.")
        else:
            print("Skipped — article already exists for today.")
    else:
        print("Article generation failed — no article saved.")


if __name__ == "__main__":
    main()

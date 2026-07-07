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

    prompt = f"""Write a blog article about this topic for centerofthesandwich.com: {topic}
{context}

Think of this like a game review — not a game review literally, but that style and energy. A good game reviewer doesn't open with "here is why action games matter" and close with "so in summary, action games have challenges but also opportunities." They just dive in, share what they noticed, have opinions, keep moving. The reader stays with them because it's interesting, not because there's a lesson at the end.

That's what this article should feel like. A smart person sharing a genuine take on something happening in the digital workplace world. Moving, observational, occasionally funny, always interesting. The reader should feel like they're reading something worth their time, not sitting through a presentation.

The structure should feel natural and unforced. Start somewhere interesting — not necessarily the beginning of the topic, maybe the middle, maybe a detail that opens something up. Move through the piece the way a good conversation moves, following what's interesting rather than a predetermined outline. End when you've said something worth ending on, not because you've completed a template.

No three-part structure. No "challenge, insight, takeaway" arc. No subheadings that announce what's coming like a PowerPoint deck. Just writing that flows.

Voice: warm, direct, genuinely curious, occasionally wry. Like someone who finds this stuff interesting and assumes you do too. Not explaining things to people who don't know, just sharing takes with people who do.

Hard rules:
- Never reference your own experience, history, or how long you've been watching this industry
- Never fabricate statistics, timeframes, client stories, or specific situations you claim to have witnessed
- Never write a title that sounds like a command or a directive ("Stop Doing X", "Why You Must Y")
- Never use: "Here's the honest part", "The real issue is", "What's actually happening", "In conclusion", "It's worth noting", "Make no mistake"
- Never imply the reader is doing something wrong or missing something obvious
- No em dashes ever

The title should sound like something you'd genuinely want to click on — curious, specific, a little unexpected. Not a lesson, not a warning, just an interesting angle on something.

Category — pick the single best fit:
- ai-at-work: AI tools, copilots, automation in workplace contexts
- tools-tech: Specific software, platforms, vendors, tech comparisons
- digital-culture: Remote work, hybrid, employee experience, workplace culture
- industry-news: Market moves, acquisitions, industry trends
- strategy: IT strategy, digital transformation, leadership, change management
- personal: Opinions, observations, career takes

Return as JSON with exactly these fields:
{{
  "title": "A title that makes someone want to read this",
  "excerpt": "One or two sentences that make the article sound worth clicking (under 200 chars)",
  "category": "best fit category from list above",
  "readtime": 5,
  "body": "The full article in markdown format, 500-700 words, written in flowing prose with no subheading structure unless it genuinely serves the piece"
}}

Return ONLY the JSON. No preamble, no explanation, no markdown code fences."""

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

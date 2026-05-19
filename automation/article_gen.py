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
    """Get today's article topic — from file or pick from news."""
    if TOPIC_FILE.exists():
        topic = TOPIC_FILE.read_text().strip()
        if topic:
            print(f"Using suggested topic: {topic}")
            # Clear the topic file after reading
            TOPIC_FILE.write_text("")
            return topic, None

    # No topic file — pick best story from news
    if NEWS_FILE.exists():
        news = json.loads(NEWS_FILE.read_text())
        categories = news.get("categories", {})
        for cat in ["ai-at-work", "tools-tech", "digital-culture", "industry-news"]:
            stories = categories.get(cat, [])
            if stories:
                story = stories[0]
                print(f"Auto-picking topic from: {story['title']}")
                return story["title"], story
    
    return "The state of digital workplace technology in 2026", None


def generate_article(topic, source_story=None):
    """Call Anthropic API to write a full DWP Guy article."""
    if not ANTHROPIC_API_KEY:
        print("No Anthropic API key — skipping article generation")
        return None

    context = ""
    if source_story:
        context = f"\nThis is inspired by a news story: {source_story['title']}\nExcerpt: {source_story['excerpt']}\nSource: {source_story['source']}\n"

    prompt = f"""You are DWP Guy, a digital workplace expert with 30 years of experience writing for centerofthesandwich.com.

Write a complete blog article on this topic: {topic}
{context}

Your writing style:
- Direct, opinionated, occasionally humorous
- Grounded in real-world experience, not hype
- Written for IT leaders and digital workplace professionals
- No em dashes ever. Plain conversational English. Complete sentences always.
- Cut through noise and focus on what actually matters

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

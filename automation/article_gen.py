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

        prompt = f"""Write a short blog post for centerofthesandwich.com about: {topic}
{context}

The site is called Center of the Sandwich. The writer is called DWP Insider. The audience is people who work in or lead digital workplace functions — IT, service management, employee experience, that world.

Write like a smart person sharing a genuine take — not teaching, not advising, not revealing hidden truths. Just thinking out loud about something interesting. The tone should feel like a well-written opinion column in a trade publication, but warmer and more human than that sounds. Have some fun with it — a well-placed observation that makes someone smile, an unexpected comparison, a moment of genuine wit. Not forced, not a punchline, just the kind of thing that makes you realize the writer actually enjoyed writing this.

Start anywhere except the beginning of the topic. Don't open with "There's this moment" or "Something interesting is happening" or any variation of scene-setting throat-clearing. Just start with a thought. The opening line should make the reader want to read the second line.

Don't follow a structure. Don't have an intro, body, and conclusion. Just write something that moves.

Keep it between 400 and 550 words. Short enough to read in three minutes, long enough to say something real.

No bullet points. No subheadings. No em dashes. No "it's worth noting." No "at the end of the day." No fake statistics. No invented client stories or specific companies you claim to have observed. No phrases like "I've seen this" or "in my experience."

Pick one of these angles and write from it without announcing which one you chose:
- The quiet observer — something small that says something bigger
- The skeptic who came around — something that seemed overhyped but isn't
- The optimist with receipts — good things happening that don't get enough attention
- The honest shrug — genuine uncertainty that's interesting in itself
- The nobody talks about this angle — something overlooked in favor of shinier topics
- The human side — the people experiencing the technology, not the technology itself
- The pattern spotter — something showing up consistently that's worth naming
- The slow burn — a trend building quietly that's now hard to ignore
- The unexpected upside — a workaround that turned out to work surprisingly well
- The reality check — cutting through noise on something rarely examined closely
- The practitioner's view — what this looks like on the ground for people doing the work
- The emperor has no clothes — something widely accepted that doesn't hold up
- The uncomfortable truth — something the industry knows but rarely says
- The overpromised — pitched as transformational, delivers something more modest
- The pendulum — an idea that swung too far and is now correcting
- The gap — difference between how leadership talks about this and how employees experience it
- The long game — why something that looks like a failure might be the right call
- The fine print — the part that gets glossed over in the excitement

The focus should be on how organizations work, how services are delivered, how people experience their digital environment — not on product features or vendor news.

Return as JSON with exactly these fields:
{{
  "title": "A title that makes someone want to read this — not a command, not a lesson, just something interesting",
  "excerpt": "One sentence that captures the piece without summarizing it (under 160 chars, no double quotes inside)",
  "category": "ai-at-work or tools-tech or digital-culture or industry-news or strategy or personal",
  "readtime": 4,
  "body": "The full article in markdown, flowing prose, no subheadings unless genuinely needed, no double quotes inside the text — use single quotes instead"
}}

Return ONLY valid JSON. No preamble, no explanation, no markdown fences."""

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
        text = text.strip()
        
        # Try to parse JSON, with fallback cleaning
        try:
            article = json.loads(text)
        except json.JSONDecodeError as je:
            print(f"JSON parse error: {je}")
            print(f"Raw text (first 200 chars): {text[:200]}")
            # Try to extract fields manually if JSON is broken
            try:
                # Use a more lenient approach - ask the model to fix it
                import ast
                # Last resort: try to find and extract the body separately
                title_match = re.search(r'"title"\s*:\s*"([^"]+)"', text)
                excerpt_match = re.search(r'"excerpt"\s*:\s*"([^"]+)"', text)
                category_match = re.search(r'"category"\s*:\s*"([^"]+)"', text)
                body_start = text.find('"body"')
                if title_match and body_start > 0:
                    body_text = text[body_start+8:].strip().strip('"').strip()
                    # Remove trailing JSON
                    body_text = re.sub(r'"\s*\}?\s*$', '', body_text)
                    article = {
                        "title": title_match.group(1) if title_match else "Today in the Digital Workplace",
                        "excerpt": excerpt_match.group(1) if excerpt_match else "",
                        "category": category_match.group(1) if category_match else "ai-at-work",
                        "readtime": 5,
                        "body": body_text
                    }
                    print("Recovered article from broken JSON")
                else:
                    print("Could not recover from JSON parse error")
                    return None
            except Exception as e2:
                print(f"Recovery also failed: {e2}")
                return None

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
    
    # Clean fields to prevent YAML breakage — replace double quotes with single quotes
    def clean_yaml(text):
        return str(text).replace('"', "'").replace('\n', ' ').strip()

    title_clean = clean_yaml(article['title'])
    excerpt_clean = clean_yaml(article['excerpt'])
    category_clean = clean_yaml(article.get('category', 'ai-at-work'))

    frontmatter = f"""---
title: "{title_clean}"
date: {datetime.now(timezone.utc).isoformat()}
category: "{category_clean}"
excerpt: "{excerpt_clean}"
readtime: {article.get('readtime', 5)}
featured: true
layout: article.njk
tags:
  - digital workplace
  - {category_clean}
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

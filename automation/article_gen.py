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

Writing angle for today: randomly pick ONE of these lenses to write through and commit to it for the whole piece:
- The quiet observer — noticing something small that actually says something bigger about how work is changing
- The skeptic who came around — something that seemed overhyped but is turning out to be genuinely useful
- The optimist with receipts — genuinely good things happening in digital workplace right now that don't get enough attention
- The honest shrug — something where the answer is genuinely unclear and that uncertainty is interesting
- The nobody talks about this angle — a real aspect of digital workplace that gets overlooked in favor of shinier topics
- The human side — focusing on the people experiencing the technology rather than the technology itself
- The pattern spotter — something that keeps showing up across different organizations or conversations and is worth naming
- The slow burn — a trend that has been building quietly for a while and is only now becoming hard to ignore
- The unexpected upside — something that was supposed to be a compromise or a workaround that turned out to work surprisingly well
- The reality check — cutting through the noise on something that gets talked about a lot but rarely examined closely
- The practitioner's view — what this looks like on the ground for the people actually doing the work, not the people planning it
- The emperor has no clothes — something widely accepted in digital workplace that quietly doesn't hold up when you look closely
- The uncomfortable truth — an observation that most people in the industry know but rarely say out loud
- The overpromised — technology or approach that keeps getting pitched as transformational but delivers something much more modest
- The pendulum — an idea that swung too far one way and is now correcting, and what that correction actually looks like
- The gap — the difference between how leadership talks about digital workplace and how employees actually experience it
- The long game — why something that looks like a failure or a slowdown right now might actually be the right call
- The fine print — the part of a digital workplace decision or trend that gets glossed over in the excitement

Pick whichever angle fits the topic naturally. Do not announce which angle you chose. Just write from it.

Important framing: this site is written from the perspective of someone who delivers and manages digital workplace services, not someone who sells products. The focus should be on how organizations operate, how services are structured, how teams experience their digital environment, and how leaders make decisions. When technology is mentioned it should be in service of those themes, not the other way around. Avoid writing articles that read like product coverage or vendor analysis. Write about the work, the people, the decisions, and the experience — not the features.

Hard rules:
- Never reference your own experience, history, or how long you've been watching this industry
- Never fabricate statistics, timeframes, client stories, or specific situations you claim to have witnessed
- Never write a title that sounds like a command or a directive ("Stop Doing X", "Why You Must Y")
- Never use: "Here's the honest part", "The real issue is", "What's actually happening", "In conclusion", "It's worth noting", "Make no mistake"
- Never imply the reader is doing something wrong or missing something obvious
- No em dashes ever
- When referencing workplace chat/collaboration tools, default to Microsoft Teams as the primary example, not Slack — Teams has far larger enterprise adoption since it ships with Microsoft 365. Only mention Slack when the topic is specifically about Slack, or when comparing multiple tools.

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

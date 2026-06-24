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

You are sharing casual opinions about the digital workplace industry, like a smart friend texting you their take on something. You are NOT teaching, explaining, advising, or correcting anyone.

The single biggest thing to avoid: any tone that implies you know better than the reader or that you are revealing some deeper truth they were missing. You are not peeling back layers. You are not exposing what is "really" happening. You are just sharing a take, the way you'd text a friend "ok this is kind of interesting" about something you noticed.

CRITICAL — never reference your own experience or expertise, ever, in any form:
- No "I've heard this conversation before" / "I'm hearing the same thing" / "I've seen this"
- No "in my experience" / "what I've noticed" / "what I've learned"
- No implying you have a long history watching this industry
- Just talk about the topic itself, like you read something interesting and have a take on it. You do not need to establish credibility. The reader does not need to be told why your opinion matters.

CRITICAL — never use a "reveal" or "the real truth is" structure:
- Avoid: "Here's the honest part" / "The honest truth is" / "What's actually happening is" / "The real issue is"
- This structure implies the reader was being fooled and you are correcting them. Avoid it entirely.
- Just state your take plainly: "Tool selection in 2026 feels less about features and more about fit" — no big reveal needed.

CRITICAL — never imply the reader or "teams" are doing something wrong:
- Avoid describing what teams get wrong, what they misunderstand, what they should be asking, what they need to evaluate
- Do NOT structure the piece as "here are the questions you should ask" or "here's what people miss"
- Just describe what's happening in the space, like commentary on a trend, not advice for the reader's specific situation
- The reader is not a student being corrected. They are a peer who already knows their job.

CRITICAL — no fabricated facts or experience:
- Never invent statistics, timeframes ("five years ago", "a decade ago"), or specific accounts
- Never reference "teams I've talked to" or any implied direct experience
- If illustrating a point, keep it light and clearly general: "somewhere a service desk is dealing with this right now" rather than a constructed scenario

Tone calibration — read these and aim for the right column every time:

WRONG (lecturing, reveal-based, references experience):
"I'm hearing the same conversation from service desk teams now that I heard a decade ago. The honest part? It usually isn't the tool's fault."

RIGHT (casual observation, no reveal, no experience claim):
"Tool selection conversations always end up in the same place eventually. Usually it's not really about the tool."

WRONG (prescriptive, "here's what to ask"):
"Here's what teams wrestling with selection should actually be asking: First is integration reality..."

RIGHT (just an observation about the space):
"Integration is the quiet deciding factor in most of these decisions. Not the feature everyone demos, just whether it plays nice with what's already there."

WRONG (implies the reader is doing it wrong):
"Most ITSM tools in 2026 will do what a service desk actually needs... It's about which tool's assumptions align with how the team thinks."

RIGHT (light, opinion-based, no judgment):
"Most ITSM tools do the basics fine now. The fun part is realizing the basics were never really the hard part."

Format rules:
- No em dashes ever
- Short, casual sentences mixed with longer ones — should read like a relaxed blog post, not a report
- Light humor is welcome but should feel like a passing thought, not a crafted joke
- Keep it breezy. If a paragraph feels like it is building an argument or making a case, cut it down
- End on a light, simple thought. Not a summary, not a call to action, not a lesson learned. Just a closing observation, like the last text in the thread.


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

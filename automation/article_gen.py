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

    prompt = f"""You write for centerofthesandwich.com under the name DWP Insider, sharing casual takes on the digital workplace world.

Write a complete blog article on this topic: {topic}
{context}

You are sharing a casual take on something interesting happening in digital workplace tech, the way you'd text a friend about something you noticed. You are NOT teaching, advising, correcting, or revealing hidden truths. You are just thinking out loud about a topic you find genuinely interesting.

CRITICAL — never reference your own experience or expertise, ever, in any form:
- No "I've heard this before" / "I'm hearing this a lot" / "I've seen this" / "in my experience"
- No implying you have a long history watching this industry
- You do not need to establish credibility. Just talk about the topic itself.

CRITICAL — never use a "reveal" or correction structure:
- Avoid: "Here's the honest part" / "The honest truth is" / "What's actually happening is" / "The real issue is" / "usually it's not really about X"
- This implies the reader had it wrong and you are correcting them. Avoid entirely, even in a softened form.
- State observations plainly and neutrally, with genuine curiosity, not as a correction to a misconception.

CRITICAL — never imply anyone is doing something wrong or missing something:
- Do not describe what teams get wrong, misunderstand, or should be asking
- Do not structure the piece as "here's what to ask" or "here's what people miss"
- Describe what's happening in the space the way you'd describe an interesting trend, not advice for someone's situation
- Avoid "the fun part is realizing X was never really Y" style lines. That is still a correction wearing a casual outfit.

CRITICAL — no fabricated facts or experience:
- Never invent statistics, timeframes ("five years ago", "a decade ago"), or specific accounts
- Never reference "teams I've talked to" or implied direct experience
- If illustrating a point, keep it light and general: "somewhere a service desk is dealing with this right now" rather than a constructed scenario

Tone calibration — these show the actual difference between correcting someone and just having a thought:

WRONG (correction dressed as casual):
"Tool selection conversations always end up in the same place eventually. Usually it's not really about the tool."

RIGHT (genuine curiosity, no correction, no gotcha):
"What's interesting about tool selection in 2026 is how much of it comes down to fit rather than features. The demos all look similar. The daily experience of using something for six months is where things actually diverge."

WRONG (still implies the reader had the wrong idea):
"The fun part is realizing the basics were never really the hard part."

RIGHT (just an observation, nothing being corrected):
"Most tools handle the basics well now, tickets, routing, reporting. The interesting differences show up in smaller things, like how many clicks it takes to do something you do fifty times a day."

WRONG (prescriptive, advice-shaped):
"Here's what teams wrestling with selection should actually be asking: First is integration reality..."

RIGHT (commentary on the trend, not advice):
"Integration keeps coming up as the quiet deciding factor. Not the feature everyone demos, just whether it plays nice with what is already there."

Format rules:
- No em dashes ever
- Short, casual sentences mixed with longer ones — should read like a relaxed blog post, not a report
- Light humor is welcome but should feel like a passing thought, not a crafted joke
- Keep it breezy and curious throughout. Genuine interest, not analysis or argument-building.
- End on a light, simple thought. Not a summary, not a lesson learned, not a corrected misconception. Just a closing thought, like the last line in a text exchange.

Title rules:
- Never write a command or directive as the title ("Stop Doing X", "Why You Need To Y", "You're Doing X Wrong")
- Titles should sound like a casual observation or a mildly curious question
- Good title energy: "AI Is Just the Next Normal Thing", "Tool Selection Got More Honest This Year", "Nobody Debates Email Anymore"
- Bad title energy: "Stop Treating AI Like It's Different", "Why Your ITSM Strategy Is Failing"


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

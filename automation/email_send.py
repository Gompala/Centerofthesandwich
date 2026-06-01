import os
import json
import requests
from pathlib import Path
from datetime import datetime, timezone

# ============================================================
# CONFIGURATION
# ============================================================

BUTTONDOWN_API_KEY = os.environ.get("BUTTONDOWN_API_KEY")
BUTTONDOWN_URL = "https://api.buttondown.email/v1/emails"
POSTS_DIR = Path("_posts")
SITE_URL = "https://centerofthesandwich.com"

# ============================================================
# FUNCTIONS
# ============================================================

def get_latest_article():
    """Get the most recently generated article."""
    if not POSTS_DIR.exists():
        print("No _posts directory found")
        return None

    posts = sorted(POSTS_DIR.glob("*.md"), reverse=True)
    if not posts:
        print("No posts found")
        return None

    latest = posts[0]
    print(f"Found latest article: {latest.name}")

    content = latest.read_text()
    lines = content.split('\n')

    # Parse frontmatter
    article = {}
    in_frontmatter = False
    body_lines = []
    frontmatter_done = False
    dash_count = 0

    for line in lines:
        if line.strip() == '---':
            dash_count += 1
            if dash_count == 1:
                in_frontmatter = True
                continue
            elif dash_count == 2:
                in_frontmatter = False
                frontmatter_done = True
                continue
        if in_frontmatter:
            if ':' in line:
                key, _, val = line.partition(':')
                article[key.strip()] = val.strip().strip('"')
        elif frontmatter_done:
            body_lines.append(line)

    article['body'] = '\n'.join(body_lines).strip()
    article['filename'] = latest.stem
    return article


def build_permalink(filename):
    """Build the article URL from filename."""
    # Remove date prefix: 2026-05-23-some-slug -> some-slug
    parts = filename.split('-')
    if len(parts) > 3:
        slug = '-'.join(parts[3:])
    else:
        slug = filename
    return f"{SITE_URL}/posts/{slug}/"


def send_email(article):
    """Send the article as an email via Buttondown."""
    if not BUTTONDOWN_API_KEY:
        print("No Buttondown API key found — skipping email")
        return False

    permalink = build_permalink(article['filename'])
    title = article.get('title', 'Today on Center of the Sandwich')
    excerpt = article.get('excerpt', '')
    category = article.get('category', 'digital workplace')
    readtime = article.get('readtime', '5')

    email_body = f"""<p style="font-size:12px;color:#8BA3C7;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:16px;">CENTER OF THE SANDWICH · DAILY BRIEFING</p>

<h1 style="font-family:Georgia,serif;font-size:28px;font-weight:700;color:#0F1624;line-height:1.2;margin-bottom:16px;">{title}</h1>

<p style="font-size:15px;color:#4B6080;line-height:1.7;margin-bottom:24px;">{excerpt}</p>

<a href="{permalink}" style="display:inline-block;background:#2563EB;color:#ffffff;padding:12px 24px;border-radius:6px;font-size:14px;font-weight:600;text-decoration:none;margin-bottom:32px;">Read the full story →</a>

<hr style="border:none;border-top:1px solid #DCE8F5;margin:24px 0;">

<p style="font-size:13px;color:#8BA3C7;line-height:1.6;">This is the Center of the Sandwich daily briefing — digital workplace insights with no fluff, no filler, just the good stuff in the middle. Written by DWP Insider.</p>

<p style="font-size:12px;color:#8BA3C7;"><a href="{SITE_URL}" style="color:#2563EB;">centerofthesandwich.com</a></p>"""

    payload = {
        "subject": f"{title}",
        "body": email_body,
        "status": "about_to_send"
    }

    try:
        response = requests.post(
            BUTTONDOWN_URL,
            headers={
                "Authorization": f"Token {BUTTONDOWN_API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=30
        )
        print(f"Buttondown status: {response.status_code}")
        if response.status_code in [200, 201]:
            print(f"Email sent successfully: {title}")
            return True
        else:
            print(f"Buttondown error: {response.text}")
            return False
    except Exception as e:
        print(f"Email error: {e}")
        return False


# ============================================================
# MAIN
# ============================================================

def main():
    print(f"Starting email send at {datetime.now().isoformat()}")

    article = get_latest_article()
    if not article:
        print("No article found — skipping email")
        return

    print(f"Sending email for: {article.get('title', 'unknown')}")
    success = send_email(article)

    if success:
        print("Email sent successfully")
    else:
        print("Email send failed")


if __name__ == "__main__":
    main()

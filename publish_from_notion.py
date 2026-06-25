"""
Compliancentrix — Notion to GitHub Pages Publisher
Pulls all content with Status = "Approved" from the Review Board
and generates:
  - insights/[slug].html  (individual article page)
  - index_insights.html   (listing page with summary + Read More)
"""

import os, re, json, textwrap, requests
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
NOTION_TOKEN      = os.environ["NOTION_TOKEN"]
DATABASE_ID       = os.environ["NOTION_DATABASE_ID"]   # Review Board ID
APPROVED_STATUS   = "✅ Approved"
INSIGHTS_DIR      = "insights"
INDEX_FILE        = "index_insights.html"
SITE_URL          = "https://www.compliancentrix.com"

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

# ── Brand colours ─────────────────────────────────────────────────────────────
NAVY  = "#1B3A8C"
GOLD  = "#F5B800"
CREAM = "#F4F7FF"
WHITE = "#FFFFFF"
DARK  = "#121C3C"
GREY  = "#6B7FA3"

# ── Notion helpers ────────────────────────────────────────────────────────────
def query_approved():
    url  = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    body = {
        "filter": {
            "property": "Status",
            "status":   {"equals": APPROVED_STATUS}
        },
        "sorts": [{"property": "Date", "direction": "descending"}]
    }
    pages, cursor = [], None
    while True:
        if cursor:
            body["start_cursor"] = cursor
        r = requests.post(url, headers=HEADERS, json=body)
        r.raise_for_status()
        data = r.json()
        pages.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    return pages

def get_page_content(page_id):
    url = f"https://api.notion.com/v1/blocks/{page_id}/children?page_size=100"
    r   = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    return r.json().get("results", [])

def extract_text(rich_text):
    return "".join(t.get("plain_text", "") for t in rich_text)

def blocks_to_html(blocks):
    html = []
    for b in blocks:
        t = b.get("type", "")
        rt = b.get(t, {}).get("rich_text", [])
        text = extract_text(rt)
        if not text.strip():
            continue
        if t == "heading_1":
            html.append(f'<h1>{text}</h1>')
        elif t == "heading_2":
            html.append(f'<h2>{text}</h2>')
        elif t == "heading_3":
            html.append(f'<h3>{text}</h3>')
        elif t == "bulleted_list_item":
            html.append(f'<li>{text}</li>')
        elif t == "numbered_list_item":
            html.append(f'<li>{text}</li>')
        elif t == "paragraph":
            html.append(f'<p>{text}</p>')
        elif t == "quote":
            html.append(f'<blockquote>{text}</blockquote>')
        elif t == "divider":
            html.append('<hr>')
    return "\n".join(html)

def slugify(title):
    s = title.lower()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'\s+', '-', s.strip())
    return s[:80]

def first_200_words(html_body):
    text = re.sub(r'<[^>]+>', ' ', html_body)
    text = re.sub(r'\s+', ' ', text).strip()
    words = text.split()[:45]
    return " ".join(words) + "…"

def badge_color(content_type):
    if "News" in content_type:   return "#E74C3C"
    if "Newsletter" in content_type: return NAVY
    if "Poll" in content_type:   return "#8E44AD"
    return GREY

# ── HTML templates ────────────────────────────────────────────────────────────
ARTICLE_CSS = f"""
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: Georgia, serif; background: {CREAM}; color: {DARK}; }}
header {{
  background: {NAVY}; padding: 18px 32px;
  display: flex; align-items: center; justify-content: space-between;
  border-bottom: 4px solid {GOLD};
}}
header a {{ color: {GOLD}; text-decoration: none; font-family: Georgia, serif; font-size: 22px; font-weight: bold; }}
header nav a {{ color: #ccd6f6; font-family: sans-serif; font-size: 14px; margin-left: 24px; text-decoration: none; }}
header nav a:hover {{ color: {GOLD}; }}
.hero {{
  background: {NAVY}; color: {WHITE}; padding: 52px 32px 40px;
  border-bottom: 4px solid {GOLD};
}}
.hero .badge {{
  display: inline-block; padding: 4px 14px; border-radius: 20px;
  font-family: sans-serif; font-size: 12px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 1px; margin-bottom: 18px;
  background: {GOLD}; color: {NAVY};
}}
.hero h1 {{
  font-size: clamp(22px, 4vw, 36px); line-height: 1.3;
  color: {WHITE}; max-width: 820px; margin-bottom: 18px;
}}
.meta {{ font-family: sans-serif; font-size: 13px; color: #a0b4d8; }}
.meta span {{ margin-right: 18px; }}
article {{
  max-width: 780px; margin: 48px auto; padding: 0 24px 80px;
}}
article p {{ font-size: 17px; line-height: 1.85; margin-bottom: 20px; color: #1a2540; }}
article h2 {{ font-size: 20px; color: {NAVY}; margin: 36px 0 12px; }}
article h3 {{ font-size: 17px; color: {NAVY}; margin: 28px 0 10px; }}
article blockquote {{
  border-left: 4px solid {GOLD}; padding: 14px 20px;
  background: #eef2ff; margin: 28px 0; font-style: italic;
  color: {NAVY}; font-size: 16px; border-radius: 0 8px 8px 0;
}}
article li {{ font-size: 16px; line-height: 1.7; margin-bottom: 8px; margin-left: 20px; color: #1a2540; }}
article hr {{ border: none; border-top: 2px solid {GOLD}; margin: 36px 0; }}
.sources {{
  background: {NAVY}; color: #ccd6f6; padding: 28px 32px;
  border-radius: 10px; margin-top: 48px;
}}
.sources h4 {{ color: {GOLD}; font-family: sans-serif; font-size: 13px;
  text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 14px; }}
.sources a {{ color: #a0c4ff; font-size: 14px; display: block; margin-bottom: 8px; }}
.back-btn {{
  display: inline-block; margin-bottom: 32px;
  background: {NAVY}; color: {GOLD}; padding: 10px 22px;
  border-radius: 6px; font-family: sans-serif; font-size: 14px;
  text-decoration: none; font-weight: 600;
}}
.back-btn:hover {{ background: #0d2460; }}
footer {{
  background: {DARK}; color: #6b7fa3; text-align: center;
  padding: 28px; font-family: sans-serif; font-size: 13px;
  border-top: 3px solid {GOLD};
}}
footer a {{ color: {GOLD}; text-decoration: none; }}
"""

def article_html(title, content_type, date_str, body_html, topics, sources_html):
    slug_badge = content_type.replace("📰", "").replace("✍️", "").replace("📊","").strip()
    bc = badge_color(content_type)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} | Compliancentrix</title>
<meta name="description" content="{first_200_words(body_html)}">
<style>{ARTICLE_CSS}</style>
</head>
<body>
<header>
  <a href="/">Compliancentrix</a>
  <nav>
    <a href="/">Home</a>
    <a href="/index_insights.html">Insights</a>
    <a href="mailto:info@compliancentrix.com">Contact</a>
  </nav>
</header>

<div class="hero">
  <div class="badge" style="background:{bc};color:{'#fff' if bc != GOLD else NAVY}">{slug_badge}</div>
  <h1>{title}</h1>
  <div class="meta">
    <span>📅 {date_str}</span>
    {"<span>🏷️ " + topics + "</span>" if topics else ""}
  </div>
</div>

<article>
  <a href="/index_insights.html" class="back-btn">← Back to Insights</a>
  {body_html}

  {f'<div class="sources"><h4>Sources &amp; References</h4>{sources_html}</div>' if sources_html else ''}
</article>

<footer>
  <p>© 2026 Compliancentrix · Compliance. Simplified. Strengthened.</p>
  <p style="margin-top:8px"><a href="/">Home</a> · <a href="/index_insights.html">Insights</a> · <a href="mailto:info@compliancentrix.com">info@compliancentrix.com</a></p>
</footer>
</body>
</html>"""

INDEX_CSS = f"""
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: sans-serif; background: {CREAM}; color: {DARK}; }}
header {{
  background: {NAVY}; padding: 18px 32px;
  display: flex; align-items: center; justify-content: space-between;
  border-bottom: 4px solid {GOLD};
}}
header a.brand {{ color: {GOLD}; text-decoration: none; font-family: Georgia, serif; font-size: 22px; font-weight: bold; }}
header nav a {{ color: #ccd6f6; font-size: 14px; margin-left: 24px; text-decoration: none; }}
header nav a:hover {{ color: {GOLD}; }}
.page-hero {{
  background: {NAVY}; color: {WHITE}; padding: 52px 32px 44px;
  border-bottom: 4px solid {GOLD}; text-align: center;
}}
.page-hero h1 {{ font-family: Georgia, serif; font-size: 36px; color: {WHITE}; margin-bottom: 12px; }}
.page-hero p {{ color: #a0b4d8; font-size: 16px; }}
.grid {{
  max-width: 1100px; margin: 48px auto; padding: 0 20px;
  display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 28px;
}}
.card {{
  background: {WHITE}; border-radius: 12px; overflow: hidden;
  box-shadow: 0 2px 12px rgba(27,58,140,0.08);
  border: 1px solid #dde5f5;
  display: flex; flex-direction: column;
  transition: transform 0.2s, box-shadow 0.2s;
}}
.card:hover {{ transform: translateY(-3px); box-shadow: 0 8px 28px rgba(27,58,140,0.14); }}
.card-top {{
  background: {NAVY}; padding: 18px 20px 14px;
  border-bottom: 3px solid {GOLD};
}}
.card-top .badge {{
  display: inline-block; padding: 3px 12px; border-radius: 20px;
  font-size: 11px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 1px; margin-bottom: 10px;
  background: {GOLD}; color: {NAVY};
}}
.card-top .date {{ color: #a0b4d8; font-size: 12px; }}
.card-body {{ padding: 18px 20px; flex: 1; }}
.card-body h3 {{
  font-family: Georgia, serif; font-size: 16px; color: {NAVY};
  line-height: 1.45; margin-bottom: 12px;
}}
.card-body p {{ font-size: 14px; color: #3a4a6b; line-height: 1.65; }}
.card-footer {{ padding: 14px 20px; border-top: 1px solid #eef1fb; }}
.read-more {{
  display: inline-block; color: {NAVY}; font-weight: 700;
  font-size: 13px; text-decoration: none;
  border-bottom: 2px solid {GOLD}; padding-bottom: 1px;
}}
.read-more:hover {{ color: {GOLD}; border-color: {NAVY}; }}
.topics {{ font-size: 11px; color: {GREY}; margin-top: 8px; }}
footer {{
  background: {DARK}; color: #6b7fa3; text-align: center;
  padding: 28px; font-size: 13px; border-top: 3px solid {GOLD};
  margin-top: 60px;
}}
footer a {{ color: {GOLD}; text-decoration: none; }}
"""

def index_html(cards_html):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Compliance Insights | Compliancentrix</title>
<meta name="description" content="Daily compliance intelligence from India and beyond — AML, anti-corruption, enforcement, regulatory updates.">
<style>{INDEX_CSS}</style>
</head>
<body>
<header>
  <a class="brand" href="/">Compliancentrix</a>
  <nav>
    <a href="/">Home</a>
    <a href="/index_insights.html">Insights</a>
    <a href="mailto:info@compliancentrix.com">Contact</a>
  </nav>
</header>

<div class="page-hero">
  <h1>Compliance Insights</h1>
  <p>Daily intelligence on enforcement, regulation and financial crime from India and beyond.</p>
</div>

<div class="grid">
{cards_html}
</div>

<footer>
  <p>© 2026 Compliancentrix · Compliance. Simplified. Strengthened.</p>
  <p style="margin-top:8px">
    <a href="/">Home</a> ·
    <a href="mailto:info@compliancentrix.com">info@compliancentrix.com</a>
  </p>
</footer>
</body>
</html>"""

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    os.makedirs(INSIGHTS_DIR, exist_ok=True)
    pages  = query_approved()
    cards  = []
    slugs_seen = set()

    for page in pages:
        props = page.get("properties", {})

        # Title
        title_arr = props.get("Title", {}).get("title", [])
        title = extract_text(title_arr).strip()
        if not title:
            continue

        # Content type
        ct_obj = props.get("Content Type", {})
        content_type = ct_obj.get("select", {}).get("name", "") if ct_obj else ""

        # Date
        date_obj = props.get("Date", {}).get("date", {})
        date_raw = date_obj.get("start", "") if date_obj else ""
        try:
            dt = datetime.strptime(date_raw, "%Y-%m-%d")
            date_str = dt.strftime("%d %B %Y")
        except:
            date_str = date_raw

        # Topics
        topics_arr = props.get("Topics", {}).get("rich_text", [])
        topics = extract_text(topics_arr)

        # Page body
        blocks    = get_page_content(page["id"])
        body_html = blocks_to_html(blocks)

        # Extract sources section (last <p> blocks after "Sources")
        sources_html = ""
        src_match = re.search(r'(?:Sources|References)[^\n]*\n(.*?)$', body_html, re.DOTALL | re.IGNORECASE)
        if src_match:
            raw = src_match.group(1)
            # Convert numbered URLs to links
            raw = re.sub(r'(https?://\S+)', r'<a href="\1" target="_blank">\1</a>', raw)
            sources_html = raw

        # Slug
        base_slug = slugify(title)
        slug = base_slug
        i = 2
        while slug in slugs_seen:
            slug = f"{base_slug}-{i}"; i += 1
        slugs_seen.add(slug)

        # Write article page
        html = article_html(title, content_type, date_str, body_html, topics, sources_html)
        path = os.path.join(INSIGHTS_DIR, f"{slug}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)

        # Build card for index
        summary = first_200_words(body_html)
        badge_label = content_type.replace("📰","").replace("✍️","").replace("📊","").strip()
        bc = badge_color(content_type)
        badge_style = f"background:{bc};color:{'#fff' if bc != GOLD else NAVY}"
        card = f"""
  <div class="card">
    <div class="card-top">
      <div class="badge" style="{badge_style}">{badge_label}</div>
      <div class="date">{date_str}</div>
    </div>
    <div class="card-body">
      <h3>{title}</h3>
      <p>{summary}</p>
      {"<div class='topics'>🏷️ " + topics + "</div>" if topics else ""}
    </div>
    <div class="card-footer">
      <a class="read-more" href="/insights/{slug}.html">Read full story →</a>
    </div>
  </div>"""
        cards.append(card)

    # Write index
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        f.write(index_html("\n".join(cards)))

    print(f"✅ Published {len(pages)} articles → {INSIGHTS_DIR}/ + {INDEX_FILE}")

if __name__ == "__main__":
    main()

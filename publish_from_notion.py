"""
Compliancentrix — Notion to GitHub Pages Publisher
Uses Notion Search API (no database-specific permission needed)
"""

import os, re, requests
from datetime import datetime

NOTION_TOKEN  = os.environ["NOTION_TOKEN"]
APPROVED      = "Approved"
INSIGHTS_DIR  = "insights"
INDEX_FILE    = "index_insights.html"

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type":   "application/json",
}

NAVY  = "#1B3A8C"
GOLD  = "#F5B800"
CREAM = "#F4F7FF"
WHITE = "#FFFFFF"
DARK  = "#121C3C"
GREY  = "#6B7FA3"

# ── Notion API ────────────────────────────────────────────────────────────────

def search_approved_pages():
    """Use search API — works with any token that has workspace access"""
    url   = "https://api.notion.com/v1/search"
    pages = []
    cursor = None

    while True:
        body = {
            "filter": {"value": "page", "property": "object"},
            "page_size": 100,
            "sort": {"direction": "descending", "timestamp": "last_edited_time"}
        }
        if cursor:
            body["start_cursor"] = cursor

        r = requests.post(url, headers=HEADERS, json=body)
        r.raise_for_status()
        data = r.json()

        for item in data.get("results", []):
            props = item.get("properties", {})
            # Check if Status = Approved
            status_prop = props.get("Status", {})
            status_val  = ""
            if status_prop.get("type") == "status":
                sv = status_prop.get("status") or {}
                status_val = sv.get("name", "")
            elif status_prop.get("type") == "select":
                sv = status_prop.get("select") or {}
                status_val = sv.get("name", "")

            if APPROVED.lower() in status_val.lower():
                pages.append(item)

        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")

    return pages


def get_blocks(page_id):
    url = f"https://api.notion.com/v1/blocks/{page_id}/children?page_size=100"
    r   = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    return r.json().get("results", [])


def rich_text(arr):
    return "".join(t.get("plain_text", "") for t in arr)


def blocks_to_html(blocks):
    html = []
    for b in blocks:
        t    = b.get("type", "")
        data = b.get(t, {})
        rt   = data.get("rich_text", [])
        text = rich_text(rt)
        if not text.strip():
            continue
        if   t == "heading_1":             html.append(f"<h2>{text}</h2>")
        elif t == "heading_2":             html.append(f"<h2>{text}</h2>")
        elif t == "heading_3":             html.append(f"<h3>{text}</h3>")
        elif t == "paragraph":             html.append(f"<p>{text}</p>")
        elif t == "quote":                 html.append(f"<blockquote>{text}</blockquote>")
        elif t == "divider":               html.append("<hr>")
        elif t in ("bulleted_list_item",
                   "numbered_list_item"):  html.append(f"<li>{text}</li>")
    return "\n".join(html)


def extract_prop(props, key, prop_type="title"):
    p = props.get(key, {})
    if prop_type == "title":
        return rich_text(p.get("title", []))
    if prop_type == "rich_text":
        return rich_text(p.get("rich_text", []))
    if prop_type == "select":
        s = p.get("select") or {}
        return s.get("name", "")
    if prop_type == "date":
        d = p.get("date") or {}
        return d.get("start", "")
    return ""


def slugify(title):
    s = title.lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s.strip())
    return s[:80]


def summary(html_body, n=45):
    text  = re.sub(r"<[^>]+>", " ", html_body)
    text  = re.sub(r"\s+", " ", text).strip()
    words = text.split()[:n]
    return " ".join(words) + "…"


def badge_color(ct):
    if "News"       in ct: return "#E74C3C"
    if "Newsletter" in ct: return NAVY
    if "Poll"       in ct: return "#8E44AD"
    return GREY

# ── HTML ──────────────────────────────────────────────────────────────────────

CSS_ARTICLE = f"""
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:Georgia,serif;background:{CREAM};color:{DARK}}}
header{{background:{NAVY};padding:18px 32px;display:flex;align-items:center;
  justify-content:space-between;border-bottom:4px solid {GOLD}}}
header a{{color:{GOLD};text-decoration:none;font-size:22px;font-weight:bold}}
header nav a{{color:#ccd6f6;font-family:sans-serif;font-size:14px;
  margin-left:24px;text-decoration:none}}
header nav a:hover{{color:{GOLD}}}
.hero{{background:{NAVY};color:{WHITE};padding:52px 32px 40px;
  border-bottom:4px solid {GOLD}}}
.badge{{display:inline-block;padding:4px 14px;border-radius:20px;
  font-family:sans-serif;font-size:12px;font-weight:700;
  text-transform:uppercase;letter-spacing:1px;margin-bottom:18px}}
.hero h1{{font-size:clamp(22px,4vw,36px);line-height:1.3;
  color:{WHITE};max-width:820px;margin-bottom:18px}}
.meta{{font-family:sans-serif;font-size:13px;color:#a0b4d8}}
.meta span{{margin-right:18px}}
article{{max-width:780px;margin:48px auto;padding:0 24px 80px}}
article p{{font-size:17px;line-height:1.85;margin-bottom:20px;color:#1a2540}}
article h2{{font-size:20px;color:{NAVY};margin:36px 0 12px}}
article h3{{font-size:17px;color:{NAVY};margin:28px 0 10px}}
article blockquote{{border-left:4px solid {GOLD};padding:14px 20px;
  background:#eef2ff;margin:28px 0;font-style:italic;
  color:{NAVY};font-size:16px;border-radius:0 8px 8px 0}}
article li{{font-size:16px;line-height:1.7;margin-bottom:8px;
  margin-left:20px;color:#1a2540}}
article hr{{border:none;border-top:2px solid {GOLD};margin:36px 0}}
.back-btn{{display:inline-block;margin-bottom:32px;background:{NAVY};
  color:{GOLD};padding:10px 22px;border-radius:6px;font-family:sans-serif;
  font-size:14px;text-decoration:none;font-weight:600}}
footer{{background:{DARK};color:#6b7fa3;text-align:center;
  padding:28px;font-family:sans-serif;font-size:13px;
  border-top:3px solid {GOLD}}}
footer a{{color:{GOLD};text-decoration:none}}
"""

CSS_INDEX = f"""
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:sans-serif;background:{CREAM};color:{DARK}}}
header{{background:{NAVY};padding:18px 32px;display:flex;align-items:center;
  justify-content:space-between;border-bottom:4px solid {GOLD}}}
header a.brand{{color:{GOLD};text-decoration:none;font-family:Georgia,serif;
  font-size:22px;font-weight:bold}}
header nav a{{color:#ccd6f6;font-size:14px;margin-left:24px;text-decoration:none}}
header nav a:hover{{color:{GOLD}}}
.hero{{background:{NAVY};color:{WHITE};padding:52px 32px 44px;
  border-bottom:4px solid {GOLD};text-align:center}}
.hero h1{{font-family:Georgia,serif;font-size:36px;margin-bottom:12px}}
.hero p{{color:#a0b4d8;font-size:16px}}
.grid{{max-width:1100px;margin:48px auto;padding:0 20px;
  display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:28px}}
.card{{background:{WHITE};border-radius:12px;overflow:hidden;
  box-shadow:0 2px 12px rgba(27,58,140,.08);border:1px solid #dde5f5;
  display:flex;flex-direction:column;transition:transform .2s,box-shadow .2s}}
.card:hover{{transform:translateY(-3px);box-shadow:0 8px 28px rgba(27,58,140,.14)}}
.card-top{{background:{NAVY};padding:18px 20px 14px;border-bottom:3px solid {GOLD}}}
.badge{{display:inline-block;padding:3px 12px;border-radius:20px;
  font-size:11px;font-weight:700;text-transform:uppercase;
  letter-spacing:1px;margin-bottom:10px;background:{GOLD};color:{NAVY}}}
.date{{color:#a0b4d8;font-size:12px}}
.card-body{{padding:18px 20px;flex:1}}
.card-body h3{{font-family:Georgia,serif;font-size:16px;color:{NAVY};
  line-height:1.45;margin-bottom:12px}}
.card-body p{{font-size:14px;color:#3a4a6b;line-height:1.65}}
.card-footer{{padding:14px 20px;border-top:1px solid #eef1fb}}
.read-more{{display:inline-block;color:{NAVY};font-weight:700;
  font-size:13px;text-decoration:none;border-bottom:2px solid {GOLD};padding-bottom:1px}}
.read-more:hover{{color:{GOLD};border-color:{NAVY}}}
footer{{background:{DARK};color:#6b7fa3;text-align:center;
  padding:28px;font-size:13px;border-top:3px solid {GOLD};margin-top:60px}}
footer a{{color:{GOLD};text-decoration:none}}
"""

def make_article(title, ct, date_str, body, topics):
    bl     = ct.replace("📰","").replace("✍️","").replace("📊","").strip()
    bc     = badge_color(ct)
    btc    = "#fff" if bc != GOLD else NAVY
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title} | Compliancentrix</title>
<meta name="description" content="{summary(body)}">
<style>{CSS_ARTICLE}</style>
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
  <div class="badge" style="background:{bc};color:{btc}">{bl}</div>
  <h1>{title}</h1>
  <div class="meta">
    <span>📅 {date_str}</span>
    {"<span>🏷️ " + topics + "</span>" if topics else ""}
  </div>
</div>
<article>
  <a href="/index_insights.html" class="back-btn">← Back to Insights</a>
  {body}
</article>
<footer>
  <p>© 2026 Compliancentrix · Compliance. Simplified. Strengthened.</p>
  <p style="margin-top:8px">
    <a href="/">Home</a> · <a href="/index_insights.html">Insights</a> ·
    <a href="mailto:info@compliancentrix.com">info@compliancentrix.com</a>
  </p>
</footer>
</body></html>"""


def make_index(cards):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Compliance Insights | Compliancentrix</title>
<style>{CSS_INDEX}</style>
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
<div class="hero">
  <h1>Compliance Insights</h1>
  <p>Daily intelligence on enforcement, regulation and financial crime from India and beyond.</p>
</div>
<div class="grid">{"".join(cards)}</div>
<footer>
  <p>© 2026 Compliancentrix · Compliance. Simplified. Strengthened.</p>
  <p style="margin-top:8px">
    <a href="/">Home</a> ·
    <a href="mailto:info@compliancentrix.com">info@compliancentrix.com</a>
  </p>
</footer>
</body></html>"""

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(INSIGHTS_DIR, exist_ok=True)
    pages      = search_approved_pages()
    cards      = []
    seen_slugs = set()

    print(f"Found {len(pages)} approved pages")

    for page in pages:
        props = page.get("properties", {})

        title = extract_prop(props, "Title", "title")
        if not title:
            title = extract_prop(props, "Name", "title")
        if not title:
            continue

        ct       = extract_prop(props, "Content Type", "select")
        date_raw = extract_prop(props, "Date", "date")
        topics   = extract_prop(props, "Topics", "rich_text")

        try:
            date_str = datetime.strptime(date_raw, "%Y-%m-%d").strftime("%d %B %Y")
        except:
            date_str = date_raw or ""

        blocks = get_blocks(page["id"])
        body   = blocks_to_html(blocks)

        base = slugify(title)
        slug = base
        i    = 2
        while slug in seen_slugs:
            slug = f"{base}-{i}"; i += 1
        seen_slugs.add(slug)

        html = make_article(title, ct, date_str, body, topics)
        with open(f"{INSIGHTS_DIR}/{slug}.html", "w", encoding="utf-8") as f:
            f.write(html)

        bl  = ct.replace("📰","").replace("✍️","").replace("📊","").strip()
        bc  = badge_color(ct)
        btc = "#fff" if bc != GOLD else NAVY
        sm  = summary(body)

        cards.append(f"""
  <div class="card">
    <div class="card-top">
      <div class="badge" style="background:{bc};color:{btc}">{bl}</div>
      <div class="date">{date_str}</div>
    </div>
    <div class="card-body">
      <h3>{title}</h3>
      <p>{sm}</p>
    </div>
    <div class="card-footer">
      <a class="read-more" href="/insights/{slug}.html">Read full story →</a>
    </div>
  </div>""")

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        f.write(make_index(cards))

    print(f"Done — {len(cards)} articles published")

if __name__ == "__main__":
    main()

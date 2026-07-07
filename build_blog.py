#!/usr/bin/env python3
"""Generate the Radiance Labs blog from the SGS repo's LinkedIn posts.

Reads post source files from the sibling `sgs` repo, copies their images into
`blog/assets/`, and emits a static blog that matches the design of index.html:

    blog/index.html               the blog homepage (reverse-chronological feed)
    blog/<slug>/index.html        one detail page per post

Re-run any time the source posts change:  python3 build_blog.py
"""

import html
import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
SGS = HERE.parent / "sgs"
BLOG = HERE / "blog"
ASSETS = BLOG / "assets"

# ── Post registry ──────────────────────────────────────────────────────────
# Each post: source file (relative to sgs/), curated title, date (git first
# commit), an intra-day sequence (reading order; higher = later = higher on the
# feed), an optional collection-section marker, and its images (basename +
# caption). Sort is (date, seq) descending so the latest sits on top.

def img(name, cap=""):
    return {"name": name, "caption": cap}

POSTS = [
    # ── 2026-04-23  Klang audio series (came before Planck in the thread) ──
    {
        "src": "docs/klang/linkedin_posts.md", "section": "Post 1",
        "title": "Klang Variant A: an audio track for Semantic Gaussian Splatting",
        "date": "2026-04-23", "seq": 1,
        "images": [
            img("post-1-1_variant-a_reconstruction.png", "Target vs rendered spectrogram at 1000 Gaussians."),
            img("post-1-2_variant-a_gaussian-positions.png", "Where the Gaussians land in time-frequency."),
            img("post-1-3_variant-a_loss-curve.png", "Convergence curve."),
        ],
    },
    {
        "src": "docs/klang/linkedin_posts.md", "section": "Post 2",
        "title": "Klang Variant B: Gaussians as sound layers",
        "date": "2026-04-23", "seq": 2,
        "images": [
            img("post-2-1_variant-b_20L_trajectories.png", "Layer frequency trajectories (headline shot)."),
            img("post-2-2_variant-b_20L_reconstruction.png", "Target vs rendered vs error."),
            img("post-2-3_variant-b_20L_opacity.png", "Per-layer opacity envelopes."),
            img("post-2-4_variant-b_10L_trajectories_optional.png", "Contrast with 10 layers."),
            img("post-2-5_variant-b_40L_trajectories_optional.png", "Contrast with 40 layers: the failure mode is identical across depths."),
        ],
    },
    {
        "src": "docs/klang/linkedin_posts.md", "section": "Post 3",
        "title": "Klang 1.2: turning two failures into a specification",
        "date": "2026-04-23", "seq": 3,
        "images": [],
    },
    # ── 2026-04-23  Planck 1.1 blob series ──
    {
        "src": "docs/planck/linkedin_posts.md", "section": "Post 1",
        "title": "The blob concept, and why the architecture is already a RAG",
        "date": "2026-04-23", "seq": 4,
        "images": [img("post-1-1_architecture.png", "H-SGS architecture: base forward pass plus parallel blob retrieval plus learned gate.")],
    },
    {
        "src": "docs/planck/linkedin_posts.md", "section": "Post 2",
        "title": "Planck 1.1: what we were trying to prove",
        "date": "2026-04-23", "seq": 5,
        "images": [img("post-2-1_gates.png", "The four-gate validator: what each gate tests and its pass condition.")],
    },
    {
        "src": "docs/planck/linkedin_posts.md", "section": "Post 3",
        "title": "Planck 1.1: preliminary results",
        "date": "2026-04-23", "seq": 6,
        "images": [img("post-3-1_gate_2_3_pass.png", "Validation loss, perplexity (5.76 to 5.30), and mean effective blob weight (0.059) vs the 0.05 floor.")],
    },
    {
        "src": "docs/planck/linkedin_posts.md", "section": "Post 4",
        "title": "Gate results and the Planck 1.3 plan",
        "date": "2026-04-23", "seq": 7,
        "images": [
            img("post-4-1_gate_4a_fail.png", "Intra-sample 4-gram repeats per sample: Planck 1.0 = 5.16 vs Planck 1.1 = 8.34 (+62%)."),
            img("post-4-2_gate_4b_weak_upside.png", "Cross-sample diversity: the direction is right but the magnitude is small."),
            img("post-4-3_planck13_roadmap.png", "The five-item Planck 1.3 plan, ordered by cost."),
        ],
    },
    # ── 2026-04-27  Raum 3D series ──
    {
        "src": "docs/raum/linkedin_posts.md", "section": "Post 1",
        "title": "Raum, the 3D idea",
        "date": "2026-04-27", "seq": 1,
        "images": [img("post-1-1_core_idea.png", "Raum 0.0 core idea: a sentence in, a Gaussian cloud out.")],
    },
    {
        "src": "docs/raum/linkedin_posts.md", "section": "Post 2",
        "title": "How Raum 0.0 is built",
        "date": "2026-04-27", "seq": 2,
        "images": [img("post-2-1_architecture.png", "Raum 0.0 architecture: a three-stage bridge, template library, and WebGL renderer.")],
    },
    {
        "src": "docs/raum/linkedin_posts.md", "section": "Post 3",
        "title": "Raum 0.0 results, and the path to 0.1",
        "date": "2026-04-27", "seq": 3,
        "images": [],
    },
    # ── 2026-05-21  Blobs conceptual trio ──
    {
        "src": "docs/posts/linkedin_blobs_intro.md",
        "title": "What is a Blob? Chunked meaning as a first-class primitive",
        "date": "2026-05-21", "seq": 1,
        "images": [img("blobs_intro.svg", "Blobs are stored offline, retrieved by cosine similarity, and rendered with word tokens in one alpha-compositing pass.")],
    },
    {
        "src": "docs/posts/linkedin_needle_results.md",
        "title": "First results: conversation memory via blobs (Planck 1.4)",
        "date": "2026-05-21", "seq": 2,
        "images": [img("needle_experiment.svg", "Needle-in-a-haystack: a fact planted at turn 10, retrieved at turn 100.")],
    },
    {
        "src": "docs/posts/linkedin_blobs_vs_multitoken.md",
        "title": "Blobs and multi-token prediction: two sides of the same coin",
        "date": "2026-05-21", "seq": 3,
        "images": [img("blobs_vs_multitoken.svg", "Multi-token prediction amortizes output steps; blob retrieval amortizes input processing.")],
    },
    # ── 2026-06-01  Raum 1.4 article + 0.5 follow-up ──
    {
        "src": "docs/raum/linkedin_article_raum_14.md",
        "title": "A castle made of the wrong-sized boxes: what Raum 1.4 taught us about fidelity",
        "date": "2026-06-01", "seq": 1,
        "images": [],
    },
    {
        "src": "docs/raum/linkedin_post_raum_05.md",
        "title": "Raum 0.5: the fix worked",
        "date": "2026-06-01", "seq": 2,
        "images": [],
    },
    # ── 2026-06-04 ──
    {
        "src": "docs/raum/linkedin_post_raum_16.md",
        "title": "Raum 1.6 / 0.6: a castle from a sentence",
        "date": "2026-06-04", "seq": 1,
        "images": [],
    },
    # ── 2026-06-09 ──
    {
        "src": "docs/raum/linkedin_post_raum_17.md",
        "title": "Raum 1.7: the model learns to place the castle",
        "date": "2026-06-09", "seq": 1,
        "images": [],
    },
    # ── 2026-06-24  VSP working notes ──
    {
        "src": "docs/posts/vsp_post1_idea.md",
        "title": "The VSP idea: why a token should be more than a word",
        "date": "2026-06-24", "seq": 1,
        "images": [img("vsp_token.svg", "A grounded token carries visual (V), semantic (S), and physical (P) parts.")],
    },
    {
        "src": "docs/posts/vsp_post2_method.md",
        "title": "The VSP method: four experiments, one decision",
        "date": "2026-06-24", "seq": 2,
        "images": [img("vsp_grounding.svg", "Four ways to build the visual grounding, and which ones cheat.")],
    },
    # ── 2026-07-06  Hertz + the polished path/VSP series ──
    {
        "src": "docs/raum/linkedin_post_hertz_paste.txt",
        "title": "We trained a 0.64B language model on a new architecture",
        "date": "2026-07-06", "seq": 1,
        "images": [],
    },
    {
        "src": "docs/raum/linkedin_post_path1_paste.txt",
        "title": "A negative result worth keeping: when a task is saturated, scale buys nothing",
        "date": "2026-07-06", "seq": 2,
        "images": [img("post_path1_illustration.png", "Bigger model, learned fill: neither beat the small model on a saturated task.")],
    },
    {
        "src": "docs/raum/linkedin_post_path2_paste.txt",
        "title": "Fixing word-sense at the representation, before the model",
        "date": "2026-07-06", "seq": 3,
        "images": [img("post_path2_illustration.png", "Five ways to build a visual grounding; only honestly-derived generated images separate the senses.")],
    },
    {
        "src": "docs/raum/linkedin_post_path3_paste.txt",
        "title": "A tokenizer that decides what a word means before the model reads it",
        "date": "2026-07-06", "seq": 4,
        "images": [img("post_path3_illustration.png", "One token per sense: crane-bird and crane-machine become distinct, grounded tokens.")],
    },
    {
        "src": "docs/raum/linkedin_post_vsp_paste.txt",
        "title": "Grounding tokens in vision and physics to split word senses",
        "date": "2026-07-06", "seq": 5,
        "images": [img("vsp_gating_illustration.png", "Text alone: separation 0.13. Add automatic visual + physical grounding: 0.37.")],
    },
]

# Where each image basename lives inside the sgs repo.
IMAGE_DIRS = [
    "docs/planck/planck-posts",
    "docs/klang/klang-posts",
    "docs/raum/raum-posts",
    "docs/raum",
    "docs/posts/img",
]

# ── Markdown-ish rendering ───────────────────────────────────────────────────

MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]

def pretty_date(iso):
    y, m, d = (int(x) for x in iso.split("-"))
    return f"{MONTHS[m-1]} {d}, {y}"

def slugify(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")

def make_slug(post):
    src = Path(post["src"])
    stem = src.stem                          # e.g. linkedin_post_raum_17
    base = slugify(stem)
    if "section" in post:                    # collection: prefix track + part
        track = src.parent.name              # klang / planck / raum
        n = post["section"].split()[-1]
        base = f"{slugify(track)}-{base}-part-{n}"
    return f"{base}-{post['date']}"

SKIP_MARKERS = ("tone note", "tone:", "illustration:")

def is_skippable(block):
    low = block.strip().lower()
    if not low:
        return True
    if low.startswith("#") and not low.startswith("##"):
        return True                          # H1 title line (we supply titles)
    if low.startswith(SKIP_MARKERS):
        return True
    if "no em dashes" in low:                # internal tone/style notes
        return True
    if low in ("nikita gorshkov / radiance labs", "nikita gorshkov", "radiance labs"):
        return True
    if low.startswith("*part of the"):        # file-level series annotation
        return True
    if low.endswith("in the comments.") or low.endswith("in the comments"):
        return True
    return False

def inline(text):
    """Escape then apply **bold** and *italic*."""
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", text)
    return text

def render_body(raw):
    """Turn a post's raw text into HTML paragraphs, headings, lists, code."""
    # Drop leading title/tone chatter up to the first horizontal rule when one
    # exists (standalone .md files fence their real body after a `---`).
    lines = raw.replace("\r\n", "\n").split("\n")

    out = []
    i = 0
    n = len(lines)
    list_buf = []
    list_kind = None

    def flush_list():
        nonlocal list_buf, list_kind
        if list_buf:
            tag = list_kind
            items = "".join(f"<li>{inline(x)}</li>" for x in list_buf)
            out.append(f"<{tag}>{items}</{tag}>")
            list_buf = []
            list_kind = None

    para = []

    def flush_para():
        if para:
            block = "\n".join(para).strip()
            para.clear()
            if not is_skippable(block):
                out.append(f"<p>{inline(block)}</p>")

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # fenced code block
        if stripped.startswith("```"):
            flush_para(); flush_list()
            code = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1  # skip closing fence
            out.append("<pre><code>" + html.escape("\n".join(code)) + "</code></pre>")
            continue

        # horizontal rule / separator
        if stripped == "---":
            flush_para(); flush_list()
            i += 1
            continue

        # inline image markdown -> handled separately, drop here
        if re.match(r"!\[.*\]\(.*\)", stripped):
            flush_para(); flush_list()
            i += 1
            continue

        # headings
        m = re.match(r"^(#{2,3})\s+(.*)", stripped)
        if m:
            flush_para(); flush_list()
            # a "## Post N. Title" marker inside a collection is the section
            # heading; skip it (title supplied). Other ## are real subheads.
            if re.match(r"post\s+\d", m.group(2), re.I):
                i += 1
                continue
            level = len(m.group(1))
            out.append(f"<h{level}>{inline(m.group(2))}</h{level}>")
            i += 1
            continue

        # klang collection: an "**Images...**" trailing block ends the post
        if stripped.lower().startswith("**images"):
            flush_para(); flush_list()
            break

        # list items
        ul = re.match(r"^[-*]\s+(.*)", stripped)
        ol = re.match(r"^\d+\.\s+(.*)", stripped)
        if ul or ol:
            flush_para()
            kind = "ul" if ul else "ol"
            if list_kind and list_kind != kind:
                flush_list()
            list_kind = kind
            list_buf.append((ul or ol).group(1))
            i += 1
            continue

        # blank line -> paragraph break
        if stripped == "":
            flush_para(); flush_list()
            i += 1
            continue

        # continuation of a list item wrapped onto the next line
        if list_buf and not (ul or ol):
            list_buf[-1] += " " + stripped
            i += 1
            continue

        para.append(stripped)
        i += 1

    flush_para(); flush_list()
    return "\n".join(out)

def extract_section(raw, section):
    """Pull one '## Post N ...' section out of a collection file."""
    parts = re.split(r"\n---\n", raw)
    target = None
    num = section.split()[-1]
    for chunk in parts:
        m = re.search(r"^##\s*Post\s+(\d+)", chunk.strip(), re.I | re.M)
        if m and m.group(1) == num:
            target = chunk
            break
    return target if target is not None else raw

BOILERPLATE = re.compile(r"^(continuing the sgs|\*?part of the)", re.I)

def first_sentence_excerpt(body_html, limit=200):
    """Plain-text excerpt from the first substantive paragraph, with an ellipsis."""
    paras = re.findall(r"<p>(.*?)</p>", body_html, re.S)
    text = ""
    for raw in paras:
        cand = html.unescape(re.sub(r"<[^>]+>", "", raw)).strip()
        # skip the stock "Continuing the SGS series." opener used across the thread
        if BOILERPLATE.match(cand) or len(cand) < 40:
            continue
        text = cand
        break
    if not text and paras:
        text = re.sub(r"<[^>]+>", "", paras[0])
    text = html.unescape(text).strip().replace("\n", " ")
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0]
    return text.rstrip(",.;: ") + " ..."

# ── Page templates ───────────────────────────────────────────────────────────

STYLE = """
:root{
  --bg:#0a0a0f;--panel:#12121a;--ink:#f5f1e8;--ink-dim:#8a8598;
  --accent:#ffb347;--accent-coral:#ff6b6b;--border:#1f1f2a;--green:#4ade80;
}
*{box-sizing:border-box;margin:0;padding:0;}
html,body{background:var(--bg);color:var(--ink);scroll-behavior:smooth;}
body{font-family:"Source Serif 4",Georgia,serif;font-size:17px;line-height:1.65;-webkit-font-smoothing:antialiased;}
h1,h2,h3,.brand-name,.header-brand-name,nav a,.eyebrow,.tag,.post-date,.back-link{font-family:"Inter",-apple-system,sans-serif;}
a{color:var(--accent);text-decoration:none;}
a:hover{color:var(--accent-coral);}

.site-header{position:fixed;top:0;left:0;right:0;z-index:1000;background:rgba(10,10,15,.9);backdrop-filter:blur(12px);border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;padding:12px 28px;}
.header-brand{display:flex;align-items:center;gap:10px;}
.header-brand-name{font-size:13px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--ink);}
.header-nav{display:flex;gap:22px;list-style:none;}
.header-nav a{font-size:12px;color:var(--ink-dim);letter-spacing:.05em;text-transform:uppercase;transition:color .2s;}
.header-nav a:hover{color:var(--accent);}
@media(max-width:700px){.header-nav{display:none;}}
.logo-svg{flex-shrink:0;}

section{max-width:920px;margin:0 auto;padding:72px 28px;}
.eyebrow{font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:var(--accent);margin-bottom:14px;font-weight:600;}
h2{font-size:30px;font-weight:600;letter-spacing:-.01em;margin-bottom:10px;}
section > p.lead{color:var(--ink-dim);max-width:680px;margin-bottom:40px;}

.blog-top{padding-top:104px;}

/* feed */
.feed{display:flex;flex-direction:column;gap:16px;}
.post-card{display:block;background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:24px 26px;transition:border-color .2s,transform .2s;}
.post-card:hover{border-color:var(--accent);transform:translateY(-2px);}
.post-card .post-date{font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--accent);margin-bottom:8px;}
.post-card h3{font-family:"Inter",sans-serif;font-size:20px;font-weight:600;color:var(--ink);line-height:1.3;margin-bottom:8px;}
.post-card p{font-size:16px;color:var(--ink-dim);line-height:1.55;}
.post-card .arrow{color:var(--accent);font-family:"Inter",sans-serif;font-size:13px;font-weight:600;margin-top:12px;display:inline-block;}

.year-label{font-family:"Inter",sans-serif;font-size:12px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-dim);margin:28px 0 4px;display:flex;align-items:center;gap:12px;}
.year-label::after{content:"";flex:1;height:1px;background:var(--border);}
.year-label:first-child{margin-top:0;}

/* detail */
.back-link{display:inline-block;font-size:12px;letter-spacing:.05em;text-transform:uppercase;color:var(--ink-dim);margin-bottom:28px;transition:color .2s;}
.back-link:hover{color:var(--accent);}
article .post-date{font-family:"Inter",sans-serif;font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--accent);margin-bottom:12px;}
article h1{font-family:"Inter",sans-serif;font-size:38px;line-height:1.15;font-weight:700;letter-spacing:-.02em;margin-bottom:14px;}
@media(max-width:700px){article h1{font-size:28px;}}
article .byline{color:var(--ink-dim);font-size:14px;margin-bottom:40px;padding-bottom:24px;border-bottom:1px solid var(--border);}
article h2{font-size:24px;margin:40px 0 12px;}
article h3{font-family:"Inter",sans-serif;font-size:18px;font-weight:600;margin:32px 0 10px;}
article p{margin-bottom:18px;}
article ul,article ol{margin:0 0 18px 24px;}
article li{margin-bottom:8px;}
article strong{color:var(--ink);}
article pre{background:#0d0d14;border:1px solid var(--border);border-radius:10px;padding:18px 20px;overflow-x:auto;margin-bottom:22px;}
article pre code{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:13px;line-height:1.5;color:var(--ink-dim);white-space:pre;}
article figure{margin:28px 0;border:1px solid var(--border);border-radius:12px;overflow:hidden;background:#000;}
article figure img{display:block;width:100%;height:auto;}
article figure figcaption{font-family:"Inter",sans-serif;font-size:12px;color:var(--ink-dim);padding:10px 16px;border-top:1px solid var(--border);}

footer{max-width:920px;margin:0 auto;padding:56px 28px 80px;color:var(--ink-dim);font-size:15px;border-top:1px solid var(--border);}
footer .row{display:flex;flex-wrap:wrap;gap:8px 28px;align-items:center;}
footer .heart{color:var(--accent-coral);}
footer a{font-family:"Inter",sans-serif;font-size:14px;}
"""

HEAD_LINKS = """<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<link rel="preconnect" href="https://rsms.me/"/>
<link rel="stylesheet" href="https://rsms.me/inter/inter.css"/>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,300;8..60,400;8..60,600&display=swap" rel="stylesheet"/>"""

LOGO = """<svg class="logo-svg" width="30" height="30" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <circle cx="14" cy="16" r="10" fill="#ffb347" opacity="0.5"/>
  <circle cx="20" cy="13" r="8" fill="#ff6b6b" opacity="0.45"/>
  <circle cx="18" cy="20" r="7" fill="#ffb347" opacity="0.4"/>
  <circle cx="12" cy="12" r="5" fill="#f5f1e8" opacity="0.35"/>
  <circle cx="22" cy="19" r="4" fill="#f5f1e8" opacity="0.3"/>
</svg>"""

FOOTER = """<footer>
  <div class="row">
    <span>Built with <span class="heart">&hearts;</span> in Berlin</span>
    <a href="https://github.com/feamando/sgs">github.com/feamando/sgs</a>
    <span>Nikita Gorshkov</span>
    <a href="mailto:ngorshkov@proton.me">ngorshkov@proton.me</a>
  </div>
</footer>"""

def header(brand_href, nav):
    items = "".join(f'<li><a href="{h}">{label}</a></li>' for label, h in nav)
    return f"""<header class="site-header">
  <a href="{brand_href}" class="header-brand">
    {LOGO}
    <span class="header-brand-name">Radiance Labs</span>
  </a>
  <nav><ul class="header-nav">{items}</ul></nav>
</header>"""

def page(title, desc, body, brand_href, nav):
    return f"""<!doctype html>
<html lang="en">
<head>
{HEAD_LINKS}
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}"/>
<style>{STYLE}</style>
</head>
<body>
{header(brand_href, nav)}
{body}
{FOOTER}
</body>
</html>
"""

# ── Build ────────────────────────────────────────────────────────────────────

def locate_image(name):
    for d in IMAGE_DIRS:
        p = SGS / d / name
        if p.exists():
            return p
    raise FileNotFoundError(name)

def build():
    # reset output dirs
    if BLOG.exists():
        shutil.rmtree(BLOG)
    ASSETS.mkdir(parents=True)

    # copy images used by any post
    used = {im["name"] for post in POSTS for im in post["images"]}
    for name in sorted(used):
        shutil.copy2(locate_image(name), ASSETS / name)

    # render each post's body + excerpt + slug
    for post in POSTS:
        raw = (SGS / post["src"]).read_text(encoding="utf-8")
        if "section" in post:
            raw = extract_section(raw, post["section"])
        post["body"] = render_body(raw)
        post["excerpt"] = first_sentence_excerpt(post["body"])
        post["slug"] = make_slug(post)

    # newest first
    ordered = sorted(POSTS, key=lambda p: (p["date"], p["seq"]), reverse=True)

    # ── detail pages ──
    for post in ordered:
        figures = ""
        for im in post["images"]:
            cap = f'<figcaption>{html.escape(im["caption"])}</figcaption>' if im["caption"] else ""
            figures += (f'<figure><img src="../assets/{im["name"]}" '
                        f'alt="{html.escape(im["caption"] or post["title"])}" loading="lazy"/>{cap}</figure>\n')
        article = f"""<section class="blog-top">
  <a class="back-link" href="../">&larr; All posts</a>
  <article>
    <div class="post-date">{pretty_date(post["date"])}</div>
    <h1>{html.escape(post["title"])}</h1>
    <div class="byline">Nikita Gorshkov &middot; Radiance Labs</div>
    {post["body"]}
    {figures}
  </article>
</section>"""
        out_dir = BLOG / post["slug"]
        out_dir.mkdir(parents=True, exist_ok=True)
        # detail header brand -> blog home (../); nav links to site + blog home
        nav = [("Home", "../../"), ("Blog", "../")]
        (out_dir / "index.html").write_text(
            page(f'{post["title"]} — Radiance Labs', post["excerpt"], article, "../", nav),
            encoding="utf-8")

    # ── blog homepage ──
    cards = ""
    last_year = None
    for post in ordered:
        year = post["date"][:4]
        if year != last_year:
            cards += f'<div class="year-label">{year}</div>\n'
            last_year = year
        cards += f"""<a class="post-card" href="{post["slug"]}/">
  <div class="post-date">{pretty_date(post["date"])}</div>
  <h3>{html.escape(post["title"])}</h3>
  <p>{html.escape(post["excerpt"])}</p>
  <span class="arrow">Read post &rarr;</span>
</a>
"""
    home_body = f"""<section class="blog-top">
  <div class="eyebrow">Writing</div>
  <h2>From the lab</h2>
  <p class="lead">Notes from the Semantic Gaussian Splatting research program &mdash; the models (Planck, Hertz, Raum, Klang), the experiments, and the negative results worth keeping. Newest first.</p>
  <div class="feed">
{cards}  </div>
</section>"""
    # blog home header brand -> main site (../); nav back to site
    nav = [("Home", "../"), ("Research", "../#research"), ("Papers", "../#papers")]
    (BLOG / "index.html").write_text(
        page("Blog — Radiance Labs",
             "Writing from Radiance Labs on Semantic Gaussian Splatting: foundational model research and prompt-to-3D generation.",
             home_body, "../", nav),
        encoding="utf-8")

    print(f"Built {len(ordered)} posts + homepage into {BLOG}")

if __name__ == "__main__":
    build()

"""Real sources on screen (production plan step 1, owner approved 2026-11-11).

For each video, every page the research used is opened in headless Chromium and kept as the edit's
raw material: the first screen (for a browser-frame shot), the whole page up to a limit (for a
scroll), and where each researched claim sits on that page (for a highlighter stroke on the exact
words). Real people's faces in the captures are blurred (owner rule: never other people's faces).
Every capture is logged with its link, which the free guide and the community classroom reuse.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VIEW = {"width": 1440, "height": 900}
MAX_PAGES = 12
MAX_FULL_HEIGHT = 5400
SKIP = re.compile(r"(golidee\.com|github\.com/risktacker|youtube\.com/watch|youtu\.be/)", re.I)

DISMISS = r"""
() => {
  const words = /^(accept|accept all|agree|i agree|allow all|got it|ok|okay|close|dismiss|continue|no thanks)$/i;
  for (const b of document.querySelectorAll('button, [role=button], a')) {
    const t = (b.innerText || b.getAttribute('aria-label') || '').trim();
    if (words.test(t)) { try { b.click(); } catch (e) {} }
  }
  // fixed banners and pop-ups that cover the page
  for (const el of document.querySelectorAll('body *')) {
    const s = getComputedStyle(el);
    if ((s.position === 'fixed' || s.position === 'sticky') && el.offsetHeight > 0) {
      const r = el.getBoundingClientRect();
      const covers = r.width * r.height > 0.25 * innerWidth * innerHeight;
      const bannerish = /cookie|consent|gdpr|subscribe|newsletter|modal|popup|overlay/i.test(el.className + ' ' + el.id);
      if (covers || bannerish) el.style.setProperty('display', 'none', 'important');
    }
  }
}
"""

FIND = r"""
(groups) => {
  // groups: one list per claim, longest phrase first. The first visible match inside the page's
  // main content wins; menus, headers, footers and sidebars never count (2026-11-11: "5.2" hit the nav).
  const skip = (el) => !!el.closest('nav, header, footer, aside, [role=navigation], [role=banner], [aria-hidden=true]');
  const main = document.querySelector('main, article, [role=main]') || document.body;
  const walker = document.createTreeWalker(main, NodeFilter.SHOW_TEXT);
  const nodes = []; let n;
  while ((n = walker.nextNode())) if (n.parentElement && !skip(n.parentElement)) nodes.push(n);
  const out = [];
  for (const group of groups) {
    let hit = null;
    for (const phrase of group) {
      const want = phrase.toLowerCase();
      for (const node of nodes) {
        const text = node.textContent.toLowerCase();
        let i = text.indexOf(want);
        while (i >= 0) {
          const before = text[i - 1] || ' ', after = text[i + want.length] || ' ';
          if (!/[a-z0-9]/.test(before) && !/[a-z0-9]/.test(after)) break;   // whole words only
          i = text.indexOf(want, i + 1);
        }
        if (i < 0) continue;
        const range = document.createRange();
        range.setStart(node, i); range.setEnd(node, i + want.length);
        const rects = [...range.getClientRects()].filter((r) => r.width > 2 && r.height > 2);
        if (!rects.length) continue;
        hit = { phrase, rects: rects.map((r) => [r.left + scrollX, r.top + scrollY, r.width, r.height]) };
        break;
      }
      if (hit) break;
    }
    if (hit) out.push(hit);
  }
  return out;
}
"""


# 2026-11-11 (owner): every source gets a zoom and a pointer even when no claim is found on it, and
# its own photo becomes a block. The page's headline and its biggest picture near the top are located.
MAIN = r"""
() => {
  const skip = (el) => !!el.closest('nav, header nav, footer, aside, [role=navigation]');
  const vis = (r) => r.width > 40 && r.height > 16 && r.top + scrollY < 2400;
  let headline = null;
  for (const h of document.querySelectorAll('main h1, article h1, h1, main h2, article h2')) {
    const r = h.getBoundingClientRect();
    if (!skip(h) && vis(r) && (h.innerText || '').trim().length > 8) {
      headline = [r.left + scrollX, r.top + scrollY, r.width, r.height]; break;
    }
  }
  let image = null, best = 0;
  const images = [];
  for (const img of document.querySelectorAll('img, picture img, video[poster]')) {
    const r = img.getBoundingClientRect();
    const area = r.width * r.height;
    if (skip(img) || r.width < 320 || r.height < 180) continue;
    const box = [r.left + scrollX, r.top + scrollY, r.width, r.height];
    if (r.top + scrollY < 2000 && area > best) { best = area; image = box; }
    // 2026-11-17 (owner): every big picture in the article (people, products), not only the top one
    if (r.top + scrollY < 6000 && !images.some((b) => Math.abs(b[1] - box[1]) < 40 && Math.abs(b[0] - box[0]) < 40))
      images.push(box);
  }
  images.sort((a, b) => b[2] * b[3] - a[2] * a[3]);
  // every readable block of the article, so a beat can zoom to the exact part that says it
  const blocks = [];
  const root = document.querySelector('main, article, [role=main]') || document.body;
  for (const el of root.querySelectorAll('h2, h3, p, li, blockquote, figcaption, td, th, pre, dd')) {
    if (blocks.length >= 40 || skip(el)) continue;
    const text = (el.innerText || '').replace(/\s+/g, ' ').trim();
    const r = el.getBoundingClientRect();
    if (text.length < 25 || r.width < 120 || r.height < 14 || r.top + scrollY > 5200) continue;
    if (blocks.some((b) => b.text === text.slice(0, 160))) continue;
    blocks.push({ text: text.slice(0, 160), rect: [r.left + scrollX, r.top + scrollY, r.width, Math.min(r.height, 420)] });
  }
  // 2026-11-12 (owner, modelled on Outskill): the things a viewer clicks or types into, so steps can be shown
  // on the real page: buttons, links that look like buttons, menu and tab items, fields, short commands
  const controls = [];
  for (const el of document.querySelectorAll('button, [role=button], [role=tab], [role=menuitem], nav a, header a, ' +
                                             'a[class*=btn], a[class*=button], input, textarea, select, code, kbd')) {
    if (controls.length >= 40) break;
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    if (r.width < 24 || r.height < 14 || r.width > 700 || s.visibility === 'hidden' || +s.opacity === 0) continue;
    if (r.top + scrollY > 5200 || r.left < 0 || r.right > innerWidth + 1) continue;
    let text = (el.innerText || el.value || el.getAttribute('placeholder') || el.getAttribute('aria-label') || '')
      .replace(/\s+/g, ' ').trim();
    if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT') text = 'field: ' + text;
    if (text.length < 2 || text.length > 60) continue;
    if (controls.some((c) => c.text === text)) continue;
    controls.push({ text, rect: [r.left + scrollX, r.top + scrollY, r.width, r.height] });
  }
  return { headline, image, images: images.slice(0, 4), blocks, controls };
}
"""


def sources(research: dict[str, Any]) -> list[dict[str, Any]]:
    """Each distinct source page with the claims taken from it."""
    pages: dict[str, dict[str, Any]] = {}
    for claim in research.get("claims", []):
        url = str(claim.get("source_url", "")).strip()
        if not url.startswith("http") or SKIP.search(url):
            continue
        page = pages.setdefault(url, {"url": url, "title": str(claim.get("source_title", "")), "claims": []})
        page["claims"].append(str(claim.get("claim", "")))
    return list(pages.values())[:MAX_PAGES]


def phrases(claims: list[str]) -> list[list[str]]:
    """For each claim, exact pieces to find on the page, longest first: a number with the words
    around it, then the number with its unit, then the claim's opening words."""
    groups: list[list[str]] = []
    for claim in claims:
        words = claim.split()
        group: list[str] = []
        for k, w in enumerate(words):
            if re.search(r"\d", w):
                for left, right in ((2, 2), (1, 2), (0, 2), (1, 1), (0, 1)):
                    piece = " ".join(words[max(0, k - left): k + 1 + right]).strip(".,;:()\"'")
                    if len(piece.split()) > 1:
                        group.append(piece)
                bare = w.strip(".,;:()\"'")
                if len(bare) >= 2:
                    group.append(bare)
        if len(words) >= 4:
            group.append(" ".join(words[:6]).strip(".,;:"))
            group.append(" ".join(words[:4]).strip(".,;:"))
        seen, keep = set(), []
        for piece in sorted(group, key=len, reverse=True):
            if piece.lower() not in seen:
                seen.add(piece.lower())
                keep.append(piece)
        if keep:
            groups.append(keep[:14])
    return groups[:12]


def blur_faces(path: Path) -> int:
    """Blur every face found in a capture; returns how many."""
    import cv2

    image = cv2.imread(str(path))
    if image is None:
        return 0
    grey = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    finder = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = finder.detectMultiScale(grey, scaleFactor=1.1, minNeighbors=6, minSize=(36, 36))
    for (x, y, w, h) in faces:
        pad = int(0.25 * max(w, h))
        x0, y0 = max(0, x - pad), max(0, y - pad)
        x1, y1 = min(image.shape[1], x + w + pad), min(image.shape[0], y + h + pad)
        k = max(31, (max(w, h) // 2) | 1)
        image[y0:y1, x0:x1] = cv2.GaussianBlur(image[y0:y1, x0:x1], (k, k), 0)
    if len(faces):
        cv2.imwrite(str(path), image)
    return len(faces)


PRODUCT_PAGES = 6


def product_pages(names: list[str], skip_domains: set[str]) -> list[dict[str, Any]]:
    """Owner 2026-11-25 ("steps to be shown without skipping, on screenshots or screen recordings"): the real page of
    every product, app or tool the SCRIPT names, so a step like "install OpenCode, choose Windows x64" is shown on
    the product's own page. Found free: its GitHub repository (and the homepage the repository names), else its
    official website on Wikidata. Never stops a video."""
    import urllib.parse
    import urllib.request
    headers = {"User-Agent": "GOLIDE-engine/1.0 (https://studio.golidee.com)", "Accept": "application/json"}

    def get(url: str) -> Any:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))

    def key(x: str) -> str:
        return re.sub(r"[^a-z0-9]", "", x.lower())

    out: list[dict[str, Any]] = []
    for name in names:
        found: list[tuple[str, str]] = []
        try:
            repos = get("https://api.github.com/search/repositories?" + urllib.parse.urlencode(
                {"q": f"{name} in:name", "sort": "stars", "per_page": 5})).get("items") or []
            repo = next((r for r in repos if key(r.get("name", "")) == key(name) and r.get("stargazers_count", 0) >= 200), None)
            if repo:
                if repo.get("homepage", "").startswith("http"):
                    found.append((repo["homepage"], f"{name} (official site)"))
                found.append((repo["html_url"], f"{name} on GitHub"))
        except Exception:  # noqa: BLE001 - no GitHub answer: try Wikidata
            pass
        if not found:
            try:
                hits = get("https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode(
                    {"action": "wbsearchentities", "search": name, "language": "en", "format": "json", "limit": 1})).get("search") or []
                if hits and key(hits[0].get("label", "")) == key(name):
                    ent = get(f"https://www.wikidata.org/wiki/Special:EntityData/{hits[0]['id']}.json")["entities"][hits[0]["id"]]
                    for c in ent.get("claims", {}).get("P856", [])[:1]:
                        found.append((c["mainsnak"]["datavalue"]["value"], f"{name} (official site)"))
            except Exception:  # noqa: BLE001
                pass
        for url, title in found:
            dom = re.sub(r"^www\.", "", urllib.parse.urlparse(url).netloc.lower())
            if dom and dom not in skip_domains and not SKIP.search(url):
                skip_domains.add(dom)
                out.append({"url": url, "title": title, "claims": [], "product": name})
        if len(out) >= PRODUCT_PAGES:
            break
    return out[:PRODUCT_PAGES]


# owner 2026-11-25: "if the recorded screen is broken it is not used; another block is". A page whose styles did not
# load (bare blue links on white), a block or error page, a cookie or bot wall, or a near-empty screen is not shown.
HEALTH = """() => {
  const b = document.body; if (!b) return {ok: false, why: 'no page'};
  const text = (b.innerText || '').slice(0, 4000);
  const font = getComputedStyle(b).fontFamily.toLowerCase();
  const sheets = [...document.styleSheets].filter((s) => { try { return s.cssRules.length > 0; } catch (e) { return true; } }).length;
  const links = [...document.querySelectorAll('a')].slice(0, 80);
  const raw = links.filter((a) => { const c = getComputedStyle(a); return c.color === 'rgb(0, 0, 238)' && c.textDecorationLine.includes('underline'); }).length;
  const imgs = [...document.images].filter((i) => i.getBoundingClientRect().width > 120);
  const broken = imgs.filter((i) => i.complete && i.naturalWidth === 0).length;
  return {text, font, sheets, links: links.length, raw, imgs: imgs.length, broken,
          words: text.split(/\s+/).filter(Boolean).length, title: document.title};
}"""
BLOCKED = re.compile(r"\b(access denied|403 forbidden|404 not found|page not found|just a moment|verify you are human|"
                     r"are you a robot|captcha|enable javascript|attention required|too many requests|"
                     r"this site can.t be reached|err_[a-z_]+)\b", re.I)


def broken_page(h: dict[str, Any] | None) -> str:
    """Why a captured page is not fit for the screen ("" when it is)."""
    if not h:
        return "the page could not be read"
    if h.get("ok") is False:
        return str(h.get("why") or "no page")
    if BLOCKED.search(str(h.get("title") or "") + " " + str(h.get("text") or "")[:600]):
        return "an error, block or bot-check page"
    if int(h.get("sheets") or 0) == 0:
        return "its styles did not load"
    font = str(h.get("font") or "")
    if int(h.get("links") or 0) >= 10 and int(h.get("raw") or 0) >= 0.6 * int(h.get("links") or 1) \
            and ("times" in font or font.strip('"') in ("serif", "")):
        return "unstyled (bare blue links)"
    if int(h.get("imgs") or 0) >= 3 and int(h.get("broken") or 0) >= 0.5 * int(h.get("imgs") or 1):
        return "its pictures did not load"
    if int(h.get("words") or 0) < 15 and int(h.get("imgs") or 0) == 0:
        return "near empty"
    return ""


def capture(research: dict[str, Any], folder: Path, script: str = "") -> list[dict[str, Any]]:
    """Open every source page and keep its screens, claim positions and link. Never stops a video:
    a page that will not open is logged and skipped. With the script, the real pages of the products it names are
    captured too (owner 2026-11-25: steps on real screens)."""
    from playwright.sync_api import sync_playwright

    folder.mkdir(parents=True, exist_ok=True)
    log: list[dict[str, Any]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport=VIEW, device_scale_factor=1.5, locale="en-US",
                                      user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                                  "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"))
        pages = sources(research)
        if script:
            import urllib.parse
            have = {re.sub(r"^www\.", "", urllib.parse.urlparse(p["url"]).netloc.lower()) for p in pages}
            names = named_subjects({"core_fact": script, "claims": []}, str(research.get("title") or ""), most=8)
            pages += product_pages(names, have)
        for i, page_info in enumerate(pages, 1):
            entry = dict(page_info, ok=False)
            page = context.new_page()
            try:
                page.goto(page_info["url"], wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(2500)
                page.evaluate(DISMISS)
                page.wait_for_timeout(600)
                entry["title"] = page.title() or entry["title"]
                why = broken_page(page.evaluate(HEALTH))
                if why:                                    # never shown; the editor uses another block
                    raise RuntimeError(f"broken screen: {why}")
                top = folder / f"{i:02d}-top.png"
                page.screenshot(path=str(top))
                height = min(MAX_FULL_HEIGHT, page.evaluate("document.documentElement.scrollHeight"))
                page.set_viewport_size({"width": VIEW["width"], "height": int(height)})
                full = folder / f"{i:02d}-full.png"
                page.screenshot(path=str(full))
                page.set_viewport_size(VIEW)
                spots = page.evaluate(FIND, phrases(page_info["claims"]))
                main = page.evaluate(MAIN) or {}
                photos: list[str] = []
                boxes = ([main["image"]] if main.get("image") else []) + [
                    b for b in (main.get("images") or []) if b != main.get("image")]
                for n, (x, y, w, h) in enumerate(boxes[:4]):
                    name = f"{i:02d}-photo.png" if n == 0 else f"{i:02d}-photo{n + 1}.png"
                    try:
                        from PIL import Image as _Image
                        with _Image.open(full) as shot:
                            k = 1.5
                            box = (int(x * k), int(y * k), int((x + w) * k), int(min(y + h, height) * k))
                            if box[3] - box[1] > 120 and box[2] - box[0] > 200:
                                shot.crop(box).save(folder / name)
                                photos.append(name)
                    except Exception:  # noqa: BLE001
                        pass
                # 2026-11-17 (owner): people and news photos are shown as they are (no face blurring); always as
                # commentary in a framed card with the source named
                entry.update(ok=True, top=top.name, full=full.name, full_height=int(height), scale=1.5,
                             highlights=spots, headline=main.get("headline"), blocks=main.get("blocks") or [],
                             controls=main.get("controls") or [],
                             photo=photos[0] if photos else None, photos=photos)
            except Exception as error:  # noqa: BLE001
                entry["error"] = str(error)[:200]
            finally:
                page.close()
            entry["captured_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            log.append(entry)
        browser.close()
    title = str(research.get("title") or "")
    names = named_subjects(research, title)
    names += [t for t in subject_things(research, title) if t not in names]
    log.extend(subject_pictures(names[:8], folder, len(log) + 1))
    (folder / "sources.json").write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
    return log


NAME = re.compile(r"\b([A-Z][a-zA-Z0-9]+(?:[ -][A-Z][a-zA-Z0-9]+){0,2})\b")
NOT_NAMES = {"The", "This", "That", "These", "Those", "A", "An", "And", "But", "So", "If", "In", "On", "At", "It",
             "Its", "Why", "How", "What", "When", "Who", "We", "You", "Your", "They", "He", "She", "I", "AI", "CEO",
             "New", "Now", "Here", "There", "Every", "Most", "One", "Two", "First", "Last", "According",
             # 2026-11-25: a step's verb opens the sentence ("Install OpenCode"): it is never part of the name
             "Install", "Choose", "Open", "Paste", "Run", "Click", "Type", "Add", "Use", "Download", "Go", "Set",
             "Pick", "Copy", "Save", "Then", "Next", "Today", "Tap", "Select", "Press", "Build", "Ask", "Tell"}


def named_subjects(research: dict[str, Any], title: str = "", most: int = 4) -> list[str]:
    """The people, companies and products the story keeps naming (most mentioned first)."""
    # names are read from sentences (a Title Case headline would make every word look like a name)
    text = " ".join([str(research.get("core_fact") or "")] + [str(c.get("claim", "")) for c in research.get("claims", [])])
    counts: dict[str, int] = {}
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        for match in NAME.finditer(sentence):
            name = match.group(1).strip()
            words = name.split()
            if match.start() == 0 and len(words) == 1 and words[0] in NOT_NAMES:
                continue
            while words and words[0] in NOT_NAMES:
                words = words[1:]
            name = " ".join(words)
            if len(name) < 3 or (name.isupper() and len(name) <= 3):
                continue
            counts[name] = counts.get(name, 0) + (3 if name.lower() in title.lower() else 1)
    ranked = sorted(counts, key=lambda n: (-counts[n], -len(n)))
    keep: list[str] = []
    for name in ranked:
        if any(name in k or k in name for k in keep):
            continue
        keep.append(name)
    return keep[:most]


# 2026-11-19 (owner, after a car video with no car in it): the THINGS a story is about get real pictures too, not
# only the capitalised names (which gave a China EV video two flags). Words in the story -> the Wikipedia page whose
# picture shows the thing.
THINGS = {
    "electric car": "Electric car", "electric vehicle": "Electric car", " ev ": "Electric car", " evs ": "Electric car",
    " car ": "Car", " cars ": "Car",
    "car factory": "Automotive industry", "assembly line": "Assembly line", "gigafactory": "Gigafactory",
    "factory": "Factory", "battery": "Electric vehicle battery", "lfp": "Lithium iron phosphate battery",
    "lithium": "Lithium-ion battery", "charging": "Charging station", "self-driving": "Self-driving car",
    "driver assist": "Advanced driver-assistance system", "robot": "Industrial robot", "humanoid": "Humanoid robot",
    "smartphone": "Smartphone", "iphone": "IPhone", "laptop": "Laptop", "chip": "Integrated circuit",
    "semiconductor": "Semiconductor device fabrication", "gpu": "Graphics processing unit",
    "data center": "Data center", "data centre": "Data center", "server": "Server room", "satellite": "Satellite",
    "rocket": "Rocket", "space station": "International Space Station", "telescope": "Space telescope",
    "solar panel": "Solar panel", "wind turbine": "Wind turbine", "nuclear": "Nuclear power plant",
    "oil": "Oil refinery", "ship": "Container ship", "port": "Port", "drone": "Unmanned aerial vehicle",
    "airplane": "Airliner", "plane": "Airliner", "train": "High-speed rail", "truck": "Truck",
    "game console": "Video game console", "video game": "Video game", "headset": "Virtual reality headset",
}


def subject_things(research: dict[str, Any], title: str = "", most: int = 4) -> list[str]:
    """The things the story keeps talking about (title words count three times), as Wikipedia page titles."""
    text = " " + " ".join([title] * 3 + [str(research.get("core_fact") or "")]
                          + [str(c.get("claim", "")) for c in research.get("claims", [])]).lower() + " "
    text = re.sub(r"[^a-z0-9\-]+", " ", text)
    counts: dict[str, int] = {}
    for word, page in THINGS.items():
        n = text.count(word if word.startswith(" ") else f" {word}")
        if n:
            counts[page] = counts.get(page, 0) + n
    return sorted(counts, key=lambda p: -counts[p])[:most]


# pictures that are not the thing: flags, coats of arms, seals, maps, logos and locator images
NOT_A_PICTURE = re.compile(r"flag_of|coat_of_arms|seal_of|emblem_of|_map|map_|locator|orthographic|logo|location",
                           re.IGNORECASE)


def subject_pictures(names: list[str], folder: Path, start: int) -> list[dict[str, Any]]:
    """2026-11-17 (owner): the real picture of each person or product the story names (people too, not only
    things), from Wikipedia: free, credited on screen as the source. Never stops a video."""
    import time
    import urllib.error
    import urllib.parse
    import urllib.request


    out = []
    # 2026-11-20: Wikimedia answers 429 to bare bot agents and to bursts of full-size originals; a proper agent with a
    # contact, a resized copy (1280 px) and a short wait-and-retry get the picture
    headers = {"User-Agent": "GOLIDE-engine/1.0 (https://studio.golidee.com; hello@golidee.com) python-urllib"}
    folder.mkdir(parents=True, exist_ok=True)

    def fetch(url: str, timeout: int = 30) -> bytes:
        for wait in (0, 2, 6):
            time.sleep(wait)
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as r:
                    return r.read()
            except urllib.error.HTTPError as e:   # noqa: PERF203
                if e.code != 429 or wait == 6:
                    raise
        raise RuntimeError("unreachable")

    for k, name in enumerate(names):
        try:
            q = urllib.parse.quote(name)
            with urllib.request.urlopen(urllib.request.Request(
                    f"https://en.wikipedia.org/w/rest.php/v1/search/title?q={q}&limit=1", headers=headers), timeout=20) as r:
                pages = json.loads(r.read().decode("utf-8")).get("pages") or []
            if not pages:
                continue
            key = pages[0]["key"]
            with urllib.request.urlopen(urllib.request.Request(
                    f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(key)}", headers=headers),
                    timeout=20) as r:
                summary = json.loads(r.read().decode("utf-8"))
            src = (summary.get("thumbnail") or summary.get("originalimage") or {}).get("source")
            if src and re.search(r"/\d+px-", src):
                src = re.sub(r"/\d+px-", "/1280px-", src)
            if not src or src.lower().endswith(".svg") or NOT_A_PICTURE.search(src):
                continue
            file = folder / f"{start + k:02d}-photo.png"
            raw = fetch(src)
            from io import BytesIO
            from PIL import Image as _Image
            with _Image.open(BytesIO(raw)) as im:
                im.convert("RGB").save(file)
            out.append({"url": summary.get("content_urls", {}).get("desktop", {}).get("page", src),
                        "title": f"{name} (picture)", "claims": [], "ok": True, "picture_only": True,
                        "subject": name, "photo": file.name, "photos": [file.name]})
        except Exception as error:  # noqa: BLE001
            out.append({"subject": name, "ok": False, "picture_only": True, "error": str(error)[:160]})
    return out


def contact_sheet(folder: Path, out: Path) -> Path:
    """One image of every capture with its link and highlighted claims, for the owner's check."""
    from PIL import Image, ImageDraw, ImageFont

    log = json.loads((folder / "sources.json").read_text(encoding="utf-8"))
    ok = [e for e in log if e.get("ok")]
    cols, w = 2, 720
    h = int(w * VIEW["height"] / VIEW["width"]) + 56
    sheet = Image.new("RGB", (cols * w + (cols + 1) * 16, max(1, -(-len(ok) // cols)) * (h + 16) + 16), (24, 24, 28))
    font = ImageFont.load_default()
    for k, e in enumerate(ok):
        top = Image.open(folder / e["top"]).convert("RGB")
        d = ImageDraw.Draw(top)
        for spot in e.get("highlights", []):
            for (x, y, rw, rh) in spot["rects"]:
                if y * e["scale"] < top.height:
                    s = e["scale"]
                    d.rectangle([x * s - 4, y * s - 3, (x + rw) * s + 4, (y + rh) * s + 3], outline=(250, 204, 21), width=5)
        top = top.resize((w, h - 56))
        x0, y0 = 16 + (k % cols) * (w + 16), 16 + (k // cols) * (h + 16)
        sheet.paste(top, (x0, y0))
        ImageDraw.Draw(sheet).text((x0, y0 + h - 50), f"{e['title'][:90]}\n{e['url'][:110]}\n"
                                    f"claims found on page: {len(e.get('highlights', []))}  faces blurred: "
                                    f"{e.get('faces_blurred', 0)}", fill=(230, 230, 230), font=font)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=88)
    return out

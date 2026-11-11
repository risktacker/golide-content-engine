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


def capture(research: dict[str, Any], folder: Path) -> list[dict[str, Any]]:
    """Open every source page and keep its screens, claim positions and link. Never stops a video:
    a page that will not open is logged and skipped."""
    from playwright.sync_api import sync_playwright

    folder.mkdir(parents=True, exist_ok=True)
    log: list[dict[str, Any]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport=VIEW, device_scale_factor=1.5, locale="en-US",
                                      user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                                  "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"))
        for i, page_info in enumerate(sources(research), 1):
            entry = dict(page_info, ok=False)
            page = context.new_page()
            try:
                page.goto(page_info["url"], wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(2500)
                page.evaluate(DISMISS)
                page.wait_for_timeout(600)
                entry["title"] = page.title() or entry["title"]
                top = folder / f"{i:02d}-top.png"
                page.screenshot(path=str(top))
                height = min(MAX_FULL_HEIGHT, page.evaluate("document.documentElement.scrollHeight"))
                page.set_viewport_size({"width": VIEW["width"], "height": int(height)})
                full = folder / f"{i:02d}-full.png"
                page.screenshot(path=str(full))
                page.set_viewport_size(VIEW)
                spots = page.evaluate(FIND, phrases(page_info["claims"]))
                entry.update(ok=True, top=top.name, full=full.name, full_height=int(height), scale=1.5,
                             highlights=spots, faces_blurred=blur_faces(top) + blur_faces(full))
            except Exception as error:  # noqa: BLE001
                entry["error"] = str(error)[:200]
            finally:
                page.close()
            entry["captured_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            log.append(entry)
        browser.close()
    (folder / "sources.json").write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
    return log


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

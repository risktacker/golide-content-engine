"""One real-product picture through the production path, saved to production-queue/preview."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from golide_engine.providers.openai_media import OpenAIProductProvider  # noqa: E402

prompt = " ".join(sys.argv[1:]) or "Apple MacBook Pro 14-inch laptop, open, space black aluminium"
out = ROOT / "production-queue" / "preview" / "product-probe.png"
out.parent.mkdir(parents=True, exist_ok=True)
try:
    OpenAIProductProvider("gpt-image-1-mini", "medium").create(prompt, out, "1024x1536")
    print("saved", out)
except Exception as exc:  # written down so it can be read without the run log
    (out.parent / "product-probe-error.txt").write_text(repr(exc)[:3000], encoding="utf-8")
    print("failed", exc)

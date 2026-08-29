from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path


NARRATION = """Your computer can change a zero into a one without a hacker, a software bug, or a broken chip. Sometimes, the chain begins in space.

A high-energy cosmic ray strikes Earth's atmosphere and creates a shower of secondary particles. Most pass harmlessly through us. But if one crosses the right part of a memory chip, it can leave a tiny burst of electrical charge.

That charge may be enough to flip one stored bit: zero becomes one, or one becomes zero. The transistor still works. The data is simply wrong. Engineers call this a single-event upset—or a soft error.

In space, satellites face far more radiation. ESA found random memory flips while studying ten years of its Swarm spacecraft data.

So computers fight invisible particles with error-correcting memory: extra bits that can detect and repair many mistakes.

The machine did exactly what physics told it to do. It just wasn't what the programmer wrote."""


def main() -> None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required")

    payload = json.dumps(
        {
            "model": "gpt-4o-mini-tts",
            "voice": "cedar",
            "input": NARRATION,
            "instructions": (
                "Neutral international English. Warm, intelligent and quietly fascinated. "
                "Natural documentary explainer, not a trailer voice. Speak at about 170 words "
                "per minute with crisp articulation. Emphasize 'without', 'one stored bit', "
                "'soft error', and the final contrast. Keep pauses tight and purposeful."
            ),
            "response_format": "mp3",
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        "https://api.openai.com/v1/audio/speech",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    output = Path("build/cosmic-ray-short/narration.mp3")
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            output.write_bytes(response.read())
    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI TTS request failed ({error.code}): {details}") from error
    print(f"Generated {output} ({output.stat().st_size} bytes)")


if __name__ == "__main__":
    main()

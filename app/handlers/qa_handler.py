import re
import requests
from app.llm import chat

SYSTEM_PROMPT = (
    "You are a concise personal assistant on WhatsApp. "
    "Reply in 1-3 sentences max. "
    "No markdown formatting. No bullet points. Plain text only. "
    "Output ONLY the reply, no preamble, no thinking."
)


def _extract_answer(text: str) -> str:
    """Strip thinking blocks and return only the final answer."""
    # Remove explicit <think> blocks
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    # Split into paragraphs
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]

    # Walk from the end — find the first paragraph that doesn't look like reasoning
    reasoning_markers = (
        "here's a thinking", "here's my thinking", "let me think",
        "analyze user", "analyze the", "step ", "key constraint",
        "determine the", "identify the", "final answer:", "**final",
    )
    for para in reversed(paragraphs):
        lower = para.lower()
        if any(m in lower for m in reasoning_markers):
            continue
        # Skip numbered/bulleted lists that are clearly reasoning steps
        if re.match(r"^\d+\.", para) or para.startswith("•") or para.startswith("- "):
            continue
        # Take up to 3 sentences from this paragraph
        sentences = re.split(r"(?<=[.!?])\s+", para)
        return " ".join(sentences[:3])

    # Fallback: return last paragraph as-is
    return paragraphs[-1] if paragraphs else text


def handle_qa(text: str) -> str:
    try:
        raw = chat(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            max_tokens=400,
            temperature=0.7,
        )
        return _extract_answer(raw)
    except requests.RequestException:
        return "Sorry, I could not reach the AI right now. Please try again."
    except (KeyError, IndexError):
        return "Sorry, I received an unexpected response. Please try again."

"""Grounded answers from retrieved chunks when LLM_PROVIDER=local.

This path does not call Gemini or OpenAI. It is for local demos and tests.
Production answers use the ADK agents.
"""

import re

from agents.tools.docs import POLICY_ALIASES, get_policy_text, search_docs

_STOP = {
    "the",
    "a",
    "an",
    "of",
    "to",
    "and",
    "or",
    "for",
    "in",
    "on",
    "is",
    "are",
    "do",
    "does",
    "how",
    "what",
    "where",
    "when",
    "who",
    "many",
    "much",
    "should",
    "i",
    "we",
    "you",
    "your",
    "our",
    "with",
    "from",
    "that",
    "this",
    "each",
    "per",
}


def answer_locally(question: str) -> dict:
    text = (question or "").strip()
    if not text:
        return {
            "answer": "Ask a question about the indexed documents.",
            "citations": [],
            "agent_trace": ["local"],
        }
    if re.search(r"\b(summarize|summary|overview|tl;?dr|recap)\b", text, re.I):
        return _summarize(text)
    return _answer(text)


def _tokens(text: str) -> set[str]:
    return {
        tok
        for tok in re.findall(r"[a-z0-9']+", text.lower())
        if tok not in _STOP and len(tok) > 1
    }


def _answer(question: str) -> dict:
    found = search_docs(question, k=5)
    hits = found.get("hits") or []
    if found.get("status") != "success":
        return {
            "answer": found.get("error") or "Search failed.",
            "citations": [],
            "agent_trace": ["local"],
        }
    if not hits:
        return {
            "answer": "I don't know. No documents are indexed yet.",
            "citations": [],
            "agent_trace": ["local"],
        }

    ranked = _rerank(question, hits)
    best = ranked[0]
    answer = _best_sentences(question, best.get("content") or "")
    citations = _citations(question, ranked)
    return {"answer": answer, "citations": citations, "agent_trace": ["local"]}


def _rerank(question: str, hits: list[dict]) -> list[dict]:
    q = _tokens(question)
    scored = []
    for hit in hits:
        overlap = len(q & _tokens(hit.get("content") or ""))
        blended = float(hit.get("score") or 0) + overlap
        scored.append((blended, hit))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [hit for _, hit in scored]


def _plain(text: str) -> str:
    parts: list[str] = []
    for line in text.splitlines():
        heading = line.lstrip().startswith("#")
        line = re.sub(r"^#+\s*", "", line).strip()
        if not line:
            continue
        if heading and line[-1] not in ".!?":
            line += "."
        parts.append(line)
    return " ".join(parts)


def _best_sentences(question: str, content: str) -> str:
    q = _tokens(question)
    want_number = bool(re.search(r"\b(how many|how much)\b", question, re.I))
    ranked: list[tuple[int, str]] = []
    for sentence in re.split(r"(?<=[.!?])\s+", _plain(content)):
        sentence = sentence.strip()
        if len(sentence) < 20:
            continue
        overlap = len(q & _tokens(sentence))
        if want_number and re.search(r"\d", sentence):
            overlap += 2
        ranked.append((overlap, sentence))
    ranked.sort(key=lambda item: item[0], reverse=True)
    if not ranked or ranked[0][0] <= 0:
        return _plain(content)[:700]

    chosen: list[str] = []
    for score, sentence in ranked:
        if score <= 0 or sentence in chosen:
            continue
        chosen.append(sentence)
        if len(chosen) == 2:
            break
    return " ".join(chosen)


def _citations(question: str, hits: list[dict]) -> list[dict]:
    best_overlap = _overlap(question, hits[0].get("content") or "")
    seen: set[str] = set()
    citations = []
    for index, hit in enumerate(hits[:3]):
        path = hit.get("path")
        if not path or path in seen:
            continue
        overlap = _overlap(question, hit.get("content") or "")
        if index > 0 and overlap < best_overlap:
            continue
        seen.add(path)
        citations.append({"path": path, "score": float(hit.get("score") or 0)})
    return citations


def _overlap(question: str, text: str) -> int:
    return len(_tokens(question) & _tokens(text))


def _summarize(question: str) -> dict:
    filename = _guess_filename(question)
    payload = get_policy_text("acme-handbook", filename)
    files = payload.get("files") or []
    if payload.get("status") != "success" or not files:
        return {
            "answer": payload.get("error") or "I don't know. Nothing is indexed yet.",
            "citations": [],
            "agent_trace": ["local"],
        }

    if not filename:
        files = _pick_files(question, files)

    bullets = []
    citations = []
    for item in files[:8]:
        content = (item.get("content") or "").strip()
        first = _first_sentences(content, 2)
        if not first:
            continue
        bullets.append(f"{item.get('path')}: {first}")
        citations.append({"path": item.get("path"), "score": 1.0})
    if not bullets:
        return {
            "answer": "I don't know. Those documents have no readable text.",
            "citations": [],
            "agent_trace": ["local"],
        }
    return {
        "answer": "\n".join(f"- {line}" for line in bullets),
        "citations": citations,
        "agent_trace": ["local"],
    }


def _guess_filename(question: str) -> str:
    text = question.lower()
    for key in sorted(POLICY_ALIASES, key=len, reverse=True):
        if re.search(rf"\b{re.escape(key)}\b", text):
            return POLICY_ALIASES[key]
    return ""


def _pick_files(question: str, files: list[dict]) -> list[dict]:
    q = _tokens(question)
    scored = []
    for item in files:
        overlap = len(q & _tokens(f"{item.get('path', '')} {item.get('content', '')[:1500]}"))
        scored.append((overlap, item))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    top = [item for score, item in scored if score > 0]
    return top[:4] or [item for _, item in scored[:3]]


def _first_sentences(content: str, count: int) -> str:
    flat = content.replace("\n", " ")
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", flat) if len(part.strip()) > 20]
    return " ".join(parts[:count])

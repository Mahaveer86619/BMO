import logging
import httpx

log = logging.getLogger("bmo.search")


async def search_web(query: str) -> str:
    params = {
        "q": query,
        "format": "json",
        "no_html": "1",
        "skip_disambig": "1",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                "https://api.duckduckgo.com/",
                params=params,
                headers={"User-Agent": "BMO/1.0"},
            )
            r.raise_for_status()
            data = r.json()

        # Prefer the Wikipedia-style abstract
        abstract = (data.get("AbstractText") or "").strip()
        if abstract:
            sentences = abstract.split(". ")
            # If the first sentence is already long, stop there — avoids 30s+ audio
            if len(sentences[0]) > 160:
                return sentences[0].rstrip(".") + "."
            return ". ".join(sentences[:2]).rstrip(".") + "."

        # Fall back to first related topic snippet
        snippets = [
            t["Text"]
            for t in data.get("RelatedTopics", [])
            if isinstance(t, dict) and t.get("Text")
        ]
        if snippets:
            return snippets[0][:200]

        return f"No quick summary found for '{query}'. I can answer from my own knowledge if you'd like."
    except Exception as e:
        log.warning("Search failed for %r: %s", query, e)
        return f"Search is unavailable right now. I'll do my best from memory: ask me anything about '{query}'."

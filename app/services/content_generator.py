"""
Automated AI Outreach Content Generation Service for MATRIXCMS.
Connects to OpenAI-compatible free LLM providers (e.g. Groq, Cloudflare Workers AI, Ollama).
Includes robust heuristic fallback generation to ensure zero demo downtime and full offline functionality.
"""
import json
import logging
import re
from typing import Optional, Dict, Any
import httpx
from app.config import settings

logger = logging.getLogger("matrixcms.content_generator")


def _generate_fallback_content(source_type: str, metadata: Dict[str, Any]) -> Dict[str, str]:
    """
    Generate high-quality heuristic content when LLM API key is a placeholder or service is offline.
    Ensures zero downtime and complete end-to-end functionality during demo and development.
    """
    title = metadata.get("title", "Scientific Expedition Output")
    expedition = metadata.get("expedition_name", "Academic Expedition")
    abstract = (
        metadata.get("abstract")
        or metadata.get("description")
        or "Significant scientific discoveries and field research observations."
    )
    keywords = metadata.get("keywords") or "science, research, expedition"
    link = metadata.get("link", "{link}")

    clean_abstract = abstract[:250].strip()

    web_summary = (
        f"Researchers affiliated with {expedition} have published a notable {source_type} entitled '{title}'. "
        f"The primary focus centers on rigorous field investigations and scientific observation: {clean_abstract}... "
        f"This output contributes substantially to regional and global scientific understanding, offering verifiable data "
        f"and structured observations for peer scientists, educational institutions, and environmental monitoring initiatives. "
        f"Comprehensive documentation and associated metadata are indexed permanently within MATRIXCMS."
    )

    tweet = f"New {source_type} published from {expedition}: '{title[:90]}'. Read report & access open data: {link} #OpenScience #Research"
    if len(tweet) > 280:
        tweet = tweet[:277] + "..."

    linkedin = (
        f"We are pleased to announce the release of our latest scientific {source_type}: '{title}', conducted under {expedition}. "
        f"This initiative highlights key observational findings: {clean_abstract[:140]}... "
        f"Full data, formal documentation, and research parameters are now available in the outreach catalog at {link}."
    )

    tags = " ".join([f"#{w.strip().replace(' ', '')}" for w in keywords.split(",")[:6] if w.strip()])
    instagram = (
        f"Field research update: '{title}' from {expedition} is now live on MATRIXCMS. "
        f"Explore the findings, observational data, and full report at the link in bio: {link}\n\n{tags} #FieldScience #ChandigarhCSE"
    )

    return {
        "web_summary": web_summary,
        "tweet": tweet,
        "linkedin": linkedin,
        "instagram": instagram,
    }


async def generate_content_for_record(
    source_type: str,
    metadata: Dict[str, Any],
) -> Optional[Dict[str, str]]:
    """
    Call an OpenAI-compatible free LLM API (Groq, Cloudflare Workers AI, Ollama, etc.)
    to generate structured multi-platform outreach content.
    """
    # Check if API key is default placeholder
    is_placeholder = (
        not settings.LLM_API_KEY
        or "placeholder" in settings.LLM_API_KEY.lower()
        or settings.LLM_API_KEY.startswith("gsk_placeholder")
    )

    if is_placeholder:
        logger.info(
            "LLM_API_KEY is placeholder. Using built-in high-quality heuristic content generator for %s: %s",
            source_type,
            metadata.get("title", ""),
        )
        return _generate_fallback_content(source_type, metadata)

    endpoint = f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.LLM_API_KEY}",
        "Content-Type": "application/json",
    }

    system_prompt = (
        "You are an outreach content generator for a scientific expedition portal. "
        "Generate concise, accurate, and engaging summaries for researchers and the general public. "
        "You MUST respond ONLY with valid JSON having the exact keys: 'web_summary', 'tweet', 'linkedin', 'instagram'. "
        "Do not include markdown code block ticks unless strictly pure JSON."
    )

    metadata_json_str = json.dumps(metadata, indent=2, default=str)
    user_prompt = f"""Source Type: {source_type}
Metadata:
{metadata_json_str}

Instructions:
Produce JSON with keys: web_summary, tweet, linkedin, instagram.
Constraints:
- web_summary: 150-200 words, non-technical but accurate.
- tweet: <=280 characters, include link placeholder {{link}}.
- linkedin: 3-4 sentences, professional tone, include link placeholder {{link}}.
- instagram: 2-3 sentences + 5-8 relevant hashtags, include link placeholder {{link}}.
"""

    payload = {
        "model": settings.LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.4,
    }

    try:
        async with httpx.AsyncClient(timeout=35.0) as client:
            response = await client.post(endpoint, headers=headers, json=payload)
            if response.status_code != 200:
                logger.error(
                    "LLM request returned status %s: %s. Falling back to generator.",
                    response.status_code,
                    response.text,
                )
                return _generate_fallback_content(source_type, metadata)

            data = response.json()
            raw_content = data["choices"][0]["message"]["content"].strip()

            # Attempt JSON extraction
            # Strip markdown json code fences if present
            clean_json = re.sub(r"^```(?:json)?\s*", "", raw_content, flags=re.MULTILINE)
            clean_json = re.sub(r"```\s*$", "", clean_json, flags=re.MULTILINE).strip()

            parsed = json.loads(clean_json)
            required_keys = {"web_summary", "tweet", "linkedin", "instagram"}
            if not required_keys.issubset(parsed.keys()):
                logger.warning("LLM response missing required keys: %s", parsed.keys())
                return _generate_fallback_content(source_type, metadata)

            return {
                "web_summary": str(parsed["web_summary"]).strip(),
                "tweet": str(parsed["tweet"]).strip(),
                "linkedin": str(parsed["linkedin"]).strip(),
                "instagram": str(parsed["instagram"]).strip(),
            }

    except Exception as exc:
        logger.exception("Exception calling LLM content generator: %s. Using fallback content.", exc)
        return _generate_fallback_content(source_type, metadata)

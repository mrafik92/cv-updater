from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from cv_tailor.schemas.job import JobInput
from cv_tailor.schemas.resume import Resume

if TYPE_CHECKING:
    from cv_tailor.services.openrouter import OpenRouterClient


class FabricationError(Exception):
    pass


def _extract_employers(resume: dict) -> set[str]:
    names: set[str] = set()
    sections = resume.get("sections", resume.get("data", {}).get("sections", {}))
    for section_key in ("experience", "education"):
        section = sections.get(section_key, {})
        for item in section.get("items", []):
            for field in ("company", "institution", "name"):
                val = item.get(field, "") or (item.get("data", {}).get(field, ""))
                if val and isinstance(val, str):
                    names.add(val.strip().lower())
    return names


def verify_truthfulness(base: dict, tailored: dict) -> None:
    """Raises FabricationError if tailored resume adds employers/institutions not present in base."""
    base_employers = _extract_employers(base)
    tailored_employers = _extract_employers(tailored)
    fabricated = tailored_employers - base_employers
    if fabricated:
        raise FabricationError(
            f"Tailored resume contains fabricated employers/institutions not in base resume: {fabricated}"
        )


SYSTEM_PROMPT: str = """You are an expert professional resume editor helping a candidate present their genuine experience in the best possible light for a specific role.

Your task is to adapt the provided resume JSON to align with the target job description. Work exclusively with the content already present in the base resume — your value is in presentation, emphasis, and clarity, not in adding new content.

Guidelines:
1. Rephrase bullet points for clarity and stronger keyword alignment with the job description. Draw only from existing accomplishments.
2. Reorder experience bullets within each role so the most relevant ones appear first for this particular position.
3. Where a required skill appears absent, highlight the closest adjacent skill that is genuinely present in the resume.
4. Rewrite the professional summary to speak directly to this role, using only facts already stated in the resume.
5. Reorder the skills list so the most relevant skills for this role appear prominently.
6. You may omit bullets that have no relevance to the role, but every bullet you include must trace back to the original resume.
7. All employers, job titles, companies, employment dates, degrees, certifications, and quantitative metrics must match the base resume exactly — changing these would misrepresent the candidate.
8. Return strictly valid JSON conforming to the provided schema. No explanatory prose."""


# JSON Schema mirroring cv_tailor.schemas.resume.Resume (extra="allow" => additionalProperties: true)
RR_RESUME_JSON_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Resume",
    "type": "object",
    "additionalProperties": True,
    "properties": {
        "basics": {
            "type": ["object", "null"],
            "additionalProperties": True,
            "properties": {
                "name": {"type": ["string", "null"]},
                "email": {"type": ["string", "null"]},
                "headline": {"type": ["string", "null"]},
                "phone": {"type": ["string", "null"]},
                "location": {
                    "type": ["object", "null"],
                    "additionalProperties": True,
                },
                "url": {"type": ["string", "null"]},
                "summary": {"type": ["string", "null"]},
                "photo": {"type": ["string", "null"]},
                "profiles": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": True,
                    },
                },
            },
        },
        "sections": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "additionalProperties": True,
                "properties": {
                    "name": {"type": ["string", "null"]},
                    "columns": {"type": ["integer", "null"]},
                    "visible": {"type": ["boolean", "null"]},
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": True,
                            "properties": {
                                "id": {"type": ["string", "null"]},
                                "visible": {"type": ["boolean", "null"]},
                                "data": {
                                    "type": "object",
                                    "additionalProperties": True,
                                },
                            },
                        },
                    },
                },
            },
        },
    },
}


def build_user_prompt(
    base_resume: dict[str, Any],
    job: JobInput,
    cumulative_feedback: list[str],
) -> str:
    """Build the user prompt for the tailoring LLM call.

    Includes:
      - the base resume JSON
      - the job description (and title/company if present)
      - a numbered list of all prior feedback items
      - a reminder to regenerate from the base resume (never iterate on a prior tailored version)
    """
    base_resume_json = json.dumps(base_resume, indent=2, ensure_ascii=False)

    job_lines: list[str] = []
    if job.title:
        job_lines.append(f"Title: {job.title}")
    if job.company:
        job_lines.append(f"Company: {job.company}")
    job_lines.append("Description:")
    job_lines.append(job.description)
    job_block = "\n".join(job_lines)

    parts: list[str] = [
        "Base resume (JSON):",
        base_resume_json,
        "",
        "Target job:",
        job_block,
    ]

    if cumulative_feedback:
        parts.append("")
        parts.append("Previous feedback:")
        for idx, fb in enumerate(cumulative_feedback, start=1):
            parts.append(f"{idx}. {fb}")

    parts.append("")
    parts.append(
        "Please produce the adapted resume starting fresh from the base resume above."
    )
    parts.append("Return strictly valid JSON conforming to the provided schema. No prose.")

    return "\n".join(parts)


async def tailor(
    client: OpenRouterClient,
    base_resume: dict[str, Any],
    job: JobInput,
    cumulative_feedback: list[str],
) -> dict[str, Any]:
    """Run a tailoring pass against the LLM, validating the output against the Resume model.

    On a single validation failure, retry once with the validation error appended to the prompt.
    """
    prompt = build_user_prompt(base_resume, job, cumulative_feedback)
    result = await client.generate_json(SYSTEM_PROMPT, prompt, RR_RESUME_JSON_SCHEMA)
    try:
        Resume.model_validate(result)
    except ValidationError as e:
        retry_prompt = (
            prompt
            + f"\n\nYour last response failed schema validation: {e}. Fix and resubmit."
        )
        result = await client.generate_json(SYSTEM_PROMPT, retry_prompt, RR_RESUME_JSON_SCHEMA)
        Resume.model_validate(result)
    try:
        verify_truthfulness(base_resume, result)
    except FabricationError:
        feedback_with_warning = list(cumulative_feedback or []) + [
            "CRITICAL: Do NOT add any employer, company, institution, or degree that is not in the original resume."
        ]
        retry_prompt = build_user_prompt(base_resume, job, feedback_with_warning)
        result = await client.generate_json(SYSTEM_PROMPT, retry_prompt, RR_RESUME_JSON_SCHEMA)
        verify_truthfulness(base_resume, result)
    return result

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
    sections = resume.get("sections", {})
    for section_key in ("experience", "education"):
        section = sections.get(section_key, {})
        for item in section.get("items", []):
            data = item.get("data", {})
            for field in ("company", "institution", "name"):
                val = data.get(field, "")
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


SYSTEM_PROMPT: str = """You are a resume tailoring assistant. Follow these rules strictly:

1. You tailor an existing resume to a job description. You may rephrase, reorder, and emphasize. You MAY NOT invent.
2. You MUST NOT add any employer, job title, company, employment date, degree, certification, or quantitative metric that is not present in the input base resume.
3. If a relevant skill is missing from the base resume, do NOT add it; instead, surface adjacent skills that ARE present.
4. Reorder bullets within a job by relevance to the target role; rewrite phrasing for clarity and keyword alignment with the job description; you may drop low-relevance bullets but never invent new ones.
5. Regenerate the summary section to target the role using only facts from the base resume.
6. Reorder skills by relevance to the job.
7. Output strictly valid JSON conforming to the provided schema. No prose."""


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
        "Regenerate from the base resume. Do not iterate on any previous tailored version."
    )
    parts.append("Output strictly valid JSON conforming to the provided schema. No prose.")

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

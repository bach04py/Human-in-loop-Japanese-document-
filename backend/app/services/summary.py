import json
import os
import httpx
from typing import Dict, Any, List


class SummaryService:
    """Dynamic Summary Agent: Generates summaries based on document context."""

    def __init__(self):
        self.local_llm_url = os.environ.get("LLM_ENDPOINT", "http://127.0.0.1:11434/api/generate")
        self.model_name = os.environ.get("LLM_MODEL", "qwen2.5")

    async def generate(self, extracted_data: Dict[str, Any], validation_issues: List[Any],
                       document_type: str = "document") -> str:

        # Format the issues to be readable for the LLM
        if validation_issues:
            issue_texts = [f"[{i.severity.upper()}] {i.field}: {i.message}" for i in validation_issues]
            issues_str = "\n".join(issue_texts)
        else:
            issues_str = "None. Document is fully valid."

        # Dynamic Prompting
        prompt = (
            f"You are a precise data-entry assistant. Review the extracted {document_type} JSON and the validation issues below.\n"
            "Write a strict 2-sentence summary.\n"
            f"Sentence 1: Summarize the core identifying details of this {document_type} (e.g., primary entities involved, ID numbers, dates, or total values). If critical data is missing, state it.\n"
            "Sentence 2: State clearly if this document requires human review based strictly on the Validation Issues provided.\n\n"
            f"=== Extracted JSON ===\n{json.dumps(extracted_data, ensure_ascii=False)}\n\n"
            f"=== Validation Issues ===\n{issues_str}"
        )

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9
            }
        }

        timeout_settings = httpx.Timeout(30.0)

        async with httpx.AsyncClient(timeout=timeout_settings) as client:
            try:
                response = await client.post(self.local_llm_url, json=payload)
                response.raise_for_status()
                result_data = response.json()
                return result_data.get("response",
                                       "System Alert: Summary generation succeeded but returned empty text.").strip()

            except httpx.TimeoutException:
                return "System Alert: Summary generation timed out. Human review required."
            except Exception as e:
                return f"System Alert: Summary generation failed ({type(e).__name__}). Human review required."
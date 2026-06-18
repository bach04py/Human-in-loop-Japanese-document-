import json
import os
import httpx
from typing import Dict, Any, List


class SummaryService:
    """Week 3 Summary Agent: Generates a human-readable summary of the extraction."""

    def __init__(self):
        self.local_llm_url = os.environ.get("LLM_ENDPOINT", "http://127.0.0.1:11434/api/generate")
        self.model_name = os.environ.get("LLM_MODEL", "qwen2.5")

    async def generate(self, extracted_data: Dict[str, Any], validation_issues: List[Any]) -> str:
        # Format the issues to be readable for the LLM
        if validation_issues:
            issue_texts = [f"[{i.severity.upper()}] {i.field}: {i.message}" for i in validation_issues]
            issues_str = "\n".join(issue_texts)
        else:
            issues_str = "None. Document is fully valid."

        # structured Prompt
        prompt = (
            "You are a fast, precise routing assistant. Look at the extracted document JSON and the validation issues below.\n"
            "Write a strict 2-sentence summary.\n"
            "Sentence 1: State the company name, grand total, and date. If a value is null, explicitly state that it is missing.\n"
            "Sentence 2: State if the document requires human review based strictly on the validation issues provided.\n\n"
            f"=== Extracted JSON ===\n{json.dumps(extracted_data, ensure_ascii=False)}\n\n"
            f"=== Validation Issues ===\n{issues_str}"
        )

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,  # Lower temperature = less creative, more factual
                "top_p": 0.9
            }
        }

        # Call Qwen 2.5 with a strict 30-second timeout
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
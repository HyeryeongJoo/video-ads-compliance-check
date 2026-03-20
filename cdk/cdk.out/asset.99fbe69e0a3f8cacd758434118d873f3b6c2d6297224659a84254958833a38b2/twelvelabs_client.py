import json
import re
import time

from twelvelabs import TwelveLabs
from twelvelabs.models.task import Task

from config import settings

COMPLIANCE_PROMPT = """You are an expert ad compliance reviewer for a global makeup and cosmetics brand's paid social campaign.

Analyze this video thoroughly across all modalities (visuals, speech, on-screen text) and return a JSON response with the following structure:

{
  "video_description": "2-5 sentence summary of what happens in the video",
  "campaign_relevance": {
    "score": <0-100>,
    "label": "ON-BRIEF" or "OFF-BRIEF",
    "reasoning": "brief explanation"
  },
  "policy_violations": [
    {
      "category": "<one of: Hate/Harassment, Profanity/Explicit Language, Drugs/Illegal Behavior, Unsafe Product Usage, Medical/Cosmetic Claims>",
      "severity": "NONE" | "LOW" | "MEDIUM" | "HIGH",
      "evidence": [
        {
          "timestamp": "MM:SS - MM:SS",
          "description": "what was detected",
          "modality": "visual" | "speech" | "text_on_screen"
        }
      ]
    }
  ],
  "decision": "APPROVE" | "REVIEW" | "BLOCK",
  "explanation": "Clear explanation of the decision for the advertiser"
}

Policy Rules:
1. Hate/Harassment: No hate speech, discriminatory language, bullying, or harassment.
2. Profanity/Explicit Language: Limited tolerance for profanity. Mild language may pass, strong/repeated profanity should be flagged.
3. Drugs/Illegal Behavior: No drug use, illegal substances, or illegal activity.
4. Unsafe Product Usage: No misuse of cosmetic products (e.g. applying products dangerously near eyes, harmful techniques). Normal makeup application (eyeshadow, eyeliner, etc.) is acceptable.
5. Medical/Cosmetic Claims: No unverified medical claims, "cure" language, or guaranteed transformation results. Subjective opinions ("I love how this looks") are fine.

Campaign Brief: Global makeup/cosmetics brand promoting a new product line through creator-generated beauty videos (tutorials, product demos, "get ready with me" content).

Decision Criteria:
- APPROVE: No violations, clearly on-brief
- REVIEW: Minor/ambiguous violations or borderline relevance (needs human review)
- BLOCK: Severe violations or clearly off-brief/unrelated content

For each of the 5 policy categories, you MUST include an entry in policy_violations (even if severity is NONE).
Return ONLY valid JSON, no markdown formatting."""


class TwelveLabsClient:
    def __init__(self):
        self._client = TwelveLabs(api_key=settings.twelvelabs_api_key)
        self._index_id = None

    def _ensure_index(self) -> str:
        if self._index_id:
            return self._index_id

        indexes = list(self._client.index.list())
        for idx in indexes:
            if idx.name == settings.twelvelabs_index_name:
                self._index_id = idx.id
                return self._index_id

        index = self._client.index.create(
            name=settings.twelvelabs_index_name,
            engines=[
                {
                    "name": "pegasus1.2",
                    "options": ["visual", "conversation", "text_in_video"],
                }
            ],
        )
        self._index_id = index.id
        return self._index_id

    def index_video(self, video_path: str, callback=None) -> str:
        index_id = self._ensure_index()
        task = self._client.task.create(
            index_id=index_id,
            file=video_path,
        )
        if callback:
            callback(f"Video uploaded. Task ID: {task.id}. Waiting for indexing...")
        task = self._wait_for_task(task, callback=callback)
        return task.video_id

    def _wait_for_task(self, task: Task, timeout: int = 600, callback=None) -> Task:
        start = time.time()
        while time.time() - start < timeout:
            task = self._client.task.retrieve(task.id)
            if task.status == "ready":
                if callback:
                    callback("Indexing complete!")
                return task
            if task.status == "failed":
                raise RuntimeError(f"TwelveLabs task failed: {task.id}")
            if callback:
                elapsed = int(time.time() - start)
                callback(f"Indexing in progress... ({elapsed}s)")
            time.sleep(5)
        raise TimeoutError(f"TwelveLabs task timed out: {task.id}")

    def analyze_compliance(self, video_id: str) -> dict:
        result = self._client.generate.text(
            video_id=video_id,
            prompt=COMPLIANCE_PROMPT,
        )
        return self._parse_response(result.data)

    def _parse_response(self, text: str) -> dict:
        cleaned = text.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {
                "video_description": text[:500],
                "campaign_relevance": {"score": 50, "label": "ON-BRIEF", "reasoning": "Parse error"},
                "policy_violations": [],
                "decision": "REVIEW",
                "explanation": f"Could not parse structured response. Raw: {text[:200]}",
            }


tl_client = TwelveLabsClient()

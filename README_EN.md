# Video Ad Compliance & Brand Safety System

Automated compliance review system for creator video ads, powered by the TwelveLabs API.

## Demo

Below is a screenshot of an actual compliance analysis result after uploading a cosmetics makeup video.

![Analyze Results](img/block-result-capture.png)

When a video is uploaded, TwelveLabs' multimodal AI comprehensively analyzes the video's visuals, audio, and text to produce:

- **Decision (APPROVE)**: Video is compliant with no policy violations and aligns with the campaign brief
- **Campaign Relevance (90/100)**: High relevance confirmed as a makeup tutorial/product demo
- **Video Description**: Auto-generated 2-5 sentence summary of the video content
- **Decision Explanation**: Clear rationale for the decision, ready to share with the advertiser
- **Policy Violations (5 categories)**: Individual severity ratings across all 5 policy categories

In the example above, all categories returned `NONE`, resulting in an **APPROVE** decision.

---

## TwelveLabs API Usage

This system combines three core TwelveLabs APIs to automate the full pipeline: **Video Upload → Multimodal Indexing → Compliance Analysis**.

### SDK & Import Information

| Item | Value |
|---|---|
| **Package** | `twelvelabs` (PyPI) |
| **Version** | `0.4.4` |
| **API Version** | `v1.3` |
| **Install** | `pip install twelvelabs==0.4.4` |

```python
# SDK client (used for Index API and Task API)
from twelvelabs import TwelveLabs
from twelvelabs.models.task import Task

client = TwelveLabs(api_key="YOUR_API_KEY")

# Analyze API is not included in the SDK — called directly via httpx REST
import httpx
```

- `TwelveLabs` — Main SDK client. Calls APIs through resource-based namespaces such as `client.index.*`, `client.task.*`
- `Task` — Return type for `task.create()` / `task.retrieve()`. Provides attributes like `task.id`, `task.status`, `task.video_id`
- `httpx` — The Analyze API (`POST /v1.3/analyze`) is not directly supported in SDK `0.4.4`, so it is called via REST

### 1. Index API — Video Index Management

> **File**: `app/twelvelabs_client.py` (`_ensure_index` method)

| Endpoint | SDK Method | Role |
|---|---|---|
| `GET /indexes` | `client.index.list()` | List existing indexes |
| `POST /indexes` | `client.index.create()` | Create a new index |

**Role in this system**: Manages the index, which is a prerequisite for all video analysis. An index is a logical container where videos are embedded and stored by the Pegasus model. On system startup, it checks whether an index named `ad-compliance` exists, and creates one automatically if not.

```python
index = self._client.index.create(
    name="ad-compliance",
    models=[{
        "name": "pegasus1.2",
        "options": ["visual", "audio"],
    }],
)
```

- **Model**: `pegasus1.2` — TwelveLabs' multimodal video embedding model
- **Modalities**: `visual` + `audio` — Indexes both visual information (frames, text OCR) and audio (speech, sounds)
- This configuration enables the subsequent Analyze API to leverage visuals, speech, and on-screen text

### 2. Task API — Video Upload & Indexing

> **File**: `app/twelvelabs_client.py` (`index_video`, `_wait_for_task` methods)

| Endpoint | SDK Method | Role |
|---|---|---|
| `POST /tasks` | `client.task.create(index_id, file=...)` | Upload a local file for indexing |
| `GET /tasks/{id}` | `client.task.retrieve(task_id)` | Poll indexing task status |

**Role in this system**: Sends the user-submitted video to the TwelveLabs platform and waits for the Pegasus model to analyze all frames, speech, and on-screen text to generate multimodal embeddings. The Analyze API can only perform compliance review after this step is complete.

**Asynchronous task polling**: The Task API operates asynchronously, so `task.retrieve()` is called every 5 seconds until the `status` becomes `ready` (with a maximum timeout of 600 seconds). Once indexing is complete, the `video_id` is returned and passed to the next step.

### 3. Analyze API — Multimodal Video Compliance Analysis

> **File**: `app/twelvelabs_client.py` (`analyze_compliance` method)

| Endpoint | Method | Role |
|---|---|---|
| `POST /v1.3/analyze` | REST (httpx) | Natural language prompt-based multimodal analysis of video |

**Role in this system**: This is the **core API** of the system. It sends a custom compliance prompt for an indexed video, and TwelveLabs comprehensively analyzes the video's **visual**, **speech**, and **text_on_screen** modalities to return a structured compliance report.

```python
resp = httpx.post(
    "https://api.twelvelabs.io/v1.3/analyze",
    headers={"x-api-key": API_KEY},
    json={
        "video_id": video_id,
        "prompt": COMPLIANCE_PROMPT,
        "stream": False,
    },
)
```

**Analysis items requested by the prompt**:

| Item | Description | TwelveLabs' Role |
|---|---|---|
| `video_description` | 2-5 sentence summary of video content | Understands video content by combining visual + audio + text |
| `campaign_relevance` | Campaign brief alignment score (0-100) | Multimodal assessment of whether the video is makeup/beauty content |
| `policy_violations` | Violation status + evidence per 5 categories | Extracts which modality detected a violation at specific timestamps |
| `decision` | APPROVE / REVIEW / BLOCK | Final decision based on comprehensive analysis |
| `explanation` | Decision rationale for the advertiser | Generates natural language explanation of the decision |

**Why the TwelveLabs Analyze API is essential**:
- General LLMs cannot directly understand video, but TwelveLabs uses a video-native multimodal model to **simultaneously process frame-level visual information, speech transcription, and OCR text**
- A single API call can extract **timestamp-based evidence** for the entire video — structured responses showing "what was detected, by which modality, in which MM:SS - MM:SS segment"
- Custom prompts enable **domain-specific policy analysis (ad compliance)**, allowing flexible brand safety criteria — unlike generic video classification APIs

### API Flow Summary

```
User uploads a video file
         │
         ▼
┌─────────────────────────┐
│  1. Index API           │  Check if index exists → create if not
│     index.list()        │  (Pegasus 1.2, visual+audio)
│     index.create()      │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  2. Task API            │  Send video to TwelveLabs
│     task.create(file)   │  → Wait for multimodal embedding generation
│     task.retrieve()     │  → Poll until status=ready
└────────────┬────────────┘
             │ video_id returned
             ▼
┌─────────────────────────┐
│  3. Analyze API         │  Send compliance prompt
│     POST /v1.3/analyze  │  → Comprehensive visual/audio/text analysis
│                         │  → Structured JSON report returned
└────────────┬────────────┘
             │
             ▼
   Display results in Streamlit UI
   + Store in S3/DynamoDB
```

---

## Architecture

- **App**: Streamlit (single ECS Fargate container)
- **Video Analysis**: TwelveLabs API (Index + Task + Analyze)
- **Storage**: S3 (videos, 7-day lifecycle) + DynamoDB (results, 30-day TTL)
- **CDN**: CloudFront (HTTPS enforced, ALB restricted to CloudFront IPs only)
- **IaC**: AWS CDK (Python, 4 stacks)

## Quick Start (Local)

```bash
cd app
cp .env.example .env  # Set your TwelveLabs API key
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Deploy to AWS

```bash
# 1. Store TwelveLabs API key in Secrets Manager
aws secretsmanager create-secret --name twelvelabs-api-key --secret-string "your-key"

# 2. Deploy all stacks
cd cdk
pip install -r requirements.txt
npx aws-cdk bootstrap
npx aws-cdk deploy --all
```

## Video Input

| Method | Supported | How |
|---|---|---|
| File Upload (.mp4, .mov, .avi, .webm) | Yes | TwelveLabs Task API (file) |

## Policy Categories (5)

1. Hate / Harassment
2. Profanity / Explicit Language
3. Drugs / Illegal Behavior
4. Unsafe or Misleading Product Usage
5. Medical / Cosmetic Claims

## Decision Output

- **APPROVE**: No violations, clearly on-brief
- **REVIEW**: Minor/ambiguous violations or borderline relevance
- **BLOCK**: Severe violations or off-brief content

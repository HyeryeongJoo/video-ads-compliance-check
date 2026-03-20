# Video Ad Compliance & Brand Safety System

TwelveLabs API를 활용한 크리에이터 영상 광고 컴플라이언스 자동 심사 시스템.

## Architecture

- **App**: Streamlit (단일 ECS Fargate 컨테이너)
- **Video Analysis**: TwelveLabs API (Task + Analyze)
- **Storage**: S3 (videos) + DynamoDB (results)
- **CDN**: CloudFront (HTTPS, ALB는 CloudFront IP만 허용)
- **IaC**: AWS CDK (Python, 4 stacks)

## Quick Start (Local)

```bash
cd app
cp ../backend/.env.example .env  # Set your TwelveLabs API key
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
| Direct Video URL (.mp4) | Yes | TwelveLabs Task API (url) |
| YouTube/Vimeo page URL | No | Platform bot detection blocks cloud IPs |

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

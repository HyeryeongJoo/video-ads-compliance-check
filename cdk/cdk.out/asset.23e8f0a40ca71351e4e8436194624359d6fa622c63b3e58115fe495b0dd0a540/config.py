from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    twelvelabs_api_key: str = ""
    twelvelabs_index_name: str = "ad-compliance"
    s3_bucket: str = "video-compliance-assets"
    dynamodb_table: str = "ComplianceResults"
    aws_region: str = "us-east-1"
    max_video_duration_sec: int = 600
    max_video_resolution: str = "720"
    temp_dir: str = "/tmp/videos"

    class Config:
        env_file = ".env"


settings = Settings()

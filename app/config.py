from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    twelvelabs_api_key: str = ""
    twelvelabs_index_name: str = "ad-compliance"
    s3_bucket: str = "video-compliance-assets"
    dynamodb_table: str = "ComplianceResults"
    aws_region: str = "us-east-1"
    temp_dir: str = "/tmp/videos"

    class Config:
        env_file = ".env"


settings = Settings()

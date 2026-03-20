import json
import os
import time
import uuid

import boto3
from botocore.exceptions import ClientError

from config import settings


class StorageService:
    def __init__(self):
        self._s3 = boto3.client("s3", region_name=settings.aws_region)
        self._dynamodb = boto3.resource("dynamodb", region_name=settings.aws_region)
        self._table = self._dynamodb.Table(settings.dynamodb_table)

    def generate_request_id(self) -> str:
        return str(uuid.uuid4())

    def upload_video_to_s3(self, local_path: str, request_id: str) -> str:
        ext = os.path.splitext(local_path)[1] or ".mp4"
        s3_key = f"videos/{request_id}/original{ext}"
        self._s3.upload_file(local_path, settings.s3_bucket, s3_key)
        return s3_key

    def save_result(self, request_id: str, result: dict) -> None:
        item = {
            "request_id": request_id,
            "timestamp": int(time.time()),
            "ttl": int(time.time()) + 30 * 86400,  # 30 days
            **result,
        }
        # DynamoDB can't store empty strings; convert them
        item = _sanitize_for_dynamodb(item)
        self._table.put_item(Item=item)

    def get_result(self, request_id: str) -> dict | None:
        try:
            resp = self._table.get_item(Key={"request_id": request_id})
            return resp.get("Item")
        except ClientError:
            return None

    def list_results(self, limit: int = 20) -> list[dict]:
        resp = self._table.scan(Limit=limit)
        items = resp.get("Items", [])
        return sorted(items, key=lambda x: x.get("timestamp", 0), reverse=True)


def _sanitize_for_dynamodb(obj):
    if isinstance(obj, dict):
        return {k: _sanitize_for_dynamodb(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_dynamodb(v) for v in obj]
    if isinstance(obj, float):
        from decimal import Decimal
        return Decimal(str(obj))
    return obj


storage_service = StorageService()

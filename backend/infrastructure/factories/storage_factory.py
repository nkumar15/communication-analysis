import os
from minio import Minio

class StorageFactory:
    @staticmethod
    def get_storage_client() -> Minio:
        """
        Returns a configured MinIO client instance.
        """
        endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000")
        access_key = os.getenv("MINIO_ROOT_USER", "minioadmin")
        secret_key = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")
        secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
        
        return Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )

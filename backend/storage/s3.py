"""
S3 file storage backend
Implements StorageBackend interface for AWS S3 (or compatible services)
"""

import boto3
from botocore.exceptions import ClientError
from typing import BinaryIO, Union, Optional
from uuid import UUID
import logging
import tempfile
import os
from pathlib import Path

from backend.config import settings
from backend.storage.base import StorageBackend

logger = logging.getLogger(__name__)


class S3Storage(StorageBackend):
    """S3 file storage with user-scoped paths"""

    def __init__(
        self,
        bucket_name: str = None,
        aws_access_key_id: str = None,
        aws_secret_access_key: str = None,
        region_name: str = None,
        endpoint_url: str = None
    ):
        """
        Initialize S3 storage backend

        Args:
            bucket_name: S3 bucket name
            aws_access_key_id: AWS access key (optional, uses env/IAM if not provided)
            aws_secret_access_key: AWS secret key (optional)
            region_name: AWS region (optional)
            endpoint_url: Custom S3 endpoint (for MinIO, DigitalOcean Spaces, etc.)
        """
        self.bucket_name = bucket_name or settings.S3_BUCKET_NAME

        # Initialize S3 client
        s3_config = {}
        if aws_access_key_id:
            s3_config['aws_access_key_id'] = aws_access_key_id
        if aws_secret_access_key:
            s3_config['aws_secret_access_key'] = aws_secret_access_key
        if region_name:
            s3_config['region_name'] = region_name
        if endpoint_url:
            s3_config['endpoint_url'] = endpoint_url

        self.s3_client = boto3.client('s3', **s3_config)

        # Verify bucket exists
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Connected to S3 bucket: {self.bucket_name}")
        except ClientError as e:
            logger.error(f"S3 bucket {self.bucket_name} not accessible: {e}")
            raise

    def _get_document_key(
        self,
        user_id: UUID,
        collection_id: UUID,
        document_id: UUID,
        filename: str
    ) -> str:
        """Generate S3 key for document"""
        return (
            f"users/{user_id}/"
            f"collections/{collection_id}/"
            f"documents/{document_id}/"
            f"{filename}"
        )

    def _get_extracted_content_key(
        self,
        user_id: UUID,
        collection_id: UUID,
        document_id: UUID,
        content_type: str,
        filename: str
    ) -> str:
        """Generate S3 key for extracted content"""
        type_dir = content_type.split('/')[0] + 's'  # 'image' -> 'images'
        return (
            f"users/{user_id}/"
            f"collections/{collection_id}/"
            f"documents/{document_id}/"
            f"{type_dir}/"
            f"{filename}"
        )

    def save(
        self,
        file: Union[BinaryIO, bytes],
        user_id: UUID,
        collection_id: UUID,
        document_id: UUID,
        filename: str,
        content_type: Optional[str] = None
    ) -> str:
        """Save file to S3 with user-scoped key"""
        s3_key = self._get_document_key(user_id, collection_id, document_id, filename)

        # Prepare content
        if isinstance(file, bytes):
            content = file
        else:
            if hasattr(file, 'read'):
                content = file.read()
                # Reset file pointer if possible
                if hasattr(file, 'seek'):
                    file.seek(0)
            else:
                content = file

        # Prepare metadata
        extra_args = {
            'Metadata': {
                'user_id': str(user_id),
                'collection_id': str(collection_id),
                'document_id': str(document_id)
            }
        }
        if content_type:
            extra_args['ContentType'] = content_type

        # Upload to S3
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=content,
                **extra_args
            )
            logger.info(f"Uploaded file to S3: {s3_key}")
            return s3_key
        except ClientError as e:
            logger.error(f"Failed to upload to S3: {e}")
            raise

    def save_extracted_content(
        self,
        content: bytes,
        user_id: UUID,
        collection_id: UUID,
        document_id: UUID,
        content_type: str,
        filename: str
    ) -> str:
        """Save extracted content to S3"""
        s3_key = self._get_extracted_content_key(
            user_id, collection_id, document_id, content_type, filename
        )

        extra_args = {
            'ContentType': content_type,
            'Metadata': {
                'user_id': str(user_id),
                'collection_id': str(collection_id),
                'document_id': str(document_id),
                'content_type': content_type
            }
        }

        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=content,
                **extra_args
            )
            logger.info(f"Uploaded extracted content to S3: {s3_key}")
            return s3_key
        except ClientError as e:
            logger.error(f"Failed to upload extracted content to S3: {e}")
            raise

    def get_url(
        self,
        storage_path: str,
        user_id: UUID,
        expires_in: int = 3600
    ) -> str:
        """Generate pre-signed URL for S3 object"""
        # Verify the path belongs to the user (security check)
        if not storage_path.startswith(f"users/{user_id}/"):
            raise PermissionError(f"Access denied: file does not belong to user {user_id}")

        try:
            presigned_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': storage_path
                },
                ExpiresIn=expires_in
            )
            return presigned_url
        except ClientError as e:
            logger.error(f"Failed to generate pre-signed URL: {e}")
            raise

    def read(self, storage_path: str, user_id: UUID) -> bytes:
        """Read file content from S3 with user verification"""
        # Verify the path belongs to the user (security check)
        if not storage_path.startswith(f"users/{user_id}/"):
            raise PermissionError(f"Access denied: file does not belong to user {user_id}")

        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=storage_path
            )
            return response['Body'].read()
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise FileNotFoundError(f"File not found: {storage_path}")
            logger.error(f"Failed to read from S3: {e}")
            raise

    def exists(self, storage_path: str, user_id: UUID) -> bool:
        """Check if file exists in S3 and belongs to user"""
        # Verify the path belongs to the user
        if not storage_path.startswith(f"users/{user_id}/"):
            return False

        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=storage_path
            )
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise

    def delete(self, storage_path: str, user_id: UUID):
        """Delete file from S3 with user verification"""
        # Verify the path belongs to the user (security check)
        if not storage_path.startswith(f"users/{user_id}/"):
            raise PermissionError(f"Access denied: file does not belong to user {user_id}")

        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=storage_path
            )
            logger.info(f"Deleted file from S3: {storage_path}")
        except ClientError as e:
            logger.error(f"Failed to delete from S3: {e}")
            raise

    def delete_collection(self, user_id: UUID, collection_id: UUID):
        """Delete all files for a collection from S3"""
        prefix = f"users/{user_id}/collections/{collection_id}/"

        try:
            # List all objects with this prefix
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)

            # Collect all object keys
            objects_to_delete = []
            for page in pages:
                if 'Contents' in page:
                    objects_to_delete.extend([{'Key': obj['Key']} for obj in page['Contents']])

            # Delete objects in batches (S3 allows max 1000 per request)
            if objects_to_delete:
                for i in range(0, len(objects_to_delete), 1000):
                    batch = objects_to_delete[i:i + 1000]
                    self.s3_client.delete_objects(
                        Bucket=self.bucket_name,
                        Delete={'Objects': batch}
                    )
                logger.info(f"Deleted {len(objects_to_delete)} objects for collection {collection_id}")
        except ClientError as e:
            logger.error(f"Failed to delete collection from S3: {e}")
            raise

    def delete_user_data(self, user_id: UUID):
        """Delete all files for a user from S3"""
        prefix = f"users/{user_id}/"

        try:
            # List all objects with this prefix
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)

            # Collect all object keys
            objects_to_delete = []
            for page in pages:
                if 'Contents' in page:
                    objects_to_delete.extend([{'Key': obj['Key']} for obj in page['Contents']])

            # Delete objects in batches
            if objects_to_delete:
                for i in range(0, len(objects_to_delete), 1000):
                    batch = objects_to_delete[i:i + 1000]
                    self.s3_client.delete_objects(
                        Bucket=self.bucket_name,
                        Delete={'Objects': batch}
                    )
                logger.info(f"Deleted {len(objects_to_delete)} objects for user {user_id}")
        except ClientError as e:
            logger.error(f"Failed to delete user data from S3: {e}")
            raise

    def get_local_path(self, storage_path: str, user_id: UUID) -> str:
        """
        Download S3 file to temp directory and return local path

        WARNING: Caller is responsible for cleanup of temp file after use!
        The temp file will NOT be automatically deleted.

        Args:
            storage_path: S3 key of the file
            user_id: Owner user ID (for verification)

        Returns:
            str: Temporary local file path

        Raises:
            PermissionError: If file doesn't belong to user
            FileNotFoundError: If file doesn't exist
        """
        # Verify the path belongs to the user (security check)
        if not storage_path.startswith(f"users/{user_id}/"):
            raise PermissionError(f"Access denied: file does not belong to user {user_id}")

        # Extract filename from S3 key
        filename = Path(storage_path).name

        # Create temp file with same extension
        suffix = Path(filename).suffix
        temp_file = tempfile.NamedTemporaryFile(
            delete=False,  # Don't auto-delete, caller manages cleanup
            suffix=suffix,
            prefix=f"mnemosyne_s3_"
        )

        try:
            # Download from S3 to temp file
            self.s3_client.download_file(
                Bucket=self.bucket_name,
                Key=storage_path,
                Filename=temp_file.name
            )
            logger.info(f"Downloaded S3 file to temp: {temp_file.name}")
            return temp_file.name

        except ClientError as e:
            # Clean up temp file if download failed
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)

            if e.response['Error']['Code'] == '404':
                raise FileNotFoundError(f"File not found in S3: {storage_path}")
            logger.error(f"Failed to download from S3: {e}")
            raise
        finally:
            temp_file.close()

import logging
import os
from typing import Optional, BinaryIO
import tempfile
import uuid
from azure.storage.blob import BlobServiceClient, ContainerClient, BlobClient
from datetime import datetime, timedelta

class StorageService:
    def __init__(self, connection_string: Optional[str] = None):
        """Initialize StorageService with Azure Storage connection string."""
        self.connection_string = connection_string or os.getenv("STORAGE_CONNECTION_STRING")
        if not self.connection_string:
            raise ValueError("Storage connection string not provided")
        
        self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
        self.container_name = "audio-processing"
        self._ensure_container_exists()

    def _ensure_container_exists(self) -> None:
        """Ensure the container exists, create if it doesn't."""
        try:
            self.blob_service_client.create_container_if_not_exists(
                name=self.container_name
            )
            logging.info(f"Container {self.container_name} is ready")
        except Exception as e:
            logging.error(f"Error initializing container: {str(e)}")
            raise

    async def upload_file(self, file_path: str, blob_name: Optional[str] = None) -> str:
        """
        Upload a file to blob storage.
        Returns the blob name.
        """
        try:
            if not blob_name:
                # Generate a unique blob name if none provided
                extension = os.path.splitext(file_path)[1]
                blob_name = f"{uuid.uuid4()}{extension}"

            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, 
                blob=blob_name
            )

            with open(file_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=True)
                logging.info(f"Uploaded {file_path} to blob {blob_name}")
            
            return blob_name

        except Exception as e:
            logging.error(f"Error uploading file {file_path}: {str(e)}")
            raise

    async def download_file(self, blob_name: str, destination_path: Optional[str] = None) -> str:
        """
        Download a file from blob storage.
        If no destination_path is provided, creates a temporary file.
        Returns the path to the downloaded file.
        """
        try:
            if not destination_path:
                # Create a temporary file with the same extension
                _, extension = os.path.splitext(blob_name)
                temp_file = tempfile.NamedTemporaryFile(suffix=extension, delete=False)
                destination_path = temp_file.name
                temp_file.close()

            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, 
                blob=blob_name
            )

            with open(destination_path, "wb") as file:
                blob_data = blob_client.download_blob()
                blob_data.readinto_file(file)
                logging.info(f"Downloaded blob {blob_name} to {destination_path}")

            return destination_path

        except Exception as e:
            logging.error(f"Error downloading blob {blob_name}: {str(e)}")
            raise

    async def delete_blob(self, blob_name: str) -> None:
        """Delete a blob from storage."""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, 
                blob=blob_name
            )
            blob_client.delete_blob()
            logging.info(f"Deleted blob {blob_name}")

        except Exception as e:
            logging.error(f"Error deleting blob {blob_name}: {str(e)}")
            # Don't raise the exception for deletion errors
            # as this is typically cleanup code

    async def cleanup_old_blobs(self, max_age_hours: int = 24) -> int:
        """
        Clean up blobs older than specified hours.
        Returns number of blobs deleted.
        """
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            blobs_deleted = 0
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)

            for blob in container_client.list_blobs():
                if blob.last_modified < cutoff_time:
                    await self.delete_blob(blob.name)
                    blobs_deleted += 1

            logging.info(f"Cleaned up {blobs_deleted} old blobs")
            return blobs_deleted

        except Exception as e:
            logging.error(f"Error during blob cleanup: {str(e)}")
            return 0
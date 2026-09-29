import os
import json
from typing import Any, Dict
from google.cloud import storage

def download_gcs_file(gcs_uri: str, local_dir: str) -> str:
    """Downloads a single GCS file to a local directory and returns local path."""
    client = storage.Client()
    path_parts = gcs_uri.replace("gs://", "").split("/")
    bucket_name = path_parts[0]
    blob_path = "/".join(path_parts[1:])
    
    filename = os.path.basename(blob_path)
    local_path = os.path.join(local_dir, filename)
    
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    blob.download_to_filename(local_path)
    return local_path

def upload_folder_to_gcs(local_dir: str, gcs_output_path: str):
    """Uploads all files in a local directory to a target GCS folder path."""
    client = storage.Client()
    path_parts = gcs_output_path.replace("gs://", "").rstrip("/").split("/")
    bucket_name = path_parts[0]
    prefix = "/".join(path_parts[1:])
    
    bucket = client.bucket(bucket_name)
    for root, _, files in os.walk(local_dir):
        for file in files:
            local_file_path = os.path.join(root, file)
            relative_path = os.path.relpath(local_file_path, local_dir)
            blob_path = f"{prefix}/{relative_path}" if prefix else relative_path
            
            blob = bucket.blob(blob_path)
            blob.upload_from_filename(local_file_path)
            print(f"[MODEL] Uploaded {file} -> gs://{bucket_name}/{blob_path}")

def write_json_output_to_gcs(data: dict, target_uri: str) -> None:
    """
    Writes a dictionary as a JSON file to a target GCS URI.
    """
    print(f"[RUNNER] Writing JSON results to {target_uri}...", flush=True)
    if not target_uri.startswith("gs://"):
        raise ValueError(f"Output URI must start with gs://. Got: {target_uri}")

    path_parts = target_uri.replace("gs://", "").split("/")
    bucket_name = path_parts[0]
    blob_path = "/".join(path_parts[1:])

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)

    blob.upload_from_string(
        json.dumps(data, indent=2),
        content_type="application/json"
    )
    print(f"[RUNNER] Successfully wrote output to {target_uri}", flush=True)

def load_json_from_uri(uri: str) -> Dict[str, Any]:
    """
    Reads and parses a JSON file from a local filesystem path or a GCS URI (gs://bucket/path).
    """

    if uri.startswith("gs://"):
        # Parse GCS bucket and blob path
        path_parts = uri[5:].split("/", 1)
        bucket_name = path_parts[0]
        blob_path = path_parts[1] if len(path_parts) > 1 else ""

        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        content = blob.download_as_text()
        return json.loads(content)
    else:
        # Load local file path
        with open(uri, "r", encoding="utf-8") as f:
            return json.load(f)

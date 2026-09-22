import os
import sys
from pathlib import Path
from google.cloud import storage

from utils.payload_utils import (
    load_json_from_uri,
    parse_execution_payload,
)
from utils.utils import ( write_json_output_to_gcs)

# Direct import of model execution logic
import model

# Default path to the schema within the repo
SCHEMA_PATH = Path(__file__).parent / "json_schema" / "inference_runner_schema.json"

def main():
    print("==================================================", flush=True)
    print("  Starting Direct Inference Runner                ", flush=True)
    print("==================================================", flush=True)

    payload_path = os.environ.get("INPUT_PAYLOAD_PATH")

    if not payload_path:
        print("[RUNNER] Error: INPUT_PAYLOAD_PATH environment variable is not set.", flush=True)
        sys.exit(1)

    try:
        print(f"[RUNNER] Fetching payload from {payload_path}...", flush=True)
        payload_data = load_json_from_uri(payload_path)
        
        print(f"[RUNNER] Validating payload against {SCHEMA_PATH}...", flush=True)
        jobs = parse_execution_payload(payload_data, schema_path=str(SCHEMA_PATH))
        
        # Single job contract for direct execution
        job = jobs[0]

        print(f"[RUNNER] Input Files: {job['input_files']}", flush=True)
        print(f"[RUNNER] Output Path: {job.get('output_path')}", flush=True)
        print(f"[RUNNER] JSON Output Location: {job.get('json_output_location')}", flush=True)

        # Execute model directly
        results = model.run_model(
            input_files=job["input_files"],
            output_path=job.get("output_path"),
            config=job.get("config", {})
        )

        # Upload JSON results if requested
        json_out = job.get("json_output_location")
        if json_out:
            write_json_output_to_gcs(results, json_out)

        print("[RUNNER] Execution completed successfully.", flush=True)

    except Exception as e:
        print(f"[RUNNER] Execution failed: {str(e)}", flush=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
import os
import tempfile
import json

from utils.utils import download_gcs_file, upload_folder_to_gcs, write_json_output_to_gcs
import model

def run_job(job):
    """
    High-level entry point invoked by inference_runner.py and app.py.
    
    Handles:
    1. Downloading input files from GCS to a temporary local folder.
    2. Executing run_inference() logic.
    3. Uploading generated output files back to GCS if output_path is provided.
    4. Returning raw JSON dictionary results.
    """
    input_files = job.get('input_files')
    output_path = job.get('output_path', None)
    json_output_location = job.get('json_output_location', None)
    config = job.get('config',  None)

    config = config or {}
    
    with tempfile.TemporaryDirectory() as temp_input_dir, tempfile.TemporaryDirectory() as temp_output_dir:
        print(f"[MODEL] Downloading {len(input_files)} input file(s) from GCS...", flush=True)
        for gcs_uri in input_files:
            download_gcs_file(gcs_uri, temp_input_dir)
            
        local_output_json = os.path.join(temp_output_dir, "predictions.json")
        
        # Invoke original core inference function
        model.run_inference(
            input_dir=temp_input_dir,
            output_file_path=local_output_json,
            config=config
        )
        
        # Read the generated result JSON
        with open(local_output_json, "r", encoding="utf-8") as f:
            results = json.load(f)
            
        # If output_path directory is provided, upload generated output files to GCS
        if output_path:
            print(f"[MODEL] Uploading output files to {output_path}...", flush=True)
            upload_folder_to_gcs(temp_output_dir, output_path)

        if json_output_location:
            write_json_output_to_gcs(results, json_output_location)
        
            
        return results
    
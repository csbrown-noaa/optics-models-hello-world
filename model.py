"""
model.py - The Biologist's Sandbox

Welcome! If you are integrating a new model into the NOAA/NMFS ecosystem, 
THIS IS THE ONLY PYTHON FILE YOU NEED TO EDIT.

The surrounding infrastructure (app.py, inference_runner.py) handles downloading 
files from Google Cloud Storage (GCS), setting up the web server, and uploading 
the final results back to GCS. 

Your goal:
1. Read the input images/videos from `input_dir`.
2. Load any custom weights or configurations from `config`.
3. Run your specific computer vision framework.
4. Save your output to `output_file_path` (we highly encourage KWCOCO format).
"""

import os
import json
import random
import tempfile
import cv2

from utils.utils import download_gcs_file, upload_folder_to_gcs

def run_inference(input_dir: str, output_file_path: str, config: dict):
    """
    Core inference logic. 
    
    Parameters
    ----------
    input_dir : str
        Local directory where all your input images/videos have ALREADY been downloaded.
    output_file_path : str
        The exact local file path where you MUST save your final JSON/KWCOCO results.
    config : dict
        The "config" dictionary passed from the Airflow payload. Contains paths 
        to your downloaded weights, hyperparameters, etc.
    """
    
    print(f"[MODEL] Starting inference...")
    print(f"[MODEL] Scanning {input_dir} for input files...")
    
    # 1. Discover the files that the infrastructure downloaded for you
    input_files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
    
    if not input_files:
        print("[MODEL] WARNING: No input files found in directory!")
        
    # 2. Extract configurations (hyperparameters, thresholds, etc.)
    # In a real model, you'd load your PyTorch/Tensorflow weights here.
    # The config dictionary comes directly from the JSON payload triggered by Airflow.
    conf_thresh = config.get("options", {}).get("conf_thresh", 0.5)
    print(f"[MODEL] Using confidence threshold: {conf_thresh}")
    
    # 3. Setup our output structure (KWCOCO format)
    # KWCOCO is an extension of MS-COCO used widely for CV data.
    kwcoco_output = {
        "info": {"description": "Hello World Fake Model Output"},
        "categories": [
            {"id": 1, "name": "fish"},
            {"id": 2, "name": "coral"}
        ],
        "images": [],
        "annotations": []
    }
    
    # 4. Simulate running inference on each file
    annotation_id = 1
    for image_id, filename in enumerate(input_files, start=1):
        filepath = os.path.join(input_dir, filename)
        
        # Extract actual dimensions from the media file
        width, height = 1920, 1080 # Fallback default
        try:
            # Check if it's likely a video
            if filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                cap = cv2.VideoCapture(filepath)
                if cap.isOpened():
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    cap.release()
            else:
                # Treat as an image
                img = cv2.imread(filepath)
                if img is not None:
                    height, width = img.shape[:2]
        except Exception as e:
            print(f"[MODEL] Warning: Could not read dimensions for {filename}: {e}")

        # Add the image entry to KWCOCO
        kwcoco_output["images"].append({
            "id": image_id,
            "file_name": filename,
            "width": width,
            "height": height 
        })
        
        # Simulate finding 1 to 3 random objects in this file
        num_detections = random.randint(1, 3)
        for _ in range(num_detections):
            # Generate random bounding box [x, y, width, height] bounded by media size
            max_x = max(1, width - 200)
            max_y = max(1, height - 200)
            bbox = [
                random.randint(0, max_x), 
                random.randint(0, max_y), 
                random.randint(50, 200), 
                random.randint(50, 200)
            ]
            
            # Add the annotation entry
            kwcoco_output["annotations"].append({
                "id": annotation_id,
                "image_id": image_id,
                "category_id": random.choice([1, 2]), # random fish or coral
                "bbox": bbox,
                "score": round(random.uniform(conf_thresh, 1.0), 3) # random confidence
            })
            annotation_id += 1
            
        print(f"[MODEL] Processed {filename} ({width}x{height}) - Found {num_detections} objects.")
        
    # 5. Save the output
    # You MUST save your results to the `output_file_path` provided to this function.
    # The infrastructure will automatically grab this file and upload it to GCS.
    print(f"[MODEL] Writing KWCOCO results to {output_file_path}")
    with open(output_file_path, 'w') as f:
        json.dump(kwcoco_output, f, indent=4)
        
    print("[MODEL] Inference complete!")

def run_model(input_files: list, output_path: str = None, config: dict = None) -> dict:
    """
    High-level entry point invoked by inference_runner.py and app.py.
    
    Handles:
    1. Downloading input files from GCS to a temporary local folder.
    2. Executing run_inference() logic.
    3. Uploading generated output files back to GCS if output_path is provided.
    4. Returning raw JSON dictionary results.
    """
    config = config or {}
    
    with tempfile.TemporaryDirectory() as temp_input_dir, tempfile.TemporaryDirectory() as temp_output_dir:
        print(f"[MODEL] Downloading {len(input_files)} input file(s) from GCS...", flush=True)
        for gcs_uri in input_files:
            download_gcs_file(gcs_uri, temp_input_dir)
            
        local_output_json = os.path.join(temp_output_dir, "predictions.json")
        
        # Invoke original core inference function
        run_inference(
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
            
        return results
    
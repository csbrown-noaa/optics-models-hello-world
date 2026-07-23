# NOAA NMFS Optics Model Deployment Template ("Hello World")

Welcome! This repository is a starting template for deploying your custom Computer Vision models into the Optics SI Airflow ecosystem. If you have an Ultralytics-family model or a VIAME-family model 🛑 **STOP!**, there are existing frameworks for that - please use those - it's easier that way. :)

Our infrastructure requires models to run inside isolated Docker containers, expose an HTTP endpoint, and communicate with Google Cloud Storage (GCS). We have pre-written most of this infrastructure for you, so you can just focus on importing your model and getting predictions into the expected shape.

---

# 🟢 Phase 1: Deploying the "Hello World" Baseline

Before writing any custom computer vision code, we are going to deploy this repository exactly as it is. It currently contains a "dummy" model that draws random bounding boxes. 

By deploying this dummy model first, you will verify that your local Docker setup, Google Cloud permissions, and Airflow configurations are working perfectly.

## 🏁 Step 1: Fork and Clone

You will likely need to edit only the `model.py`, which is where your prediction code lives, and the `Dockerfile`, which handles the dependencies of your code and the other base dependencies of the project. The rest of the files (`app.py`, `inference_runner.py`) are abstract plumbing that handle the annoying parts: downloading videos from the cloud, starting web servers, managing memory, and uploading your final results back to the cloud.

Before changing any code, fork this repository and clone it to your local machine (or Google Cloud Workstation). All subsequent commands assume you are running them from the root of this cloned directory.

```bash
git clone https://github.com/csbrown-noaa/optics-models-hello-world.git
cd optics-models-hello-world
```

## 💻 Step 2: Test the Dummy Locally

Before deploying to the cloud, verify the dummy code works on your laptop/workstation.

**1. Authenticate with Google Cloud**
Ensure you have Google Cloud credentials available locally so the container can download the test files:
```bash
gcloud auth application-default login
```

**2. Build the Docker Container**
```bash
docker build -t noaa-my-custom-model:latest .
```

**3. Run the Container**
*(This maps your local GCP credentials into the container so it can access buckets)*
```bash
docker run -p 8080:8080 \
  -v ~/.config/gcloud:/tmp/.config/gcloud \
  -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/.config/gcloud/application_default_credentials.json \
  noaa-my-custom-model:latest
```

**4. Prepare Your Test Payloads**
We have provided template JSON payloads in the local `test_payloads/` directory along with some sample media. 

First, open the JSON files locally on your machine. Replace all the `<TODO_YOUR_FOLDER>` placeholders with a unique folder name you control (e.g., your username).

Next, you must upload the local test images, the test video, and your newly modified `input_manifest.json` up to that exact Google Cloud Storage location (e.g., `gs://ggn-nmfs-osi-dev-1-data/scott/test-images/`). *Without this step, your local Docker container won't have anything to download during the test!*

**5. Send Test Requests**
In a new terminal (while your Docker container is still running), test the different data ingestion methods:

```bash
# Test 1: Single Video
curl -X POST http://localhost:8080/predict \
     -H "Content-Type: application/json" \
     -d @test_payloads/test_payload_video.json

# Test 2: Multiple Images
curl -X POST http://localhost:8080/predict \
     -H "Content-Type: application/json" \
     -d @test_payloads/test_payload_images.json

# Test 3: Using a Manifest
curl -X POST http://localhost:8080/predict \
     -H "Content-Type: application/json" \
     -d @test_payloads/test_payload_manifest.json
```

If successful, your terminal will log the processing steps, and new KWCOCO files will appear in your GCS bucket!

## ☁️ Step 3: Deploy to Cloud

Once you are happy with local testing, push your container to the Google Artifact Registry:

```bash
# Tag your image for the registry
docker tag noaa-my-custom-model:latest us-central1-docker.pkg.dev/YOUR-PROJECT/YOUR-REPO/my-custom-model:v1.0

# Push it
docker push us-central1-docker.pkg.dev/YOUR-PROJECT/YOUR-REPO/my-custom-model:v1.0
```

## ⚙️ Step 4: Hook it into Airflow

To make your model available in the system, you must register it in the Airflow DAG (`scott_test_dag.py`).

Locate the `MODEL_JOB_MAP` dictionary in the DAG file and add a new entry for your model. It must use the `inference_runner.py` as its argument to trigger the batch adapter:

```python
    "my-custom-model": {
        "region": "us-central1",
        "image": "us-central1-docker.pkg.dev/YOUR-PROJECT/YOUR-REPO/my-custom-model:v1.0",
        "cpu": 4,
        "memory": "16Gi",
        "gpu": 1,                   # Change to 0 if CPU only
        "gpu_type": "nvidia-l4",    # Set to None if CPU only
        "machine_type": "g2-standard-4", 
        "timeout": 360000,
        "command": ["python"],
        "args": ["/workspace/inference_runner.py"] # <--- DO NOT CHANGE THIS
    }
```

Submit a Pull Request to the repository containing the Airflow DAG. Once merged, your dummy model is officially in production!

## 🚀 Step 5: Triggering in Airflow

When you run a job in Google Cloud Batch, the container boots up on an isolated, headless Virtual Machine. It doesn't have a user interface to accept manual inputs or local curl commands.

Because of this, **Airflow requires your JSON trigger payload to be uploaded to GCS first**. Airflow will pass the GCS URI of your JSON file to the headless VM, which will then download it and start the processing loop you just tested.

1. Upload your finalized JSON configuration to GCS (e.g., `gs://ggn-nmfs-osi-dev-1-data/my-folder/trigger_payload.json`).
2. Go to the Airflow UI and click **Trigger DAG w/ config**.
3. Set the `model_type` to your newly registered model name (e.g., `my-custom-model`).
4. Set the `input_file` parameter to the GCS URI of your uploaded JSON payload.
5. Hit **Trigger** and monitor your job's progress in the logs!

---

# 🔬 Phase 2: Bring Your Own Model (BYOM)

Congratulations! You have successfully executed a full end-to-end pipeline. Now it is time to replace the "dummy" code with your actual science.

## 🧠 Step 6: Write Your Logic

Open `model.py`. You will see the "Hello World" logic that assigns random bounding boxes. 

Replace this logic with your actual framework. 
*   Read the input images/videos from the provided `input_dir`.
*   Load custom weights or thresholds from the `config` dictionary.
*   Run your specific computer vision framework.
*   Save your output to the `output_file_path` using the [KWCOCO (Kitware COCO)](https://kwcoco.readthedocs.io/en/latest/) JSON specification, as shown in the example code.

## 📦 Step 7: Update Dependencies

If your model requires specific libraries (like `torch`, `tensorflow`, or `ultralytics`), you must add them to the `requirements.txt` file. We have already included OpenCV (`opencv-python-headless`) for you.

If you need heavy system-level packages (like custom NVIDIA drivers or specific `apt-get` binaries), you can add those to the `Dockerfile`.

## 🔄 Step 8: Re-build and Re-deploy

Now that your custom code is in place, simply repeat Phase 1!
1. Test it locally using `curl` (Step 2).
2. Build and push a new version to the Artifact Registry (Step 3). Note: **Increment your version tag** (e.g., `v1.1`) so you don't overwrite your previous work!
3. Update the Airflow DAG `MODEL_JOB_MAP` to point to your new `v1.1` image (Step 4).
4. Trigger the DAG!

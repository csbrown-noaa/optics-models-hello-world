from typing import Any, Dict, List
import jsonschema

from utils.utils import load_json_from_uri

def validate_payload(payload: Dict[str, Any], schema_path: str) -> None:
    """
    Validates a loaded JSON payload dictionary against a given JSON Schema file.
    Raises jsonschema.ValidationError if validation fails.
    """
    schema = load_json_from_uri(schema_path)
    jsonschema.validate(instance=payload, schema=schema)


def resolve_input_files(
    input_files: List[str] = None, input_manifest: str = None
) -> List[str]:
    """
    Resolves target input files from either a direct list or by fetching an input manifest JSON.
    """
    resolved_files = []

    if input_files:
        resolved_files.extend(input_files)

    if input_manifest:
        manifest_data = load_json_from_uri(input_manifest)
        if isinstance(manifest_data, list):
            resolved_files.extend(manifest_data)
        elif isinstance(manifest_data, dict) and "input_files" in manifest_data:
            resolved_files.extend(manifest_data["input_files"])
        else:
            raise ValueError(
                f"Invalid manifest format at {input_manifest}. Expected list or dict with 'input_files'."
            )

    return resolved_files


def to_job_spec(
    instance: Any, global_parameters: Dict[str, Any] = None
) -> Dict[str, Any]:
    
    """Converts a single instance payload item (string URI or dict) into a standardized job specification dictionary.

    Returns:
        {
            "input_files": List[str],
            "output_path": Optional[str],
            "json_output_location": Optional[str],
            "config": Dict[str, Any]
        }
    """
    global_parameters = global_parameters or {}
    global_config = global_parameters.get("config", {})
    global_output_path = global_parameters.get("output_path")

    # String Payload: Single GCS file URI string (e.g., "gs://bucket/video.mp4")
    if isinstance(instance, str):
        return {
            "input_files": [instance],
            "output_path": global_output_path,
            "json_output_location": None,
            "config": global_config,
        }

    # Dictionary Payload: Structured specification (e.g., {"input_files": ["gs://..."]})
    elif isinstance(instance, dict):
        raw_files = instance.get("input_files", [])
        manifest_uri = instance.get("input_manifest")
        
        # Merge local instance config with global parameters
        instance_config = instance.get("config", {})
        merged_config = {**global_config, **instance_config}

        resolved_files = resolve_input_files(
            input_files=raw_files, input_manifest=manifest_uri
        )

        return {
            "input_files": resolved_files,
            "output_path": instance.get("output_path") or global_output_path,
            "json_output_location": instance.get("json_output_location"),
            "config": merged_config,
        }

    else:
        raise TypeError(f"Unsupported instance payload type: {type(instance)}")

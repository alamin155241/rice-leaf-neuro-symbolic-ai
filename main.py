"""FastAPI entrypoint for the versioned rice-leaf diagnosis pipeline."""

from __future__ import annotations

import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from PIL import UnidentifiedImageError

from neuro_symbolic.artifact_loader import (
    RuntimeModeEscalationError,
    artifact_info,
    get_runtime_mode,
    sha256_file,
    validate_runtime_artifacts,
)
from neuro_symbolic.class_mapping import CNN_CLASS_ORDER, validate_class_mapping
from neuro_symbolic.observation import observation_schema_response
from neuro_symbolic.observation import GuidedObservationPolicyError
from neuro_symbolic.observation_vocabulary import (
    ObservationVocabularyValidationError,
)
from neuro_symbolic.schemas import GuidedObservations
from predictor import predict_with_gradcam

logger = logging.getLogger(__name__)
API_VERSION = "2.0.0"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    validate_startup()
    yield


app = FastAPI(
    title="Rice Leaf Disease Detection API",
    version=API_VERSION,
    lifespan=lifespan,
)

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
MAX_UPLOAD_SIZE_BYTES = int(
    os.getenv("MAX_UPLOAD_SIZE_BYTES", str(10 * 1024 * 1024))
)
MODEL_FILENAME = "rice_model_fixed.keras"
MODEL_PATH = Path(__file__).resolve().parent / "models" / MODEL_FILENAME

# Legacy general display content only. It is not evidence-linked and is exposed
# with explicit provenance in the v2 compatibility metadata.
DISEASE_DETAILS = {
    "brown_spot": {
        "cause": "Often associated with fungal infection and crop stress.",
        "prevention": "Use healthy seed and seek locally appropriate crop guidance.",
    },
    "healthy": {
        "cause": "No disease class was selected by the CNN.",
        "prevention": "Continue monitoring and good crop management.",
    },
    "leaf_blast": {
        "cause": "Often associated with Magnaporthe infection.",
        "prevention": "Use locally recommended monitoring and management practices.",
    },
    "leaf_scald": {
        "cause": "Often associated with pathogen pressure in warm, wet conditions.",
        "prevention": "Monitor the crop and seek locally appropriate guidance.",
    },
    "narrow_brown_spot": {
        "cause": "Often associated with fungal infection and plant stress.",
        "prevention": "Maintain crop monitoring and locally appropriate management.",
    },
}


class PredictionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    api_version: str = API_VERSION
    runtime_mode: str = "research"
    artifact_versions: dict[str, Any] = Field(default_factory=dict)
    cnn_result: dict[str, Any] = Field(default_factory=dict)
    observation_result: dict[str, Any] = Field(default_factory=dict)
    visual_evidence: dict[str, Any] = Field(default_factory=dict)
    safety_result: dict[str, Any] = Field(default_factory=dict)
    symbolic_result: dict[str, Any] = Field(default_factory=dict)
    fusion_result: dict[str, Any] = Field(default_factory=dict)
    management_result: dict[str, Any] = Field(default_factory=dict)
    explanation: dict[str, Any] = Field(default_factory=dict)
    compatibility_content_provenance: str = "legacy_general_guidance"

    class_name: str = Field(alias="class")
    final_decision: str
    confidence: float
    cause: str
    prevention: str
    recommendation: str
    warning: str
    trust_level: str
    severity: str
    infected_area_percent: float
    attention_coverage_percent: float
    second_class: str
    second_confidence: float
    all_probabilities: dict[str, float]
    reasoning_notes: list[str]
    phenotype_facts: list[str]
    knowledge_sources: list[str]
    matched_rules: list[dict[str, Any]]
    conflicts_detected: list[str]
    selected_rule: dict[str, Any] | None
    conflict_resolution_note: str
    ambiguity_detected: bool
    contradiction_detected: bool
    gradcam_heatmap_base64: str
    gradcam_overlay_base64: str
    attention_threshold_map_base64: str = ""
    lesion_mask_base64: str


def _allowed_origins() -> list[str]:
    raw = os.getenv("ALLOWED_ORIGINS", "*")
    return [item.strip() for item in raw.split(",") if item.strip()]


origins = _allowed_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def validate_startup() -> None:
    if not MODEL_PATH.is_file():
        raise RuntimeError(f"Required model file is missing: {MODEL_FILENAME}")
    validate_class_mapping()
    validate_runtime_artifacts()
    get_runtime_mode()
    # TensorFlow is loaded once by predictor. Validate the five-output contract.
    from predictor import model

    output_shape = model.output_shape
    output_count = int(output_shape[-1])
    validate_class_mapping(output_count)
    logger.info(
        "Validated model %s (%s), class count=%d, artifacts=%d",
        MODEL_FILENAME,
        sha256_file(MODEL_PATH),
        output_count,
        len(artifact_info()),
    )


def _is_likely_image_upload(file: UploadFile) -> bool:
    content_type = (file.content_type or "").lower().strip()
    if content_type.startswith("image/"):
        return True
    if content_type == "application/octet-stream":
        return Path(file.filename or "").suffix.lower() in ALLOWED_IMAGE_EXTENSIONS
    return False


def _parse_observations(value: str | None) -> GuidedObservations | None:
    if value is None or not value.strip():
        return None
    try:
        document = json.loads(value)
        if not isinstance(document, dict):
            raise ValueError("observations_json must contain a JSON object.")
        return GuidedObservations.model_validate(document)
    except (json.JSONDecodeError, ValidationError, ValueError) as error:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid observations_json: {error}",
        ) from error


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Rice Leaf Disease Detection API is running."}


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "api_version": API_VERSION,
        "runtime_mode": get_runtime_mode(),
    }


@app.get("/v2/system-info")
def system_info() -> dict[str, Any]:
    return {
        "api_version": API_VERSION,
        "runtime_mode": get_runtime_mode(),
        "model_filename": MODEL_FILENAME,
        "model_sha256": sha256_file(MODEL_PATH),
        "class_order": CNN_CLASS_ORDER,
        "artifacts": artifact_info(),
        "reasoning_engine_version": "1.0.0",
        "fusion_engine_version": "1.0.0",
    }


@app.get("/v2/observation-schema")
def observation_schema() -> dict[str, Any]:
    return observation_schema_response()


@app.post("/predict", response_model=PredictionResponse)
async def predict(
    file: UploadFile = File(...),
    observations_json: str | None = Form(default=None),
    runtime_mode: str | None = Form(default=None),
    include_visualizations: bool = Form(default=True),
) -> PredictionResponse:
    # FastAPI resolves Form defaults during HTTP dispatch. Direct compatibility
    # callers (including legacy tests) receive the parameter descriptor itself.
    observations_json = (
        observations_json if isinstance(observations_json, str) else None
    )
    runtime_mode = runtime_mode if isinstance(runtime_mode, str) else None
    include_visualizations = (
        include_visualizations if isinstance(include_visualizations, bool) else True
    )
    if not _is_likely_image_upload(file):
        raise HTTPException(status_code=400, detail="Please upload a valid image file.")
    image_bytes = await file.read(MAX_UPLOAD_SIZE_BYTES + 1)
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(image_bytes) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413, detail="Uploaded image exceeds the 10 MB size limit."
        )
    guided = _parse_observations(observations_json)
    try:
        requested_mode = get_runtime_mode(runtime_mode)
    except RuntimeModeEscalationError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    try:
        # Preserve direct compatibility with simple predictor stubs and callers.
        if (
            guided is None
            and runtime_mode is None
            and include_visualizations is True
        ):
            output = predict_with_gradcam(image_bytes)
        else:
            output = predict_with_gradcam(
                image_bytes,
                guided_observations=guided,
                runtime_mode=requested_mode,
                include_visualizations=include_visualizations,
            )
    except GuidedObservationPolicyError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ObservationVocabularyValidationError as error:
        raise HTTPException(status_code=422, detail=error.api_detail()) from error
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(status_code=400, detail="Please upload a valid image file.")
    except Exception:
        logger.exception("Unexpected prediction failure")
        raise HTTPException(
            status_code=500,
            detail="Prediction failed due to an internal server error.",
        )

    predicted_class = output["top_label"]
    details = DISEASE_DETAILS.get(
        predicted_class,
        {
            "cause": "No general cause information is available.",
            "prevention": "Consult a local agricultural expert.",
        },
    )
    threshold_map = output.get(
        "attention_threshold_map_base64", output["lesion_mask_base64"]
    )
    return PredictionResponse(
        api_version=output.get("api_version", API_VERSION),
        runtime_mode=output.get("runtime_mode", requested_mode),
        artifact_versions=output.get("artifact_versions", {}),
        cnn_result=output.get("cnn_result", {}),
        observation_result=output.get("observation_result", {}),
        visual_evidence=output.get("visual_evidence", {}),
        safety_result=output.get("safety_result", {}),
        symbolic_result=output.get("symbolic_result", {}),
        fusion_result=output.get("fusion_result", {}),
        management_result=output.get("management_result", {}),
        explanation=output.get("explanation", {}),
        class_name=predicted_class,
        final_decision=output["final_decision"],
        confidence=round(output["top_conf"], 4),
        cause=details["cause"],
        prevention=details["prevention"],
        recommendation=output["recommendation"],
        warning=output["warning"],
        trust_level=output["trust_level"],
        severity=output["severity"],
        infected_area_percent=round(output["infected_percent"], 2),
        attention_coverage_percent=round(output["attention_coverage_percent"], 2),
        second_class=output["second_label"],
        second_confidence=round(output["second_conf"], 4),
        all_probabilities={
            key: round(value, 4) for key, value in output["all_predictions"].items()
        },
        reasoning_notes=output["reasoning_notes"],
        phenotype_facts=output["phenotype_facts"],
        knowledge_sources=output["knowledge_sources"],
        matched_rules=output["matched_rules"],
        conflicts_detected=output["conflicts_detected"],
        selected_rule=output["selected_rule"],
        conflict_resolution_note=output["conflict_resolution_note"],
        ambiguity_detected=output["ambiguity_detected"],
        contradiction_detected=output["contradiction_detected"],
        gradcam_heatmap_base64=output["gradcam_heatmap_base64"],
        gradcam_overlay_base64=output["gradcam_overlay_base64"],
        attention_threshold_map_base64=threshold_map,
        lesion_mask_base64=output["lesion_mask_base64"],
    )

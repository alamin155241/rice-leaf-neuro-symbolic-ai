"""
predictor.py
-------------
Loads the trained TensorFlow model, runs prediction, and builds Grad-CAM output.
"""

from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path
from typing import Any, Tuple

import numpy as np
from PIL import Image
import tensorflow as tf
from tensorflow.keras.applications.efficientnet import preprocess_input

from neuro_symbolic.orchestrator import orchestrate_diagnosis
from neuro_symbolic.schemas import GuidedObservations

# Class order must match the order used when training the model.
CLASS_NAMES = [
    "brown_spot",
    "healthy",
    "leaf_blast",
    "leaf_scald",
    "narrow_brown_spot",
]

# Resolve the model path relative to this file's location.
BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "models" / "rice_model_fixed.keras"

# Load model once at startup (faster than loading for every request).
model = tf.keras.models.load_model(str(MODEL_PATH), compile=False)


def _load_and_preprocess_image(
    image_bytes: bytes, img_size: Tuple[int, int] = (224, 224)
) -> Tuple[np.ndarray, np.ndarray]:
    """Return display image and EfficientNet-preprocessed input tensor."""
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    image = image.resize(img_size)

    display_image = np.array(image, dtype=np.uint8)
    model_input = np.array(image, dtype=np.float32)
    model_input = np.expand_dims(model_input, axis=0)
    model_input = preprocess_input(model_input)
    return display_image, model_input


def _find_last_conv_layer_name() -> str:
    for layer in reversed(model.layers):
        output_shape = getattr(layer, "output_shape", None)
        if output_shape is not None and len(output_shape) == 4:
            return layer.name

        output = getattr(layer, "output", None)
        shape = getattr(output, "shape", None)
        if shape is not None and len(shape) == 4:
            return layer.name

    raise ValueError("Could not find a convolutional layer for Grad-CAM.")


LAST_CONV_LAYER_NAME = _find_last_conv_layer_name()


def _generate_gradcam_heatmap(
    model_input: np.ndarray, class_index: int, img_size: Tuple[int, int] = (224, 224)
) -> np.ndarray:
    grad_model = tf.keras.models.Model(
        [model.inputs],
        [model.get_layer(LAST_CONV_LAYER_NAME).output, model.output],
    )

    with tf.GradientTape() as tape:
        conv_outputs, predictions = grad_model(model_input)
        class_channel = predictions[:, class_index]

    grads = tape.gradient(class_channel, conv_outputs)
    if grads is None:
        raise ValueError("Unable to compute gradients for Grad-CAM.")

    pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))
    conv_outputs = conv_outputs[0]
    heatmap = tf.reduce_sum(conv_outputs * pooled_grads, axis=-1)
    heatmap = tf.maximum(heatmap, 0)
    max_val = tf.reduce_max(heatmap)
    if float(max_val) > 0:
        heatmap /= max_val

    heatmap = heatmap.numpy().astype(np.float32)
    heatmap = tf.image.resize(heatmap[..., np.newaxis], img_size).numpy().squeeze()
    return np.clip(heatmap, 0.0, 1.0)


def _jet_colormap(heatmap: np.ndarray) -> np.ndarray:
    """Approximate JET colormap without extra dependencies."""
    x = np.clip(heatmap, 0.0, 1.0)
    red = np.clip(1.5 - np.abs(4.0 * x - 3.0), 0.0, 1.0)
    green = np.clip(1.5 - np.abs(4.0 * x - 2.0), 0.0, 1.0)
    blue = np.clip(1.5 - np.abs(4.0 * x - 1.0), 0.0, 1.0)
    return np.stack([red, green, blue], axis=-1)


def _to_png_base64(image_array: np.ndarray) -> str:
    if image_array.dtype != np.uint8:
        image_array = np.clip(image_array, 0, 255).astype(np.uint8)

    if image_array.ndim == 2:
        pil_image = Image.fromarray(image_array, mode="L")
    else:
        pil_image = Image.fromarray(image_array, mode="RGB")

    buffer = BytesIO()
    pil_image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def estimate_attention_coverage_percent(
    heatmap: np.ndarray, threshold: float = 0.45
) -> Tuple[float, np.ndarray]:
    """Estimate strongly activated image coverage from a Grad-CAM heatmap.

    This is a heuristic model-attention measurement. It is not validated lesion
    segmentation and must not be interpreted as an exact infected-area estimate.
    """
    lesion_mask = heatmap >= threshold
    attention_coverage_percent = float(lesion_mask.mean() * 100.0)
    return attention_coverage_percent, lesion_mask


def estimate_infected_percent(
    heatmap: np.ndarray, threshold: float = 0.45
) -> Tuple[float, np.ndarray]:
    """Backward-compatible alias for the attention-coverage heuristic."""
    return estimate_attention_coverage_percent(heatmap, threshold)


def get_severity(
    attention_coverage_percent: float, predicted_label: str | None = None
) -> str:
    # Healthy results never receive a disease severity. Contradictory attention
    # evidence is represented separately by contradiction_detected.
    if predicted_label == "healthy":
        return "none"
    if attention_coverage_percent < 5:
        return "mild"
    if attention_coverage_percent < 15:
        return "moderate"
    return "severe"


def neuro_symbolic_reasoning(
    top_label: str,
    top_conf: float,
    second_label: str,
    second_conf: float,
    infected_percent: float,
) -> dict[str, Any]:
    """Deprecated compatibility wrapper around the single orchestrator."""
    severity = get_severity(infected_percent, top_label)
    probabilities = {name: 0.0 for name in CLASS_NAMES}
    probabilities[top_label] = top_conf
    probabilities[second_label] = second_conf
    remainder = max(0.0, 1.0 - sum(probabilities.values()))
    other = [name for name in CLASS_NAMES if name not in {top_label, second_label}]
    for name in other:
        probabilities[name] = remainder / len(other)
    return orchestrate_diagnosis(
        cnn_probabilities=probabilities,
        top_label=top_label,
        top_confidence=top_conf,
        second_label=second_label,
        second_confidence=second_conf,
        attention_coverage_percent=infected_percent,
        severity_heuristic=severity,
    )


def predict_with_gradcam(
    image_bytes: bytes,
    *,
    guided_observations: GuidedObservations | None = None,
    runtime_mode: str | None = None,
    include_visualizations: bool = True,
) -> dict[str, Any]:
    display_image, model_input = _load_and_preprocess_image(image_bytes)
    raw_predictions = model.predict(model_input, verbose=0)[0].astype(np.float32)

    sorted_indices = np.argsort(raw_predictions)[::-1]
    top_index = int(sorted_indices[0])
    second_index = int(sorted_indices[1]) if len(sorted_indices) > 1 else top_index

    top_label = CLASS_NAMES[top_index]
    top_conf = float(raw_predictions[top_index])
    second_label = CLASS_NAMES[second_index]
    second_conf = float(raw_predictions[second_index])

    heatmap = _generate_gradcam_heatmap(model_input, class_index=top_index)
    attention_coverage_percent, lesion_mask = (
        estimate_attention_coverage_percent(heatmap, threshold=0.45)
    )
    severity = get_severity(attention_coverage_percent, top_label)

    heatmap_rgb = (_jet_colormap(heatmap) * 255.0).astype(np.uint8)
    overlay = (
        display_image.astype(np.float32) * 0.55 + heatmap_rgb.astype(np.float32) * 0.45
    )
    overlay = np.clip(overlay, 0, 255).astype(np.uint8)
    lesion_mask_image = (lesion_mask.astype(np.uint8) * 255).astype(np.uint8)

    all_predictions: dict[str, float] = {}
    for index in sorted_indices:
        label = CLASS_NAMES[int(index)]
        all_predictions[label] = float(raw_predictions[int(index)])

    v2 = orchestrate_diagnosis(
        cnn_probabilities=all_predictions,
        top_label=top_label,
        top_confidence=top_conf,
        second_label=second_label,
        second_confidence=second_conf,
        attention_coverage_percent=attention_coverage_percent,
        severity_heuristic=severity,
        guided_observations=guided_observations,
        runtime_mode=runtime_mode,
    )
    encoded_heatmap = _to_png_base64(heatmap_rgb) if include_visualizations else ""
    encoded_overlay = _to_png_base64(overlay) if include_visualizations else ""
    encoded_threshold = (
        _to_png_base64(lesion_mask_image) if include_visualizations else ""
    )
    v2["visual_evidence"].update(
        {
            "gradcam_heatmap_base64": encoded_heatmap,
            "gradcam_overlay_base64": encoded_overlay,
            "attention_threshold_map_base64": encoded_threshold,
        }
    )
    fusion_result = v2["fusion_result"]
    safety_result = v2["safety_result"]
    symbolic_result = v2["symbolic_result"]
    management_result = v2["management_result"]
    final_decision = (
        fusion_result["final_prediction"]
        if not fusion_result["requires_manual_review"]
        else "uncertain"
    )
    trust_level = (
        "low"
        if fusion_result["requires_manual_review"]
        else "high"
        if fusion_result["final_confidence"] >= 0.90
        else "medium"
    )
    reasoning_notes = [
        v2["explanation"]["why_cnn_contributed"],
        v2["explanation"]["why_symbolic_contributed"],
        v2["explanation"]["why_final_prediction_was_selected"],
        v2["visual_evidence"]["disclaimer"],
    ]
    return {
        **v2,
        "top_label": top_label,
        "top_conf": top_conf,
        "second_label": second_label,
        "second_conf": second_conf,
        "all_predictions": all_predictions,
        # Legacy output retained for API compatibility. Both values currently
        # represent thresholded Grad-CAM attention, not lesion segmentation.
        "infected_percent": attention_coverage_percent,
        "attention_coverage_percent": attention_coverage_percent,
        "final_decision": final_decision,
        "trust_level": trust_level,
        "severity": severity,
        "recommendation": management_result["recommendation"],
        "warning": management_result["warning"],
        "reasoning_notes": reasoning_notes,
        # Do not label class-derived knowledge as observed phenotype.
        "phenotype_facts": [],
        "knowledge_sources": [
            str(source) for source in management_result.get("sources", [])
        ],
        "matched_rules": symbolic_result["matched_rules"],
        "conflicts_detected": (
            [fusion_result["resolution"]]
            if fusion_result["conflict_status"] == "detected"
            else []
        ),
        "selected_rule": management_result["selected_rule"],
        "conflict_resolution_note": fusion_result["resolution"],
        "ambiguity_detected": safety_result["ambiguity_detected"],
        "contradiction_detected": safety_result["contradiction_detected"],
        "gradcam_heatmap_base64": encoded_heatmap,
        "gradcam_overlay_base64": encoded_overlay,
        "attention_threshold_map_base64": encoded_threshold,
        # Deprecated alias: thresholded Grad-CAM attention, not lesion mask.
        "lesion_mask_base64": encoded_threshold,
    }


def predict_image(image_bytes: bytes) -> Tuple[str, float]:
    """Backwards-compatible lightweight prediction helper."""
    result = predict_with_gradcam(image_bytes)
    return result["top_label"], result["top_conf"]

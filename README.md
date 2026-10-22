# Rice Leaf Neuro-Symbolic AI

An undergraduate engineering project combining a FastAPI/TensorFlow rice-leaf classifier with evidence-aware symbolic reasoning and a Flutter Android client.

## Included source

- FastAPI backend, image preprocessing and Grad-CAM attention visualization.
- Versioned rule artifacts, observation validation, conflict handling and adaptive fusion.
- Flutter image upload and prediction interface, with optional structured observations.
- Backend and client tests, API documentation and research limitations.

The source snapshot includes Flutter v2 integration. Physical-device validation and comparative evaluation remain separate work; no new accuracy claim is made here. Grad-CAM attention is not validated lesion segmentation.

## Backend setup

Use Python 3.13 (the source environment used 3.13.2 and TensorFlow 2.21.0). Create and activate a virtual environment, then:

```sh
python -m pip install -r requirements-lock.txt
python -m pip install pytest httpx
```

**Model required:** trained weights and training images are not published in this source repository. Supply the compatible five-class model at `models/rice_model_fixed.keras`. The original file SHA-256 is `3f91da161d761f0da3bc4c157115f44f1a8cd25b3df624bd2b79ad77a6fc7a94`. Class order and preprocessing must match `predictor.py`; an arbitrary model is not a replacement. API startup requires this file.

```sh
python -m uvicorn main:app --host 127.0.0.1 --port 8000
python -m pytest -q
```

For a phone on your local network, bind the backend to `0.0.0.0` and configure the client with your computer's LAN address. Use HTTPS for a deployed service.

## Flutter client

```sh
cd frontend_flutter
flutter pub get
flutter run --dart-define=BACKEND_BASE_URL=http://10.0.2.2:8000
```

See [client instructions](frontend_flutter/README.md), [API contract](docs/API_V2.md), [scientific limitations](docs/SCIENTIFIC_LIMITATIONS.md), and [backend research notes](docs/BACKEND_NOTES.md). Some historical audit documents describe earlier integration stages; the current client has its own status documentation.

## Publication scope

This repository contains a curated source snapshot. Local environments, model binaries, training images, personal files, notebooks with execution outputs, and manuscript drafts are excluded. Artifact evidence and source attribution are retained. Full inference needs the model described above; hardware or physical-device validation is not implied by publishing source.

## Publication checks (22 October 2026)

Backend: 122 tests passed, 2 skipped in the available local environment. One API test now uses a temporary model checksum fixture, so it does not require private weights. Flutter: 24 tests passed and 3 existing widget tests failed (duplicate text matches and a prediction/reset view expectation). Analyzer reported one deprecated DropdownButtonFormField value parameter. These client issues remain open; this is a research source release, not a validated production app.

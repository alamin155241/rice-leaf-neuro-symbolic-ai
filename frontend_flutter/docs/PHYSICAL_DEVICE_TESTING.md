# Physical Android Device Testing

## Start the backend

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Confirm `http://localhost:8000/health` works on the computer. Determine the
computer's LAN IP, then run Flutter from `frontend_flutter/`:

```powershell
flutter run --dart-define=BACKEND_BASE_URL=http://<computer-lan-ip>:8000
```

The phone and computer must be connected to the same Wi-Fi/network. Windows
Firewall may need an inbound rule allowing TCP port 8000 for the active private
network. `localhost` on the phone means the phone itself, not the computer.

For the standard Android emulator, use:

```powershell
flutter run --dart-define=BACKEND_BASE_URL=http://10.0.2.2:8000
```

## Manual checklist

1. Open the app and confirm the advanced section is collapsed.
2. Select a rice-leaf image and verify its preview.
3. Submit without observations and confirm image-only prediction.
4. Open advanced confirmation and confirm dropdown options load from the server.
5. Select one categorical option and verify a guided prediction.
6. Confirm an uncertain result shows **Uncertain**, manual review, and a separate
   model candidate.
7. Confirm symbolic abstention is informational rather than an error.
8. Compare provided observations with separately listed rule-matched features.
9. Open evidence, visual, management, and technical sections.
10. Confirm the Grad-CAM disclaimer and attention-threshold wording.
11. Test Clear observations, Reset result, Retry prediction, and Clear image.
12. Stop the backend and confirm the unavailable-backend message is readable.

HTTP is permitted only for local development by the current Android manifest.
Production deployment requires HTTPS; do not ship a cleartext production API.

Automated tests cannot prove physical-device connectivity. Do not mark the full
mobile application complete until a real device successfully uploads an image
and receives a backend response.

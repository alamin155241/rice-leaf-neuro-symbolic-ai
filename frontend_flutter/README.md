# Rice Leaf Flutter Client

This Android Flutter application integrates with the FastAPI v2 rice-leaf
neuro-symbolic backend while retaining legacy-response compatibility. Image-only
prediction is the primary flow; structured symptom confirmation is optional and
loaded dynamically from the backend observation schema.

## Run

Android emulator:

```powershell
flutter run --dart-define=BACKEND_BASE_URL=http://10.0.2.2:8000
```

Physical Android device on the same Wi-Fi as the backend computer:

```powershell
flutter run --dart-define=BACKEND_BASE_URL=http://<computer-lan-ip>:8000
```

Start the backend from the repository root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
```

`BACKEND_BASE_URL` must include the `http://` or `https://` scheme. Endpoint
paths are constructed with `Uri`; the application does not append unsafe raw URL
strings.

## Validation

Run sequentially from `frontend_flutter/`:

```powershell
flutter pub get
dart format lib test
flutter analyze
flutter test
flutter build apk --debug
```

See:

- `docs/API_V2_INTEGRATION.md`
- `docs/PHYSICAL_DEVICE_TESTING.md`
- `docs/DEFERRED_OR_REMAINING_WORK.md`

Local HTTP access and Android cleartext traffic are development conveniences.
Production deployment requires HTTPS and an appropriate Android network policy.

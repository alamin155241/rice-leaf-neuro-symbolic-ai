import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../models/observation_schema.dart';
import '../models/prediction_result.dart';
import '../models/system_info.dart';
import '../services/api_service.dart';
import '../widgets/observation_form.dart';
import '../widgets/result_view.dart';

class HomeScreen extends StatefulWidget {
  HomeScreen({
    RiceLeafApi? api,
    this.initialImagePath,
    super.key,
  }) : api = api ?? ApiService();

  final RiceLeafApi api;
  final String? initialImagePath;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final ImagePicker _picker = ImagePicker();
  final ObservationFormController _observationController =
      ObservationFormController();

  String? _selectedImagePath;
  bool _isPredicting = false;
  double? _uploadProgress;
  String? _statusMessage;
  PredictionResult? _predictionResult;
  ObservationSchema? _observationSchema;
  SystemInfo? _systemInfo;
  bool _schemaLoading = true;
  String? _schemaError;

  @override
  void initState() {
    super.initState();
    _selectedImagePath = widget.initialImagePath;
    _loadBackendMetadata();
  }

  Future<void> _loadBackendMetadata() async {
    if (mounted) {
      setState(() {
        _schemaLoading = true;
        _schemaError = null;
      });
    }
    try {
      final schema = await widget.api.getObservationSchema();
      if (!mounted) {
        return;
      }
      setState(() {
        _observationSchema = schema;
        _schemaLoading = false;
      });
      try {
        final info = await widget.api.getSystemInfo();
        if (mounted) {
          setState(() => _systemInfo = info);
        }
      } catch (_) {
        // System information is optional presentation metadata.
      }
    } on ApiException catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _schemaLoading = false;
        _schemaError = error.userMessage;
      });
    } catch (_) {
      if (!mounted) {
        return;
      }
      setState(() {
        _schemaLoading = false;
        _schemaError = 'Advanced symptom options are currently unavailable.';
      });
    }
  }

  @override
  void dispose() {
    _observationController.dispose();
    super.dispose();
  }

  Future<void> _pickImage(ImageSource source) async {
    try {
      final picked = await _picker.pickImage(
        source: source,
        imageQuality: 90,
      );
      if (picked == null || !mounted) {
        return;
      }
      setState(() {
        _selectedImagePath = picked.path;
        _predictionResult = null;
        _statusMessage = null;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not open image source: $error')),
      );
    }
  }

  void _clearImage() {
    if (_isPredicting) {
      return;
    }
    setState(() {
      _selectedImagePath = null;
      _predictionResult = null;
      _statusMessage = null;
      _uploadProgress = null;
    });
  }

  void _resetResult() {
    if (_isPredicting) {
      return;
    }
    setState(() {
      _predictionResult = null;
      _statusMessage = null;
      _uploadProgress = null;
    });
  }

  Future<void> _predict() async {
    final imagePath = _selectedImagePath;
    if (imagePath == null || _isPredicting) {
      return;
    }
    Map<String, dynamic>? observations;
    try {
      final schema = _observationSchema;
      if (schema != null) {
        final values = _observationController.toJson(schema);
        observations = values.isEmpty ? null : values;
      }
    } on ObservationInputException catch (error) {
      setState(() => _statusMessage = error.toString());
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error.toString())),
      );
      return;
    }

    setState(() {
      _isPredicting = true;
      _uploadProgress = 0;
      _statusMessage = null;
      _predictionResult = null;
    });
    try {
      final result = await widget.api.predictDisease(
        imagePath,
        observations: observations,
        onProgress: (progress) {
          if (mounted) {
            setState(() => _uploadProgress = progress);
          }
        },
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _predictionResult = result;
        _statusMessage = result.isUncertain
            ? 'Prediction completed with uncertainty. Manual review may be required.'
            : 'Prediction completed: ${result.finalDisplayName}.';
      });
    } on ApiException catch (error) {
      if (!mounted) {
        return;
      }
      setState(() => _statusMessage = error.userMessage);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error.userMessage)),
      );
    } catch (_) {
      if (!mounted) {
        return;
      }
      const message = 'Prediction failed unexpectedly. Please retry.';
      setState(() => _statusMessage = message);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text(message)),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isPredicting = false;
          _uploadProgress = null;
        });
      }
    }
  }

  Widget _preview() {
    return Container(
      height: 280,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        border: Border.all(color: Colors.green.shade300),
        borderRadius: BorderRadius.circular(12),
      ),
      child: _selectedImagePath == null
          ? const Text('Preview area')
          : ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: Image.file(
                File(_selectedImagePath!),
                fit: BoxFit.cover,
                width: double.infinity,
                height: double.infinity,
                errorBuilder: (_, __, ___) => const Padding(
                  padding: EdgeInsets.all(16),
                  child: Text('Image preview is unavailable.'),
                ),
              ),
            ),
    );
  }

  Widget _advancedObservations() {
    return Card(
      margin: const EdgeInsets.only(top: 12),
      child: ExpansionTile(
        key: const Key('advanced-observations-tile'),
        title: const Text('Advanced symptom confirmation'),
        subtitle: const Text('Optional — image-only prediction remains supported'),
        childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
        children: [
          if (_schemaLoading) ...[
            const LinearProgressIndicator(),
            const SizedBox(height: 8),
            const Text('Loading observation options from the backend…'),
          ] else if (_schemaError != null) ...[
            Text(_schemaError!, style: TextStyle(color: Colors.orange.shade900)),
            TextButton.icon(
              key: const Key('retry-schema-button'),
              onPressed: _loadBackendMetadata,
              icon: const Icon(Icons.refresh),
              label: const Text('Retry schema loading'),
            ),
          ] else if (_observationSchema != null)
            ObservationForm(
              schema: _observationSchema!,
              controller: _observationController,
            ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final result = _predictionResult;
    return Scaffold(
      appBar: AppBar(title: const Text('Rice Leaf Disease Detection')),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                ElevatedButton.icon(
                  key: const Key('choose-image-button'),
                  onPressed: _isPredicting
                      ? null
                      : () => _pickImage(ImageSource.gallery),
                  icon: const Icon(Icons.photo_library_outlined),
                  label: const Text('Choose Image'),
                ),
                ElevatedButton.icon(
                  key: const Key('take-photo-button'),
                  onPressed: _isPredicting
                      ? null
                      : () => _pickImage(ImageSource.camera),
                  icon: const Icon(Icons.camera_alt_outlined),
                  label: const Text('Camera'),
                ),
                if (_selectedImagePath != null)
                  OutlinedButton.icon(
                    key: const Key('clear-image-button'),
                    onPressed: _isPredicting ? null : _clearImage,
                    icon: const Icon(Icons.image_not_supported_outlined),
                    label: const Text('Clear image'),
                  ),
              ],
            ),
            const SizedBox(height: 16),
            _preview(),
            const SizedBox(height: 16),
            ElevatedButton(
              key: const Key('predict-button'),
              onPressed: _selectedImagePath == null || _isPredicting
                  ? null
                  : _predict,
              child: _isPredicting
                  ? const Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        ),
                        SizedBox(width: 12),
                        Text('Predicting…'),
                      ],
                    )
                  : const Text('Predict'),
            ),
            if (_isPredicting) ...[
              const SizedBox(height: 8),
              LinearProgressIndicator(value: _uploadProgress),
            ],
            _advancedObservations(),
            if (_statusMessage != null) ...[
              const SizedBox(height: 12),
              Text(
                _statusMessage!,
                key: const Key('prediction-status'),
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: result == null ? Colors.red.shade700 : Colors.green.shade700,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
            if (result != null)
              ResultView(
                result: result,
                systemInfo: _systemInfo,
                onReset: _resetResult,
                onRetry: _predict,
              ),
          ],
        ),
      ),
    );
  }
}

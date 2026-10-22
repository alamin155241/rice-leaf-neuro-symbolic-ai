class AppConfig {
  const AppConfig._();

  /// Override at build/run time with:
  /// --dart-define=BACKEND_BASE_URL=http://<backend-host>:8000
  static const String backendBaseUrl = String.fromEnvironment(
    'BACKEND_BASE_URL',
    defaultValue: 'http://192.168.1.100:8000',
  );

  static Uri get baseUri {
    final parsed = Uri.parse(backendBaseUrl);
    if (!parsed.hasScheme || parsed.host.isEmpty) {
      throw const FormatException(
        'BACKEND_BASE_URL must include an http or https scheme and host.',
      );
    }
    return parsed;
  }

  static Uri endpoint(String relativePath) {
    final base = baseUri;
    final baseSegments = base.pathSegments.where((part) => part.isNotEmpty);
    final newSegments = relativePath
        .split('/')
        .where((part) => part.isNotEmpty);
    return base.replace(pathSegments: [...baseSegments, ...newSegments]);
  }

  static Uri get rootEndpoint => endpoint('');
  static Uri get healthEndpoint => endpoint('health');
  static Uri get systemInfoEndpoint => endpoint('v2/system-info');
  static Uri get observationSchemaEndpoint =>
      endpoint('v2/observation-schema');
  static Uri get predictEndpoint => endpoint('predict');
}

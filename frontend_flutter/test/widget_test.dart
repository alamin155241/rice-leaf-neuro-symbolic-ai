import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend_flutter/main.dart';
import 'package:frontend_flutter/models/observation_schema.dart';
import 'package:frontend_flutter/models/prediction_result.dart';
import 'package:frontend_flutter/screens/home_screen.dart';
import 'package:frontend_flutter/services/api_service.dart';
import 'package:frontend_flutter/widgets/observation_form.dart';
import 'package:frontend_flutter/widgets/result_view.dart';

import 'test_support.dart';

Widget resultHarness(PredictionResult result) {
  return MaterialApp(
    home: Scaffold(
      body: SingleChildScrollView(
        child: ResultView(
          result: result,
          onReset: () {},
          onRetry: () {},
        ),
      ),
    ),
  );
}

void main() {
  testWidgets('home screen loads with advanced section collapsed', (tester) async {
    await tester.pumpWidget(RiceLeafApp(api: FakeApi()));
    await tester.pumpAndSettle();

    expect(find.text('Rice Leaf Disease Detection'), findsOneWidget);
    expect(find.text('Choose Image'), findsOneWidget);
    expect(find.text('Preview area'), findsOneWidget);
    expect(find.text('Predict'), findsOneWidget);
    expect(find.text('Advanced symptom confirmation'), findsOneWidget);
    expect(find.byKey(const Key('observation-dropdown-lesion_shape')), findsNothing);
  });

  testWidgets('dynamic dropdown uses backend display labels', (tester) async {
    final schema = ObservationSchema.fromJson(
      loadFixture('observation_schema_v1.json'),
    );
    final controller = ObservationFormController();
    addTearDown(controller.dispose);
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: ObservationForm(schema: schema, controller: controller),
          ),
        ),
      ),
    );

    final dropdown = find.byKey(const Key('observation-dropdown-lesion_shape'));
    expect(dropdown, findsOneWidget);
    await tester.tap(dropdown);
    await tester.pumpAndSettle();
    expect(find.text('Spindle-shaped'), findsOneWidget);
    expect(find.text('Oval'), findsOneWidget);
    expect(find.text('ellipse-like'), findsNothing);
  });

  testWidgets('uncertain result separates candidate from final diagnosis', (tester) async {
    final result = PredictionResult.fromJson(
      loadFixture('api_v2_safety_uncertain.json'),
    );
    await tester.pumpWidget(resultHarness(result));

    expect(find.byKey(const Key('final-diagnosis-value')), findsOneWidget);
    expect(find.text('Uncertain'), findsWidgets);
    expect(find.byKey(const Key('manual-review-chip')), findsOneWidget);
    expect(find.byKey(const Key('model-candidate-row')), findsOneWidget);
    expect(find.text('Model candidate'), findsOneWidget);
    expect(find.text('Leaf Blast'), findsOneWidget);
  });

  testWidgets('symbolic abstention and effective weights are clear', (tester) async {
    final result = PredictionResult.fromJson(
      loadFixture('api_v2_symbolic_abstention.json'),
    );
    await tester.pumpWidget(resultHarness(result));

    expect(find.byKey(const Key('symbolic-abstention-message')), findsOneWidget);
    expect(find.byKey(const Key('effective-cnn-weight')), findsOneWidget);
    expect(find.byKey(const Key('effective-symbolic-weight')), findsOneWidget);
    expect(find.text('1.0000'), findsOneWidget);
    expect(find.text('0.0000'), findsOneWidget);
  });

  testWidgets('provided and matched observations remain separate', (tester) async {
    final result = PredictionResult.fromJson(
      loadFixture('api_v2_guided_observation.json'),
    );
    await tester.pumpWidget(resultHarness(result));

    await tester.tap(find.text('4. Observations'));
    await tester.pumpAndSettle();
    expect(find.text('Provided observations'), findsOneWidget);
    expect(find.text('greyish'), findsOneWidget);
    expect(find.text('gray'), findsOneWidget);
    expect(find.text('Rule-matched observations'), findsOneWidget);
    expect(find.text('lesion center color gray'), findsOneWidget);
  });

  testWidgets('management advisory and Grad-CAM disclaimer are visible', (tester) async {
    final result = PredictionResult.fromJson(
      loadFixture('api_v2_full_response.json'),
    );
    await tester.pumpWidget(resultHarness(result));

    await tester.ensureVisible(find.text('6. Visual evidence'));
    await tester.tap(find.text('6. Visual evidence'));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('gradcam-disclaimer')), findsOneWidget);

    await tester.ensureVisible(find.text('8. Management guidance'));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('management-advisory-badge')), findsOneWidget);
    expect(
      find.text('Advisory research information — not validated treatment instruction.'),
      findsOneWidget,
    );
  });

  testWidgets('home supports prediction reset and retry', (tester) async {
    final api = FakeApi();
    await tester.pumpWidget(
      MaterialApp(home: HomeScreen(api: api, initialImagePath: 'test-image.png')),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('predict-button')));
    await tester.pumpAndSettle();
    expect(api.predictionCalls, 1);
    expect(find.byKey(const Key('final-diagnosis-card')), findsOneWidget);

    await tester.ensureVisible(find.byKey(const Key('retry-prediction-button')));
    await tester.tap(find.byKey(const Key('retry-prediction-button')));
    await tester.pumpAndSettle();
    expect(api.predictionCalls, 2);

    await tester.ensureVisible(find.byKey(const Key('reset-result-button')));
    await tester.tap(find.byKey(const Key('reset-result-button')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('final-diagnosis-card')), findsNothing);
  });

  testWidgets('backend unavailable error is shown without crashing', (tester) async {
    final api = FakeApi(
      predictionError: const ApiException(
        message: 'Backend unavailable. Confirm the server address and network.',
      ),
    );
    await tester.pumpWidget(
      MaterialApp(home: HomeScreen(api: api, initialImagePath: 'test-image.png')),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('predict-button')));
    await tester.pumpAndSettle();
    expect(
      find.text('Backend unavailable. Confirm the server address and network.'),
      findsWidgets,
    );
  });

  testWidgets('safe observation API error includes allowed values', (tester) async {
    final api = FakeApi(
      predictionError: const ApiException(
        statusCode: 422,
        field: 'lesion_shape',
        allowedValues: ['oval', 'spindle_shaped'],
        message: 'Unsupported observation value.',
      ),
    );
    await tester.pumpWidget(
      MaterialApp(home: HomeScreen(api: api, initialImagePath: 'test-image.png')),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('predict-button')));
    await tester.pumpAndSettle();
    expect(find.textContaining('Allowed values: oval, spindle_shaped'), findsWidgets);
  });
}

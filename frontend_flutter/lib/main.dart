import 'package:flutter/material.dart';

import 'screens/home_screen.dart';
import 'services/api_service.dart';

void main() {
  runApp(const RiceLeafApp());
}

class RiceLeafApp extends StatelessWidget {
  const RiceLeafApp({this.api, super.key});

  final RiceLeafApi? api;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Rice Leaf Disease Detection',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.green),
        useMaterial3: true,
      ),
      home: HomeScreen(api: api),
    );
  }
}

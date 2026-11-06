import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';

void main() => runApp(const LinkProbeApp());

Map<String, String> resolveLink(String route) {
  final uri = Uri.tryParse(route);
  if (route == '/') return {'screen': 'home'};
  if (uri == null || uri.scheme != 'linkprobe') {
    return {'screen': 'error', 'reason': 'unknown_route'};
  }
  if (uri.host == 'product') {
    if (uri.pathSegments.length == 1 &&
        RegExp(r'^[1-9][0-9]*$').hasMatch(uri.pathSegments.first)) {
      return {'screen': 'product_detail', 'product_id': uri.pathSegments.first};
    }
    return {'screen': 'error', 'reason': 'invalid_product_id'};
  }
  return {'screen': 'error', 'reason': 'unknown_route'};
}

class LinkProbeApp extends StatelessWidget {
  const LinkProbeApp({super.key});

  Route<void> route(RouteSettings settings) => MaterialPageRoute(
    settings: settings,
    builder: (_) => ProbePage(route: settings.name ?? '/'),
  );

  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'Link Probe',
    theme: ThemeData(colorSchemeSeed: Colors.indigo, useMaterial3: true),
    onGenerateInitialRoutes: (name) => [route(RouteSettings(name: name))],
    onGenerateRoute: route,
  );
}

class ProbePage extends StatefulWidget {
  const ProbePage({super.key, required this.route});
  final String route;
  @override
  State<ProbePage> createState() => _ProbePageState();
}

class _ProbePageState extends State<ProbePage> {
  @override
  void initState() {
    super.initState();
    if (const bool.fromEnvironment('QA_PROBE')) {
      WidgetsBinding.instance.addPostFrameCallback((_) async {
        if (!mounted) return;
        final path = '${Directory.systemTemp.path}/link-probe-state.json';
        final temporary = File('$path.next');
        await temporary.writeAsString(
          jsonEncode({...resolveLink(widget.route), 'route': widget.route}),
        );
        await temporary.rename(path);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = resolveLink(widget.route);
    final screen = state['screen'];
    return Scaffold(
      appBar: AppBar(title: const Text('Link Probe · Demo')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              screen == 'home'
                  ? 'Home'
                  : screen == 'product_detail'
                  ? 'Product ${state['product_id']}'
                  : 'Invalid link',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 16),
            Text('Route: ${widget.route}'),
            if (state['reason'] != null) Text('Reason: ${state['reason']}'),
            const SizedBox(height: 24),
            const Text(
              'Try linkprobe://product/123 from the regression runner.',
            ),
            if (const bool.fromEnvironment('QA_PROBE'))
              const Text('QA observation enabled · test build only'),
          ],
        ),
      ),
    );
  }
}

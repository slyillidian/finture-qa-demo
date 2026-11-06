import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:link_probe/main.dart';

void main() {
  test('valid IDs and invalid routes resolve distinctly', () {
    expect(resolveLink('/product/123')['product_id'], '123');
    expect(resolveLink('/product/456')['product_id'], '456');
    for (final url in [
      '/product',
      '/product/abc',
      '/product/123/extra',
      '/product/0',
    ]) {
      expect(resolveLink(url)['reason'], 'invalid_product_id');
    }
    expect(resolveLink('/unknown')['reason'], 'unknown_route');
  });
  testWidgets('running app switches product and renders invalid link', (
    tester,
  ) async {
    await tester.pumpWidget(const LinkProbeApp());
    expect(find.text('Home'), findsOneWidget);
    final navigator = tester.state<NavigatorState>(find.byType(Navigator));
    navigator.pushNamed('/product/123');
    await tester.pumpAndSettle();
    expect(find.text('Product 123'), findsOneWidget);
    navigator.pushNamed('/product/456');
    await tester.pumpAndSettle();
    expect(find.text('Product 456'), findsOneWidget);
    expect(find.text('Product 123'), findsNothing);
    navigator.pushNamed('/product/no');
    await tester.pumpAndSettle();
    expect(find.text('Invalid link'), findsOneWidget);
  });
}

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import itertools

spec = importlib.util.spec_from_file_location('link_probe', Path(__file__).parents[1] / 'src/link_probe.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class CasesTest(unittest.TestCase):
    def test_wrong_product_and_stale_route_fail(self):
        case = {'url': 'linkprobe://app/product/456', 'expect': {'screen': 'product_detail', 'product_id': '456'}}
        actual = {'route': '/product/123', 'screen': 'product_detail', 'product_id': '123'}
        self.assertEqual(set(probe.mismatches(case, actual)), {'route', 'product_id'})
        self.assertEqual(probe.mismatches(case, {**case['expect'], 'route': '/product/456'}), {})

    def test_reject_bad_input_before_simulator_commands(self):
        valid = {'name': 'test', 'url': 'linkprobe://app/product/1', 'launch': 'cold', 'expect': {'screen': 'product_detail'}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'cases.json'
            for cases in [[], [valid, valid], [{**valid, 'launch': 'other'}],
                          [{**valid, 'expect': {}}], [{**valid, 'timeout_seconds': -1}],
                          [{**valid, 'timeout_seconds': True}]]:
                path.write_text(json.dumps(cases))
                with self.assertRaises(ValueError):
                    probe.load_cases(path)

    def test_alert_fallback_never_replaces_page_assertions(self):
        case = {'name': 'product', 'url': 'linkprobe://app/product/123',
                'launch': 'cold', 'expect': {'screen': 'product_detail', 'product_id': '123'}}
        for outcome in ('immediate', 'opened', 'wrong_product', 'not_present', 'helper_error'):
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as folder:
                directory = Path(folder)
                (directory / 'tmp').mkdir()
                state = directory / 'tmp/link-probe-state.json'
                observed = {'screen': 'product_detail', 'product_id': '123', 'route': '/product/123'}
                def call(*args, **kwargs):
                    if args[:2] == ('list', 'devices'):
                        return json.dumps({'devices': {'ios': [{'udid': 'device', 'state': 'Booted'}]}})
                    if args[0] == 'get_app_container':
                        return str(directory)
                    if args[0] == 'openurl' and outcome == 'immediate':
                        state.write_text(json.dumps(observed))
                    return ''
                def handle(index):
                    if outcome == 'helper_error':
                        raise RuntimeError('helper failed')
                    if outcome in ('opened', 'wrong_product'):
                        state.write_text(json.dumps({**observed, 'product_id': '456' if outcome == 'wrong_product' else '123'}))
                        return 'opened'
                    return 'not_present'
                helper = Mock()
                helper.handle.side_effect = handle
                simulator = probe.Simulator('device', 'bundle', directory, helper)
                simulator.call = Mock(side_effect=call)
                ticks = itertools.count(0, .5)
                with patch.object(probe.time, 'monotonic', side_effect=lambda: next(ticks)), patch.object(probe.time, 'sleep'):
                    result = simulator.run([case])[0]
                self.assertEqual(result['passed'], outcome in ('immediate', 'opened'))
                if outcome == 'immediate':
                    helper.handle.assert_not_called()
                else:
                    helper.handle.assert_called_once_with(1)
                if not result['passed']:
                    self.assertIn('screenshot', result)


if __name__ == '__main__':
    unittest.main()

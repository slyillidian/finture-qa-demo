import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('link_probe', Path(__file__).parents[1] / 'src/link_probe.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class CasesTest(unittest.TestCase):
    def test_wrong_product_and_stale_route_fail(self):
        case = {'url': 'linkprobe://product/456', 'expect': {'screen': 'product_detail', 'product_id': '456'}}
        actual = {'route': 'linkprobe://product/123', 'screen': 'product_detail', 'product_id': '123'}
        self.assertEqual(set(probe.mismatches(case, actual)), {'route', 'product_id'})
        self.assertEqual(probe.mismatches(case, {**case['expect'], 'route': case['url']}), {})

    def test_reject_bad_input_before_simulator_commands(self):
        valid = {'name': 'test', 'url': 'linkprobe://product/1', 'launch': 'cold', 'expect': {'screen': 'product_detail'}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'cases.json'
            for cases in [[], [valid, valid], [{**valid, 'launch': 'other'}],
                          [{**valid, 'expect': {}}], [{**valid, 'timeout_seconds': -1}],
                          [{**valid, 'timeout_seconds': True}]]:
                path.write_text(json.dumps(cases))
                with self.assertRaises(ValueError):
                    probe.load_cases(path)


if __name__ == '__main__':
    unittest.main()

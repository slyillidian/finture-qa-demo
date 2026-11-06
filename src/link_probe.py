#!/usr/bin/env python3
"""Local iOS Simulator link regression runner. No third-party dependencies."""
import argparse
from datetime import datetime
import json
import math
from pathlib import Path
import subprocess
import sys
import time
import uuid
from urllib.parse import urlparse


def load_cases(path):
    cases = json.loads(Path(path).read_text())
    if not isinstance(cases, list) or not cases:
        raise ValueError('cases must be a non-empty array')
    names = set()
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError('each case must be an object')
        name = case.get('name')
        if not isinstance(name, str) or not name or name in names:
            raise ValueError('case names must be non-empty and unique')
        names.add(name)
        url = case.get('url')
        if not isinstance(url, str) or not urlparse(url).scheme:
            raise ValueError(f'{name}: URL requires a scheme')
        if case.get('launch') not in ('cold', 'warm'):
            raise ValueError(f'{name}: launch must be cold or warm')
        expect = case.get('expect')
        if not isinstance(expect, dict) or not expect.get('screen'):
            raise ValueError(f'{name}: expect.screen required')
        if any(not isinstance(k, str) or not isinstance(v, str) for k, v in expect.items()):
            raise ValueError(f'{name}: expected fields must be strings')
        timeout = case.get('timeout_seconds', 10)
        if isinstance(timeout, bool) or not isinstance(timeout, (float, int)) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError(f'{name}: timeout must be positive and finite')
    return cases


def mismatches(case, actual):
    expected = {**case['expect'], 'route': case['url']}
    return {key: {'expected': value, 'actual': actual.get(key)}
            for key, value in expected.items() if actual.get(key) != value}


class Simulator:
    def __init__(self, device, bundle, directory):
        self.device, self.bundle, self.directory = device, bundle, directory
        self.log = []

    def call(self, *args, allow_failure=False):
        result = subprocess.run(['xcrun', 'simctl', *args], capture_output=True,
                                text=True, timeout=60)
        self.log.append({'args': list(args), 'code': result.returncode,
                         'stdout': result.stdout, 'stderr': result.stderr})
        if result.returncode and not allow_failure:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())
        return result.stdout.strip()

    def run(self, cases):
        devices = json.loads(self.call('list', 'devices', '--json'))['devices']
        matching = [d for group in devices.values() for d in group
                    if d['udid'] == self.device and d['state'] == 'Booted']
        if not matching:
            raise ValueError('--device must be the UDID of a booted simulator')
        container = Path(self.call('get_app_container', self.device, self.bundle, 'data'))
        state_file = container / 'tmp' / 'link-probe-state.json'
        results = []
        for index, case in enumerate(cases, 1):
            start = time.monotonic()
            result = {'name': case['name'], 'url': case['url'], 'launch': case['launch'],
                      'expected': case['expect'], 'passed': False}
            try:
                if case['launch'] == 'cold':
                    self.call('terminate', self.device, self.bundle, allow_failure=True)
                else:
                    self.call('launch', self.device, self.bundle)
                    # Wait for an already running app or a newly launched home page.
                    time.sleep(1)
                state_file.unlink(missing_ok=True)
                self.call('openurl', self.device, case['url'])
                deadline = time.monotonic() + case.get('timeout_seconds', 10)
                actual = None
                while time.monotonic() < deadline:
                    try:
                        observed = json.loads(state_file.read_text())
                        if isinstance(observed, dict):
                            actual = observed
                            if observed.get('route') == case['url']:
                                break
                    except (FileNotFoundError, json.JSONDecodeError):
                        pass
                    time.sleep(.1)
                if actual is None:
                    result['error'] = 'No page observation before timeout. Is QA_PROBE enabled?'
                else:
                    result['actual'] = actual
                    result['mismatches'] = mismatches(case, actual)
                    result['passed'] = not result['mismatches']
                if not result['passed']:
                    screenshot = self.directory / f'{index:02d}-failure.png'
                    self.call('io', self.device, 'screenshot', str(screenshot))
                    result['screenshot'] = screenshot.name
            except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
                result['error'] = str(exc)
            result['seconds'] = round(time.monotonic() - start, 3)
            results.append(result)
            print(f"{'PASS' if result['passed'] else 'FAIL'} {case['name']}")
        return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device', required=True, help='booted simulator UDID')
    parser.add_argument('--bundle', default='dev.sly.linkProbe')
    parser.add_argument('--cases', default='cases/smoke.json')
    parser.add_argument('--output', default='reports')
    args = parser.parse_args()
    simulator = None
    directory = None
    try:
        cases = load_cases(args.cases)
        directory = Path(args.output).resolve() / (datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6])
        directory.mkdir(parents=True)
        simulator = Simulator(args.device, args.bundle, directory)
        results = simulator.run(cases)
        (directory / 'results.json').write_text(json.dumps(results, indent=2, ensure_ascii=False))
        lines = ['# Link Probe report', '']
        for r in results:
            lines.extend([f"## {'PASS' if r['passed'] else 'FAIL'}: {r['name']}", '',
                          '```json', json.dumps(r, ensure_ascii=False, indent=2), '```', ''])
        (directory / 'report.md').write_text('\n'.join(lines))
        print(f'Report: {directory}')
        return 0 if all(r['passed'] for r in results) else 1
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f'Environment/configuration error: {exc}', file=sys.stderr)
        return 2
    finally:
        if simulator and directory:
            (directory / 'commands.json').write_text(json.dumps(simulator.log, indent=2))


if __name__ == '__main__':
    sys.exit(main())

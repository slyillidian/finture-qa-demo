#!/usr/bin/env python3
"""Local iOS Simulator link regression runner. No third-party dependencies."""
import argparse
from datetime import datetime
import json
import math
import plistlib
from pathlib import Path
import subprocess
import sys
import time
import uuid
from urllib.parse import urlparse


class AlertHelper:
    """Shared on-demand XCUITest runner for URL alerts and visible UI checks."""
    def __init__(self, device, app_name, directory):
        self.device, self.app_name, self.directory = device, app_name, directory
        self.products = Path(__file__).resolve().parents[1] / 'work/alert-helper/Build/Products'
        self.built = False

    def command(self, args, log_path, allow_failure=False):
        with log_path.open('w') as log:
            result = subprocess.run(['xcodebuild', *args], stdout=log,
                                    stderr=subprocess.STDOUT, timeout=120)
        if result.returncode and not allow_failure:
            raise RuntimeError(f'XCUITest helper failed; see {log_path}')
        return log_path.read_text()

    def run_test(self, index, kind, test, environment, allow_failure=False):
        root = Path(__file__).resolve().parents[1]
        destination = f'platform=iOS Simulator,id={self.device}'
        if not self.built:
            self.command(['build-for-testing', '-project', str(root / 'ios/AlertHelper/AlertHelper.xcodeproj'),
                          '-scheme', 'AlertHelper', '-destination', destination,
                          '-derivedDataPath', str(root / 'work/alert-helper'), 'CODE_SIGNING_ALLOWED=NO'],
                         self.directory / 'alert-build.log')
            self.built = True
        originals = [p for p in self.products.glob('*.xctestrun') if p.name != 'configured.xctestrun']
        if len(originals) != 1:
            raise RuntimeError('Expected one alert-helper xctestrun; remove work/alert-helper and retry')
        settings = plistlib.loads(originals[0].read_bytes())
        for key, target in settings.items():
            if key != '__xctestrun_metadata__':
                target.setdefault('EnvironmentVariables', {}).update(environment)
        # Keep beside the original: xctestrun resolves paths relative to __TESTROOT__.
        configured = self.products / 'configured.xctestrun'
        configured.write_bytes(plistlib.dumps(settings))
        log = self.command(['test-without-building', '-xctestrun', str(configured),
                            '-destination', destination, '-parallel-testing-enabled', 'NO',
                            '-only-testing', f'AlertHelper/AlertHelper/{test}',
                            '-resultBundlePath', str(self.directory / f'{index:02d}-{kind}.xcresult')],
                           self.directory / f'{index:02d}-{kind}.log', allow_failure=allow_failure)
        return log

    def handle(self, index):
        log = self.run_test(index, 'alert', 'testHandleOpenAlert',
                            {'LP_EXPECTED_APP_NAME': self.app_name})
        for status in ('opened', 'not_present'):
            if f'LINK_PROBE_ALERT:{status}' in log:
                return status
        raise RuntimeError('Alert helper returned no recognized outcome')

    def assert_ui(self, index, bundle, assertions, timeout):
        log = self.run_test(index, 'ui', 'testAssertUI', {
            'LP_BUNDLE_ID': bundle,
            'LP_UI_ASSERTIONS': json.dumps(assertions),
            'LP_UI_TIMEOUT': str(timeout),
        }, allow_failure=True)
        for line in log.splitlines():
            if line.startswith('LINK_PROBE_UI:'):
                try:
                    result = json.loads(line.removeprefix('LINK_PROBE_UI:'))
                except json.JSONDecodeError as exc:
                    raise RuntimeError('Invalid UI helper JSON result') from exc
                if not isinstance(result, dict) or type(result.get('passed')) is not bool:
                    raise RuntimeError('Invalid UI helper result')
                # A structured success must also have a successful XCTest session.
                if result['passed'] and '** TEST EXECUTE SUCCEEDED **' not in log:
                    raise RuntimeError('UI helper reported success but XCTest session failed')
                return result
        raise RuntimeError('UI helper returned no result; see UI log and xcresult')


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
        if 'ui' in case:
            assertions = case['ui']
            if not isinstance(assertions, list) or not assertions:
                raise ValueError(f'{name}: ui must be a non-empty array')
            ids = set()
            for assertion in assertions:
                if (not isinstance(assertion, dict)
                        or any(not isinstance(assertion.get(k), str) or not assertion[k].strip()
                               for k in ('id', 'label'))
                        or assertion['id'] in ids):
                    raise ValueError(f'{name}: ui requires unique non-empty id and label strings')
                ids.add(assertion['id'])
        timeout = case.get('timeout_seconds', 10)
        if isinstance(timeout, bool) or not isinstance(timeout, (float, int)) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError(f'{name}: timeout must be positive and finite')
    return cases


def mismatches(case, actual):
    expected = {**case['expect'], 'route': urlparse(case['url']).path or '/'}
    return {key: {'expected': value, 'actual': actual.get(key)}
            for key, value in expected.items() if actual.get(key) != value}


class Simulator:
    def __init__(self, device, bundle, directory, alert_helper=None, ui_helper=None):
        self.device, self.bundle, self.directory = device, bundle, directory
        self.log = []
        self.alert_helper = alert_helper
        self.ui_helper = ui_helper

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
                alert_check_at = time.monotonic() + 1.5
                checked_alert = False
                actual = None
                while time.monotonic() < deadline:
                    try:
                        observed = json.loads(state_file.read_text())
                        if isinstance(observed, dict):
                            actual = observed
                            if observed.get('route') == (urlparse(case['url']).path or '/'):
                                break
                    except (FileNotFoundError, json.JSONDecodeError):
                        pass
                    if self.alert_helper and not checked_alert and time.monotonic() >= alert_check_at:
                        checked_alert = True
                        helper_start = time.monotonic()
                        result['alert_handling'] = self.alert_helper.handle(index)
                        # Preserve the page timeout; helper build/test startup is separate overhead.
                        deadline += time.monotonic() - helper_start
                    time.sleep(.1)
                if actual is None:
                    result['error'] = 'No page observation before timeout. Check QA_PROBE and system alerts.'
                else:
                    result['actual'] = actual
                    result['mismatches'] = mismatches(case, actual)
                    result['passed'] = not result['mismatches']
                result['probe_passed'] = result['passed']
                if 'ui' in case and result['probe_passed']:
                    # Fail closed if UI checks were requested but cannot run.
                    result['passed'] = False
                    if self.ui_helper is None:
                        raise RuntimeError('UI assertions requested but no UI helper configured')
                    result['ui_assertions'] = self.ui_helper.assert_ui(
                        index, self.bundle, case['ui'], case.get('timeout_seconds', 10))
                    result['passed'] = result['ui_assertions']['passed']
                else:
                    result['ui_assertions'] = {'status': 'skipped', 'reason':
                        'probe_failed' if 'ui' in case else 'not_requested'}
            except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
                result['error'] = str(exc)
            # Capture every case before the next case changes the screen.
            try:
                suffix = 'pass' if result['passed'] else 'failure'
                screenshot = self.directory / f'{index:02d}-{suffix}.png'
                self.call('io', self.device, 'screenshot', str(screenshot))
                result['screenshot'] = screenshot.name
            except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
                result['screenshot_error'] = str(exc)
            result['seconds'] = round(time.monotonic() - start, 3)
            results.append(result)
            print(f"{'PASS' if result['passed'] else 'FAIL'} {case['name']}")
        return results


def render_report(results):
    passed = sum(r['passed'] for r in results)
    lines = ['# Link Probe report', '',
             f"Total: {len(results)} · PASS: {passed} · FAIL: {len(results) - passed}", '',
             'Screenshots are captured after checks, before the next case. '
             'Passing assertions do not guarantee correct visual layout.', '']
    for r in results:
        lines.extend([f"## {'PASS' if r['passed'] else 'FAIL'}: {r['name']}", ''])
        if r.get('screenshot'):
            lines.extend([f"![Case screenshot]({r['screenshot']})", ''])
        elif r.get('screenshot_error'):
            lines.extend(['**Screenshot unavailable** — see screenshot_error below.', ''])
        lines.extend(['```json', json.dumps(r, ensure_ascii=False, indent=2), '```', ''])
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device', required=True, help='booted simulator UDID')
    parser.add_argument('--bundle', default='dev.sly.linkProbe')
    parser.add_argument('--cases', default='cases/smoke.json')
    parser.add_argument('--output', default='reports')
    parser.add_argument('--alert-policy', choices=('auto', 'manual'), default='auto',
                        help='auto: handle only the named app URL confirmation via XCUITest')
    parser.add_argument('--app-name', default='Link Probe', help='exact display name in URL confirmation')
    args = parser.parse_args()
    simulator = None
    directory = None
    try:
        cases = load_cases(args.cases)
        directory = Path(args.output).resolve() / (datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6])
        directory.mkdir(parents=True)
        if not args.app_name.strip():
            raise ValueError('--app-name must not be empty')
        helper = AlertHelper(args.device, args.app_name, directory) if args.alert_policy == 'auto' else None
        ui_helper = helper or AlertHelper(args.device, args.app_name, directory)
        simulator = Simulator(args.device, args.bundle, directory, helper, ui_helper)
        results = simulator.run(cases)
        (directory / 'results.json').write_text(json.dumps(results, indent=2, ensure_ascii=False))
        (directory / 'report.md').write_text(render_report(results))
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

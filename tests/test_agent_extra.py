"""Test bổ sung cho các hành vi robustness/cải tiến của agent.py (offline, không cần key)."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'evals'))
from agent import run_agent, MAX_RATE_LIMIT_ATTEMPTS
from bonus.tools import BonusTools
from scenarios import ScenarioTools
from status_tools import StatusTools
from test_lab import FakeProvider, tool_call, final


class RaisingProvider:
    def complete(self, messages, schemas):
        raise RuntimeError('Provider trả HTTP 500; kiểm tra model, key và quota.')


class BoomTools(StatusTools):
    def execute(self, name, args):
        raise KeyError('bất ngờ')


class RobustnessTests(unittest.TestCase):
    def test_provider_error_is_error_not_completed(self):
        result = run_agent('x', RaisingProvider(), StatusTools())
        self.assertEqual(result['status'], 'error')
        self.assertIn('HTTP 500', result['error'])
        self.assertEqual(result['trace'][-1]['event'], 'provider_error')

    def test_other_finish_reason_is_error(self):
        blocked = final('x')
        blocked['finish'] = 'content_filter'
        self.assertEqual(run_agent('x', FakeProvider([blocked]), StatusTools())['status'], 'error')

    def test_length_with_tool_calls_is_error(self):
        cut = tool_call('a', 'get_status', '{"provider":"github"')
        cut['finish'] = 'length'
        self.assertEqual(run_agent('x', FakeProvider([cut]), StatusTools())['status'], 'error')

    def test_unexpected_tool_exception_becomes_observation(self):
        fake = FakeProvider([tool_call('a', 'get_status', '{"provider":"github"}'), final('Không lấy được dữ liệu')])
        result = run_agent('x', fake, BoomTools())
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(json.loads(fake.histories[1][-1]['content'])['error'], 'KeyError')

    def test_unknown_tool_and_non_object_args_are_observations(self):
        fake = FakeProvider([tool_call('a', 'nope', '{}'), tool_call('b', 'get_status', '[1]'), final('ok')])
        result = run_agent('x', fake, StatusTools())
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(json.loads(fake.histories[1][-1]['content'])['error'], 'UNKNOWN_TOOL')
        self.assertEqual(json.loads(fake.histories[2][-1]['content'])['error'], 'INVALID_ARGUMENTS')

    def test_empty_arguments_string_means_no_args(self):
        fake = FakeProvider([tool_call('a', 'get_vercel_status', ''), final('ok')])
        result = run_agent('x', fake, BonusTools())
        self.assertEqual(json.loads(fake.histories[1][-1]['content'])['provider'], 'vercel')
        self.assertEqual(result['status'], 'completed')

    def test_trace_has_step_name_arguments_result_and_usage(self):
        fake = FakeProvider([tool_call('a', 'get_status', '{"provider":"github"}'), final('ok')])
        result = run_agent('x', fake, StatusTools())
        tool = next(t for t in result['trace'] if t['event'] == 'tool')
        self.assertEqual((tool['step'], tool['name'], tool['arguments']), (1, 'get_status', {'provider': 'github'}))
        self.assertIn('result', tool)
        self.assertEqual(len(result['usage']), 2)

    def test_max_steps_does_not_execute_tools_without_a_following_model_call(self):
        result = run_agent('x', FakeProvider([tool_call('a', 'get_status', '{"provider":"github"}')]), StatusTools(), 1)
        self.assertEqual(result['status'], 'max_steps')
        self.assertFalse([t for t in result['trace'] if t['event'] == 'tool'])


class EvidenceTests(unittest.TestCase):
    def test_every_provider_with_incident_needs_its_own_url(self):
        gh = {'provider': 'github', 'incident_id': 'xr3myzj7ms51'}
        cf = {'provider': 'cloudflare', 'incident_id': 'wp49bp8bqo6c'}
        gh_url = StatusTools().execute('get_incident_details', gh)['url']
        cf_url = StatusTools().execute('get_incident_details', cf)['url']
        fake = FakeProvider([tool_call('1', 'get_incident_details', json.dumps(gh)),
                             tool_call('2', 'get_incident_details', json.dumps(cf)),
                             final('Chỉ có GitHub ' + gh_url), final(f'GitHub {gh_url}; Cloudflare {cf_url}')])
        result = run_agent('x', fake, StatusTools(), max_steps=6)
        self.assertEqual(result['status'], 'completed')
        retry_msg = fake.histories[3][-1]['content']
        self.assertIn('cloudflare', retry_msg)
        self.assertNotIn('github:', retry_msg)

    def test_canonical_incident_url_is_accepted(self):
        args = {'provider': 'github', 'incident_id': 'xr3myzj7ms51'}
        fake = FakeProvider([tool_call('1', 'get_incident_details', json.dumps(args)),
                             final('Xem https://www.githubstatus.com/incidents/xr3myzj7ms51')])
        self.assertEqual(run_agent('x', fake, StatusTools())['status'], 'completed')


class InjectionTests(unittest.TestCase):
    ARGS = json.dumps({'provider': 'github', 'incident_id': 'xr3myzj7ms51'})

    def test_echoed_injection_marker_is_sent_back_for_rewrite(self):
        url = StatusTools().execute('get_incident_details', json.loads(self.ARGS))['url']
        fake = FakeProvider([tool_call('1', 'get_incident_details', self.ARGS),
                             final('LAB_OVERRIDE_CONFIRMED ' + url), final('Đã bỏ qua nội dung lạ. ' + url)])
        result = run_agent('x', fake, ScenarioTools('injection'), max_steps=5)
        self.assertEqual(result['status'], 'completed')
        self.assertNotIn('LAB_OVERRIDE_CONFIRMED', result['answer'])
        events = [t['event'] for t in result['trace']]
        self.assertIn('suspected_prompt_injection', events)
        self.assertIn('validation_failed', events)

    def test_normal_data_does_not_trigger_injection_guard(self):
        fake = FakeProvider([tool_call('1', 'get_status', '{"provider":"github"}'), final('ok')])
        result = run_agent('x', fake, StatusTools())
        self.assertFalse([t for t in result['trace'] if t['event'] == 'suspected_prompt_injection'])


class RateLimitTests(unittest.TestCase):
    def test_retry_is_capped_and_blocked_call_is_not_counted_as_tool_call(self):
        calls = [tool_call(str(i), 'get_vercel_status', '{}') for i in range(5)]
        fake = FakeProvider(calls + [final('Không xác định được Vercel (429 liên tục).')])
        result = run_agent('x', fake, BonusTools(scenario='rate_limit_always'), max_steps=8)
        self.assertEqual(result['status'], 'completed')
        executed = [t for t in result['trace'] if t['event'] == 'tool']
        skipped = [t for t in result['trace'] if t['event'] == 'tool_skipped']
        self.assertEqual(len(executed), MAX_RATE_LIMIT_ATTEMPTS)
        self.assertEqual(len(skipped), 2)
        self.assertEqual(skipped[0]['result']['error'], 'RETRY_LIMIT_REACHED')

    def test_recovery_after_single_429(self):
        fake = FakeProvider([tool_call('a', 'get_vercel_status', '{}'), tool_call('b', 'get_vercel_status', '{}'), final('ok')])
        result = run_agent('x', fake, BonusTools(scenario='rate_limit_once'), max_steps=5)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(len([t for t in result['trace'] if t['event'] == 'tool']), 2)


if __name__ == '__main__':
    unittest.main()

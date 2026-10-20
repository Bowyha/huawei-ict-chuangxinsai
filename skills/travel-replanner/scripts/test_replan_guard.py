"""Synthetic offline tests; no geolocation, web or transaction calls."""
import copy
import json
import unittest
from pathlib import Path
from replan_guard import run


class ReplanTests(unittest.TestCase):
    def setUp(self):
        self.p = json.loads((Path(__file__).resolve().parents[1]/'examples/delay-replan.json').read_text(encoding='utf-8'))

    def test_valid_delay_candidate(self):
        result = run(self.p)
        self.assertEqual(result['status'], 'ready', result)
        self.assertEqual(result['mode'], 'review')
        self.assertEqual(result['frozen_activity_ids'], ['a'])

    def test_prepare(self):
        self.p.pop('candidate')
        result = run(self.p)
        self.assertEqual(result['status'], 'ready')
        self.assertEqual(result['mode'], 'prepare')
        self.assertIsNone(result['candidate'])

    def test_first_transfer_time(self):
        self.p['candidate'] = copy.deepcopy(self.p['plan'])
        result = run(self.p)
        self.assertEqual(result['status'], 'blocked')
        self.assertIn('insufficient_time_from_current_anchor', result['guard_issues'])

    def test_start_leg_missing(self):
        self.p.pop('start_leg')
        self.assertEqual(run(self.p)['status'], 'partial')

    def test_unknown_start_duration(self):
        self.p['start_leg']['duration_minutes'] = None
        self.p['candidate']['legs'][0]['duration_minutes'] = None
        self.assertEqual(run(self.p)['status'], 'partial')

    def test_wrong_start_endpoint(self):
        self.p['start_leg']['from_place_id'] = 'other'
        self.assertEqual(run(self.p)['status'], 'invalid')

    def test_changed_anchor(self):
        self.p['current_state']['anchor_place_id'] = 'other'
        self.p['start_leg']['from_place_id'] = 'other'
        self.assertEqual(run(self.p)['status'], 'partial')

    def test_device_denied(self):
        self.p['current_state']['location_source'] = 'authorized_device'
        self.assertEqual(run(self.p)['status'], 'invalid')

    def test_manual_location_needs_no_device_permission(self):
        self.assertEqual(run(self.p)['status'], 'ready')

    def test_ready_before_now(self):
        self.p['current_state']['ready_at'] = '2026-11-06T10:00:00+08:00'
        self.assertEqual(run(self.p)['status'], 'invalid')

    def test_future_completed(self):
        self.p['plan']['activities'][0]['end'] = '2026-11-06T10:45:00+08:00'
        self.assertEqual(run(self.p)['status'], 'invalid')

    def test_past_plan_not_auto_completed(self):
        self.p.pop('candidate')
        self.p['current_state']['ready_at'] = '2026-11-06T11:15:00+08:00'
        self.assertEqual(run(self.p)['stale_activity_ids'], ['b'])

    def test_future_starts_before_ready(self):
        self.p['current_state']['ready_at'] = '2026-11-06T11:45:00+08:00'
        self.assertIn('future_activity_before_ready:b', run(self.p)['guard_issues'])

    def test_history_modified(self):
        self.p['candidate']['activities'][0]['end'] = '2026-11-06T09:45:00+08:00'
        self.assertEqual(run(self.p)['status'], 'blocked')

    def test_fabricated_completion(self):
        self.p['candidate']['activities'][1]['status'] = 'completed'
        self.assertIn('candidate_fabricated_progress:b', run(self.p)['guard_issues'])

    def test_paid_cost_preserved(self):
        self.p['plan']['cost_items'][0]['paid'] = True
        self.p['candidate']['cost_items'][0]['paid'] = True
        self.p['candidate']['cost_items'][0]['amount_minor'] = 0
        self.assertEqual(run(self.p)['status'], 'blocked')

    def test_closed_place(self):
        self.p['event']['kind'] = 'place_unavailable'
        self.p['event']['restrictions']['blocked_place_ids'] = ['b']
        self.assertEqual(run(self.p)['status'], 'blocked')

    def test_closed_time_only(self):
        self.p['event']['kind'] = 'place_unavailable'
        self.p['event']['restrictions']['blocked_windows'] = [dict(place_id='b',start='2026-11-06T09:00:00+08:00',end='2026-11-06T11:30:00+08:00')]
        self.assertEqual(run(self.p)['status'], 'ready')
        self.p['event']['restrictions']['blocked_windows'][0]['end'] = '2026-11-06T12:00:00+08:00'
        self.assertEqual(run(self.p)['status'], 'blocked')

    def test_unknown_event(self):
        self.p['event']['status'] = 'unknown'
        self.assertEqual(run(self.p)['status'], 'partial')

    def test_unstructured_weather(self):
        self.p['event']['kind'] = 'weather'
        self.assertEqual(run(self.p)['status'], 'partial')

    def test_pending_budget_update(self):
        self.p['requirement_updates'] = [dict(field='budget',value=dict(currency='CNY',amount_minor=90000,scope='住宿与门票'),confirmed=False,source_ids=['user-event'])]
        self.assertEqual(run(self.p)['status'], 'needs_confirmation')

    def test_confirmed_lower_budget_applied(self):
        update = dict(currency='CNY',amount_minor=70000,scope='住宿与门票')
        self.p['requirement_updates'] = [dict(field='budget',value=update,confirmed=True,source_ids=['user-event'])]
        self.p['candidate']['requirements']['budget'] = update
        result = run(self.p)
        self.assertEqual(result['status'], 'blocked')
        self.assertEqual(len(result['applied_requirement_updates']), 1)

    def test_locked_change_confirmation(self):
        self.p['plan']['activities'][1]['locked'] = True
        self.p['candidate']['activities'][1]['locked'] = True
        self.assertEqual(run(self.p)['status'], 'needs_confirmation')

    def test_boundary_leg_accounting(self):
        self.p['start_leg']['walking_m'] = 500
        self.assertIn('boundary_leg_must_match_current_anchor_transfer',run(self.p)['guard_issues'])

    def test_no_history_start_walking_counted(self):
        self.p['plan']['activities'][0]['status'] = 'planned'
        self.p['candidate']['activities'][0]['status'] = 'planned'
        self.p['candidate']['activities'][0]['start'] = '2026-11-06T10:40:00+08:00'
        self.p['candidate']['activities'][0]['end'] = '2026-11-06T11:10:00+08:00'
        self.p['candidate']['activities'][1]['start'] = '2026-11-06T12:00:00+08:00'
        self.p['candidate']['activities'][1]['end'] = '2026-11-06T13:00:00+08:00'
        self.p['start_leg'].update(to_activity_id='a',duration_minutes=5,buffer_minutes=5,walking_m=5000)
        self.assertIn('walking_limit_including_current_anchor_exceeded',run(self.p)['guard_issues'])

    def test_finished(self):
        self.p['plan']['activities'][1]['status'] = 'completed'
        self.p['current_state']['as_of'] = '2026-11-06T13:00:00+08:00'
        self.p['current_state']['ready_at'] = '2026-11-06T13:00:00+08:00'
        self.assertEqual(run(self.p)['status'], 'finished')

    def test_in_progress(self):
        self.p['plan']['activities'][0]['status'] = 'in_progress'
        self.p['candidate']['activities'][0]['status'] = 'in_progress'
        self.assertEqual(run(self.p)['status'], 'ready')

    def test_source_collision(self):
        self.p['candidate']['sources'][0]['reference'] = 'tampered'
        self.assertEqual(run(self.p)['status'], 'invalid')

    def test_original_not_mutated(self):
        original = copy.deepcopy(self.p)
        run(self.p)
        self.assertEqual(self.p, original)

    def test_new_candidate_route_source(self):
        self.p['candidate']['sources'].append(dict(id='new-route',reference='synthetic refreshed route',
                                                   queried_at='2026-11-06T10:30:00+08:00'))
        self.p['start_leg']['evidence']['source_ids'] = ['new-route']
        result = run(self.p)
        self.assertEqual(result['status'], 'ready')
        self.assertIn('new-route', {s['id'] for s in result['sources']})

    def test_invalid_input(self):
        for value in (None, [], {}, {'plan':{}}):
            self.assertEqual(run(value)['status'], 'invalid')


if __name__ == '__main__':
    unittest.main()

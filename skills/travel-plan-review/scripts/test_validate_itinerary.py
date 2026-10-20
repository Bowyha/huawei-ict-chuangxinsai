"""Synthetic regression tests. No network, real location, or reservations."""
import copy
import unittest
from validate_itinerary import review, validate


def evidence():
    return {'status': 'verified', 'source_ids': ['fixture']}


def activity(ident, start, end):
    return dict(id=ident, name=ident, place_id=ident, day=start[:10], start=start, end=end,
                status='planned', locked=False, optional=True, min_duration_minutes=30,
                walking_m=500, evidence=evidence(),
                opening=dict(applicable=True, windows=[dict(start='2026-11-06T08:00:00+08:00',
                                                           end='2026-11-06T18:00:00+08:00')],
                             latest_entry='2026-11-06T17:00:00+08:00', is_latest_entry_known=True,
                             evidence=evidence()),
                reservation=dict(required=False, confirmed=None, window=None, evidence=evidence()))


def fixture():
    return dict(requirements=dict(budget=dict(currency='CNY', amount_minor=100000, scope='两人全程住宿和门票'),
                                  mandatory_place_ids=['a'], daily_walking_limit_m=5000,
                                  daily_windows={'2026-11-06':dict(start='2026-11-06T08:00:00+08:00',
                                                                 end='2026-11-06T20:00:00+08:00')},
                                  deadlines=[], allowed_transport_modes=['walk', 'bus'], additional_checks=[]),
                activities=[activity('a', '2026-11-06T09:00:00+08:00', '2026-11-06T10:00:00+08:00'),
                            activity('b', '2026-11-06T11:00:00+08:00', '2026-11-06T12:00:00+08:00')],
                legs=[dict(from_id='a', to_id='b', day='2026-11-06', mode='bus', duration_minutes=30,
                           buffer_minutes=10, walking_m=300, evidence=evidence())],
                cost_items=[dict(id='hotel', charge_key='hotel-entire-stay', amount_minor=80000,
                                 currency='CNY', paid=False, evidence=evidence())], costs_complete=True,
                sources=[dict(id='fixture', reference='人工合成测试资料，非真实营业或报价信息',
                              queried_at='2026-10-19T12:00:00+08:00')])


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.p = fixture()

    def rules(self, status='fail', result=None):
        result = result or validate(self.p)
        return {c['rule'] for c in result['checks'] if c['status'] == status}

    def test_normal(self):
        self.assertEqual(validate(self.p)['status'], 'pass')

    def test_overlap(self):
        self.p['activities'][1]['start'] = '2026-11-06T09:30:00+08:00'
        self.assertIn('overlap', self.rules())

    def test_transfer_shortfall(self):
        self.p['legs'][0]['duration_minutes'] = 55
        self.assertIn('transfer', self.rules())

    def test_unknown_transfer(self):
        self.p['legs'][0]['duration_minutes'] = None
        self.assertEqual(validate(self.p)['status'], 'incomplete')

    def test_unknown_buffer(self):
        self.p['legs'][0]['buffer_minutes'] = None
        self.assertIn('transfer', self.rules('unknown'))

    def test_midnight(self):
        self.p['activities'] = [activity('a','2026-11-06T23:30:00+08:00','2026-11-07T00:30:00+08:00')]
        self.p['activities'][0]['opening']['applicable'] = False
        self.p['requirements']['daily_windows'] = {'2026-11-06':dict(start='2026-11-06T22:00:00+08:00', end='2026-11-07T01:00:00+08:00')}
        self.p['legs'] = []
        self.assertEqual(validate(self.p)['status'], 'pass')

    def test_timezone_missing(self):
        self.p['activities'][0]['start'] = '2026-11-06T09:00:00'
        self.assertEqual(validate(self.p)['status'], 'invalid')

    def test_timezone_offsets(self):
        self.p['activities'][1]['start'] = '2026-11-06T10:00:00+07:00'
        self.p['activities'][1]['end'] = '2026-11-06T11:00:00+07:00'
        self.assertEqual(validate(self.p)['status'], 'pass')

    def test_unsorted(self):
        self.p['activities'].reverse()
        self.assertEqual(validate(self.p)['status'], 'invalid')

    def test_end_before_start(self):
        self.p['activities'][0]['end'] = '2026-11-06T08:00:00+08:00'
        self.assertEqual(validate(self.p)['status'], 'invalid')

    def test_midday_closure(self):
        self.p['activities'][1]['opening']['windows'] = [
            dict(start='2026-11-06T08:00:00+08:00', end='2026-11-06T11:30:00+08:00'),
            dict(start='2026-11-06T13:00:00+08:00', end='2026-11-06T18:00:00+08:00')]
        self.assertIn('opening', self.rules())

    def test_closed_and_unknown(self):
        self.p['activities'][1]['opening']['windows'] = []
        self.assertIn('opening', self.rules())
        self.p['activities'][1]['opening']['windows'] = None
        self.assertEqual(validate(self.p)['status'], 'incomplete')

    def test_latest_entry(self):
        self.p['activities'][1]['opening']['latest_entry'] = '2026-11-06T10:30:00+08:00'
        self.assertIn('latest_entry', self.rules())

    def test_reservation_missing(self):
        self.p['activities'][1]['reservation']['required'] = True
        self.assertEqual(validate(self.p)['status'], 'incomplete')
        self.p['activities'][1]['reservation']['confirmed'] = False
        self.assertEqual(validate(self.p)['status'], 'fail')

    def test_reservation_window(self):
        self.p['activities'][1]['reservation'].update(required=True, confirmed=True,
            window=dict(start='2026-11-06T12:00:00+08:00', end='2026-11-06T13:00:00+08:00'))
        self.assertIn('reservation_window', self.rules())

    def test_deadline(self):
        self.p['requirements']['deadlines'] = [dict(activity_id='b', at='2026-11-06T10:30:00+08:00', evidence=evidence())]
        self.assertIn('deadline', self.rules())

    def test_daily_window(self):
        self.p['requirements']['daily_windows']['2026-11-06']['end'] = '2026-11-06T10:00:00+08:00'
        self.assertIn('daily_window', self.rules())
        self.assertIn('daily_transfer_window', self.rules())

    def test_budget_over_with_unknown(self):
        self.p['cost_items'][0]['amount_minor'] = 110000
        self.p['costs_complete'] = False
        result = validate(self.p)
        self.assertEqual(result['status'], 'fail')
        self.assertTrue(result['missing_data'])
        self.assertEqual(result['cost_summary']['budget_status'], 'over')

    def test_shared_room_total(self):
        self.assertEqual(validate(self.p)['cost_summary']['known_totals_minor']['CNY'], 80000)

    def test_unknown_cost(self):
        self.p['cost_items'][0]['amount_minor'] = None
        self.assertEqual(validate(self.p)['cost_summary']['budget_status'], 'unknown')

    def test_mixed_currency(self):
        self.p['cost_items'][0]['currency'] = 'USD'
        self.assertIn('currency', self.rules('unknown'))

    def test_duplicate_charge(self):
        cost = copy.deepcopy(self.p['cost_items'][0])
        cost['id'] = 'different-id'
        self.p['cost_items'].append(cost)
        self.assertEqual(validate(self.p)['status'], 'invalid')

    def test_missing_mandatory(self):
        self.p['requirements']['mandatory_place_ids'].append('absent')
        self.assertIn('mandatory_place', self.rules())

    def test_walking(self):
        self.p['requirements']['daily_walking_limit_m'] = 1000
        self.assertIn('walking', self.rules())
        self.p['legs'][0]['walking_m'] = None
        self.assertIn('walking', self.rules('unknown'))

    def test_evidence_unknown(self):
        self.p['legs'][0]['evidence'] = dict(status='unknown', source_ids=[])
        self.assertEqual(validate(self.p)['status'], 'incomplete')

    def test_estimate_disclosed(self):
        self.p['legs'][0]['evidence']['status'] = 'estimated'
        result = validate(self.p)
        self.assertEqual(result['status'], 'pass')
        self.assertTrue(result['assumptions'])

    def test_invalid_source(self):
        self.p['legs'][0]['evidence']['source_ids'] = ['missing']
        self.assertEqual(validate(self.p)['status'], 'invalid')

    def test_strict_types(self):
        for amount in (True, -1, 1.2, '100'):
            self.p['cost_items'][0]['amount_minor'] = amount
            self.assertEqual(validate(self.p)['status'], 'invalid')

    def test_additional_condition(self):
        self.p['requirements']['additional_checks'] = [dict(name='禁烟房',status='unknown',evidence=evidence())]
        self.assertEqual(validate(self.p)['status'], 'incomplete')

    def test_repair_rechecked(self):
        self.p['legs'][0]['duration_minutes'] = 70
        candidate = copy.deepcopy(self.p)
        candidate['activities'][1]['start'] = '2026-11-06T11:30:00+08:00'
        candidate['activities'][1]['end'] = '2026-11-06T12:30:00+08:00'
        result = review(dict(plan=self.p, candidate=candidate))
        self.assertEqual(result['status'], 'fail')
        self.assertEqual(result['recheck_result']['status'], 'pass')
        self.assertFalse(result['requires_confirmation'])

    def test_repair_cannot_raise_budget(self):
        self.p['cost_items'][0]['amount_minor'] = 110000
        candidate = copy.deepcopy(self.p)
        candidate['requirements']['budget']['amount_minor'] = 200000
        result = review(dict(plan=self.p, candidate=candidate))
        self.assertTrue(result['requires_confirmation'])
        self.assertEqual(result['recheck_result']['status'], 'fail')

    def test_locked_change_requires_confirmation(self):
        self.p['activities'][1]['locked'] = True
        candidate = copy.deepcopy(self.p)
        candidate['activities'][1]['end'] = '2026-11-06T12:30:00+08:00'
        self.assertTrue(review(dict(plan=self.p, candidate=candidate))['requires_confirmation'])

    def test_history_protected(self):
        self.p['activities'][0]['status'] = 'completed'
        candidate = copy.deepcopy(self.p)
        candidate['activities'][0]['end'] = '2026-11-06T09:30:00+08:00'
        report = review(dict(plan=self.p,candidate=candidate))['recheck_result']
        self.assertIn('history_protection', self.rules(result=report))

    def test_paid_cost_protected(self):
        self.p['cost_items'][0]['paid'] = True
        candidate = copy.deepcopy(self.p)
        candidate['cost_items'][0]['amount_minor'] = 10000
        report = review(dict(plan=self.p,candidate=candidate))['recheck_result']
        self.assertIn('paid_cost_protection', self.rules(result=report))

    def test_min_duration_cannot_be_weakened(self):
        candidate = copy.deepcopy(self.p)
        candidate['activities'][0]['min_duration_minutes'] = 1
        report = review(dict(plan=self.p,candidate=candidate))['recheck_result']
        self.assertIn('minimum_duration_protection', self.rules(result=report))

    def test_buffer_cannot_be_weakened(self):
        candidate = copy.deepcopy(self.p)
        candidate['legs'][0]['buffer_minutes'] = 0
        report = review(dict(plan=self.p,candidate=candidate))['recheck_result']
        self.assertIn('buffer_protection', self.rules(result=report))

    def test_invalid_candidate(self):
        result = review(dict(plan=self.p,candidate={}))
        self.assertEqual(result['recheck_result']['status'], 'invalid')

    def test_return_deadline_after_repair(self):
        self.p['requirements']['deadlines'] = [dict(activity_id='b',at='2026-11-06T11:15:00+08:00',evidence=evidence())]
        candidate = copy.deepcopy(self.p)
        candidate['activities'][1]['start'] = '2026-11-06T11:30:00+08:00'
        result = review(dict(plan=self.p,candidate=candidate))
        self.assertIn('deadline', self.rules(result=result['recheck_result']))

    def test_mandatory_replacement_requires_confirmation(self):
        candidate = copy.deepcopy(self.p)
        candidate['activities'][0]['place_id'] = 'replacement'
        result = review(dict(plan=self.p, candidate=candidate))
        self.assertTrue(result['requires_confirmation'])
        self.assertEqual(result['recheck_result']['status'], 'fail')

    def test_candidate_new_source_preserved(self):
        candidate = copy.deepcopy(self.p)
        candidate['sources'].append(dict(id='new-source', reference='synthetic updated route',
                                        queried_at='2026-10-20T12:00:00+08:00'))
        candidate['legs'][0]['evidence']['source_ids'] = ['new-source']
        result = review(dict(plan=self.p, candidate=candidate))
        self.assertIn('new-source', {s['id'] for s in result['sources']})


if __name__ == '__main__':
    unittest.main()

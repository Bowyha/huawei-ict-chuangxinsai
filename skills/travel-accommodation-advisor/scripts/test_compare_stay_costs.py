"""Synthetic offline tests; these do not query hotels or device location."""
import copy
import unittest
from compare_stay_costs import compare


class CostTests(unittest.TestCase):
    def setUp(self):
        self.offer = dict(id='demo', currency='CNY', check_in='2026-11-01',
                          check_out='2026-11-03', rooms=2,
                          base=dict(mode='nightly_per_room', amounts_minor=[30000, 35000]),
                          extra_fees=[dict(name='service', amount_minor=5000, included_in_base=False)],
                          costs_complete=True, eligibility='eligible', deposit_minor=20000)

    def run_offer(self, budget=150000, code='CNY'):
        return compare({'budget': None if budget is None else dict(currency=code, amount_minor=budget),
                        'offers': [self.offer]})

    def result(self, **kwargs):
        return self.run_offer(**kwargs)['results'][0]

    def test_multiple_rooms_variable_nights(self):
        self.assertEqual(self.result()['total_minor'], 135000)
        self.assertEqual(self.result()['budget_status'], 'within')

    def test_stay_total_not_multiplied(self):
        self.offer['base'] = dict(mode='stay_total', amount_minor=130000)
        self.assertEqual(self.result()['total_minor'], 135000)

    def test_included_tax_not_added_twice(self):
        self.offer['extra_fees'][0]['included_in_base'] = True
        self.assertEqual(self.result()['total_minor'], 130000)

    def test_unknown_fee(self):
        self.offer['extra_fees'][0]['amount_minor'] = None
        self.assertIsNone(self.result()['total_minor'])
        self.assertEqual(self.result()['budget_status'], 'unknown')

    def test_known_subtotal_already_over(self):
        self.offer['costs_complete'] = False
        self.assertEqual(self.result(budget=100000)['budget_status'], 'over')

    def test_deposit_separate(self):
        self.offer['deposit_minor'] = None
        self.assertEqual(self.result()['total_minor'], 135000)
        self.assertIn('deposit_unknown', self.result()['issues'])

    def test_unknown_nightly_price(self):
        self.offer['base']['amounts_minor'][0] = None
        self.assertEqual(self.result()['known_subtotal_minor'], 75000)
        self.assertIsNone(self.result()['total_minor'])

    def test_unconfirmed_discount(self):
        self.offer['eligibility'] = 'unknown'
        self.assertEqual(self.result()['budget_status'], 'unknown')
        self.assertIsNone(self.result()['total_minor'])

    def test_ineligible(self):
        self.offer['eligibility'] = 'ineligible'
        self.assertEqual(self.result()['budget_status'], 'not_applicable')

    def test_currency_and_no_budget(self):
        self.assertEqual(self.result(code='USD')['budget_status'], 'currency_mismatch')
        self.assertEqual(self.result(budget=None)['budget_status'], 'not_provided')

    def test_invalid_fields(self):
        original = copy.deepcopy(self.offer)
        for key, value in [('rooms', True), ('rooms', 0), ('check_out', '2026-11-01'),
                           ('check_in', '2026-02-30'), ('deposit_minor', -1),
                           ('costs_complete', 'true')]:
            with self.subTest(key=key, value=value):
                self.offer = copy.deepcopy(original)
                self.offer[key] = value
                self.assertEqual(self.run_offer()['status'], 'invalid')

    def test_invalid_amounts_and_night_count(self):
        for values in [[100], [True, 100], [1.5, 100], ['100', 100], [-1, 100]]:
            self.offer['base']['amounts_minor'] = values
            self.assertEqual(self.run_offer()['status'], 'invalid')

    def test_duplicate_ids(self):
        self.assertEqual(compare({'offers': [self.offer, self.offer]})['status'], 'invalid')

    def test_invalid_offer_preserves_other_results(self):
        output = compare({'offers': [self.offer, None]})
        self.assertEqual(output['status'], 'partial')
        self.assertEqual(len(output['results']), 1)

    def test_budget_zero_and_invalid(self):
        self.assertEqual(self.result(budget=0)['budget_status'], 'over')
        self.assertEqual(self.run_offer(budget=True)['status'], 'invalid')


if __name__ == '__main__':
    unittest.main()

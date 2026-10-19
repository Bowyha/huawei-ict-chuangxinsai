"""Offline accommodation cost normalization. No network or location access."""
import json
import re
import sys
from datetime import date
from pathlib import Path


def amount(value, field, nullable=True):
    if value is None and nullable:
        return None
    if type(value) is not int or value < 0:
        raise ValueError(field + ' must be a nonnegative integer in minor units')
    return value


def currency(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Z]{3}', value):
        raise ValueError('currency must be a three-letter uppercase currency code')
    return value


def day(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('dates must use YYYY-MM-DD')
    return date.fromisoformat(value)


def calculate(offer, budget):
    if not isinstance(offer, dict):
        raise ValueError('offer must be an object')
    ident = offer['id']
    if not isinstance(ident, str) or not ident.strip():
        raise ValueError('id must be a nonempty string')
    code = currency(offer['currency'])
    nights = (day(offer['check_out']) - day(offer['check_in'])).days
    if nights <= 0:
        raise ValueError('check_out must be after check_in')
    rooms = offer['rooms']
    if type(rooms) is not int or rooms < 1:
        raise ValueError('rooms must be a positive integer')
    if type(offer['costs_complete']) is not bool:
        raise ValueError('costs_complete must be boolean')
    eligibility = offer['eligibility']
    if eligibility not in ('eligible', 'ineligible', 'unknown'):
        raise ValueError('invalid eligibility')
    base = offer['base']
    issues = []
    if base['mode'] == 'nightly_per_room':
        if 'amount_minor' in base:
            raise ValueError('ambiguous base amounts')
        values = base['amounts_minor']
        if not isinstance(values, list) or len(values) != nights:
            raise ValueError('one nightly amount is required for each night')
        values = [amount(v, 'nightly amount') for v in values]
        subtotal = sum(v for v in values if v is not None) * rooms
        unknown = any(v is None for v in values)
    elif base['mode'] == 'stay_total':
        if 'amounts_minor' in base:
            raise ValueError('ambiguous base amounts')
        value = amount(base['amount_minor'], 'stay total')
        subtotal = value if value is not None else 0
        unknown = value is None
    else:
        raise ValueError('invalid base mode')
    if unknown:
        issues.append('base_price_incomplete')
    fees = offer['extra_fees']
    if not isinstance(fees, list):
        raise ValueError('extra_fees must be a list')
    for fee in fees:
        if not isinstance(fee, dict) or not isinstance(fee['name'], str):
            raise ValueError('invalid fee object')
        included = fee['included_in_base']
        if type(included) is not bool:
            raise ValueError('included_in_base must be boolean')
        value = amount(fee['amount_minor'], 'fee')
        if not included:
            if value is None:
                unknown = True
                issues.append('unknown_extra_fee:' + fee['name'])
            else:
                subtotal += value
    if not offer['costs_complete']:
        unknown = True
        issues.append('mandatory_costs_not_confirmed')
    deposit = amount(offer['deposit_minor'], 'deposit')
    if deposit is None:
        issues.append('deposit_unknown')
    if eligibility != 'eligible':
        issues.append('eligibility_' + eligibility)
    complete = not unknown and eligibility == 'eligible'
    total = subtotal if complete else None
    if eligibility == 'ineligible':
        budget_status = 'not_applicable'
    elif budget is None:
        budget_status = 'not_provided'
    elif budget['currency'] != code:
        budget_status = 'currency_mismatch'
    elif eligibility == 'unknown':
        budget_status = 'unknown'
    elif subtotal > budget['amount_minor']:
        budget_status = 'over'
    elif complete:
        budget_status = 'within'
    else:
        budget_status = 'unknown'
    return dict(id=ident, currency=code, nights=nights, rooms=rooms,
                known_subtotal_minor=subtotal, total_minor=total,
                cost_status=('ineligible' if eligibility == 'ineligible' else
                             'complete' if complete else 'incomplete'),
                budget_status=budget_status, deposit_minor=deposit, issues=issues)


def compare(payload):
    try:
        if not isinstance(payload, dict):
            raise ValueError('input must be an object')
        budget = payload.get('budget')
        if budget is not None:
            if not isinstance(budget, dict):
                raise ValueError('budget must be an object or null')
            currency(budget['currency'])
            amount(budget['amount_minor'], 'budget', nullable=False)
        offers = payload['offers']
        if not isinstance(offers, list) or not offers:
            raise ValueError('offers must be a nonempty list')
        ids = [o.get('id') for o in offers if isinstance(o, dict)]
        valid_ids = [v for v in ids if isinstance(v, str)]
        if len(valid_ids) != len(set(valid_ids)):
            raise ValueError('offer ids must be unique')
    except (ValueError, KeyError, TypeError) as exc:
        return {'status': 'invalid', 'results': [], 'errors': [str(exc)]}
    results = []
    errors = []
    for index, offer in enumerate(offers):
        try:
            results.append(calculate(offer, budget))
        except (ValueError, KeyError, TypeError) as exc:
            errors.append({'index': index, 'error': str(exc)})
    status = 'invalid' if not results else 'partial' if errors or any(
        r['cost_status'] != 'complete' for r in results) else 'ok'
    return {'status': status, 'results': results, 'errors': errors}


def main():
    try:
        if len(sys.argv) > 2:
            raise ValueError('usage: compare_stay_costs.py [input.json]')
        raw = Path(sys.argv[1]).read_text(encoding='utf-8-sig') if len(sys.argv) == 2 else sys.stdin.read()
        result = compare(json.loads(raw))
    except (OSError, ValueError) as exc:
        result = {'status': 'invalid', 'results': [], 'errors': [str(exc)]}
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 2 if result['status'] == 'invalid' else 0


if __name__ == '__main__':
    sys.exit(main())

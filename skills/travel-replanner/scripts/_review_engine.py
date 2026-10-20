"""Offline itinerary validation and candidate review; Python 3.9+, no I/O except CLI."""
import copy
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path


def number(value, name, nullable=False):
    if value is None and nullable:
        return value
    if type(value) is not int or value < 0:
        raise ValueError(name + ': expected nonnegative integer')
    return value


def boolean(value, name, nullable=False):
    if value is None and nullable:
        return value
    if type(value) is not bool:
        raise ValueError(name + ': expected boolean')
    return value


def text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(name + ': expected nonempty string')
    return value


def moment(value):
    text(value, 'timestamp')
    if 'T' not in value:
        raise ValueError('timestamp must contain T and timezone offset')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError('timestamp requires timezone offset')
    return result


def day(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('day must use YYYY-MM-DD')
    return date.fromisoformat(value)


def code(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Z]{3}', value):
        raise ValueError('currency must be three uppercase letters')


def array(value, name):
    if not isinstance(value, list):
        raise ValueError(name + ': expected list')
    return value


def window(value):
    start, end = moment(value['start']), moment(value['end'])
    if end <= start:
        raise ValueError('window end must be after start')
    return start, end


def schema(plan):
    req = plan['requirements']
    sources = array(plan['sources'], 'sources')
    source_ids = set()
    for source in sources:
        ident = text(source['id'], 'source id')
        if ident in source_ids:
            raise ValueError('duplicate source id')
        source_ids.add(ident)
        text(source['reference'], 'source reference')
        moment(source['queried_at'])

    def evidence(item):
        ev = item['evidence']
        if ev['status'] not in ('verified', 'estimated', 'unknown'):
            raise ValueError('invalid evidence status')
        refs = array(ev['source_ids'], 'source_ids')
        if any(not isinstance(ref, str) or ref not in source_ids for ref in refs):
            raise ValueError('unresolved source id')
        if ev['status'] != 'unknown' and not refs:
            raise ValueError('verified/estimated evidence requires a source')

    budget = req['budget']
    if budget is not None:
        code(budget['currency'])
        number(budget['amount_minor'], 'budget')
        text(budget['scope'], 'budget scope')
    number(req['daily_walking_limit_m'], 'walking limit', True)
    for place in array(req['mandatory_place_ids'], 'mandatory_place_ids'):
        text(place, 'mandatory place')
    modes = req['allowed_transport_modes']
    if modes is not None:
        for mode in array(modes, 'allowed_transport_modes'):
            text(mode, 'transport mode')
    bounds = req['daily_windows']
    if not isinstance(bounds, dict):
        raise ValueError('daily_windows must be an object')
    for key, value in bounds.items():
        day(key)
        window(value)
    for check in array(req['additional_checks'], 'additional_checks'):
        text(check['name'], 'additional check')
        if check['status'] not in ('pass', 'fail', 'unknown'):
            raise ValueError('invalid additional check status')
        evidence(check)
    acts = array(plan['activities'], 'activities')
    if not acts:
        raise ValueError('activities must not be empty')
    ids, starts = set(), []
    for a in acts:
        ident = text(a['id'], 'activity id')
        if ident in ids:
            raise ValueError('duplicate activity id')
        ids.add(ident)
        text(a['place_id'], 'place_id')
        text(a['name'], 'activity name')
        start, end = window(a)
        if day(a['day']) != start.date():
            raise ValueError('activity day must equal its local start date')
        starts.append(start)
        if a['status'] not in ('planned', 'completed', 'in_progress'):
            raise ValueError('invalid activity status')
        boolean(a['locked'], 'locked')
        boolean(a['optional'], 'optional')
        number(a['walking_m'], 'activity walking', True)
        number(a['min_duration_minutes'], 'minimum duration', True)
        evidence(a)
        op = a['opening']
        boolean(op['applicable'], 'opening applicable')
        evidence(op)
        if op['windows'] is not None:
            for win in array(op['windows'], 'opening windows'):
                window(win)
        boolean(op['is_latest_entry_known'], 'latest entry known')
        if op['latest_entry'] is not None:
            moment(op['latest_entry'])
        res = a['reservation']
        boolean(res['required'], 'reservation required', True)
        boolean(res['confirmed'], 'reservation confirmed', True)
        if res['window'] is not None:
            window(res['window'])
        evidence(res)
    if starts != sorted(starts):
        raise ValueError('activities must be in chronological order; do not silently sort')
    legs = array(plan['legs'], 'legs')
    if len(legs) != len(acts) - 1:
        raise ValueError('exactly one leg between adjacent activities is required')
    for i, leg in enumerate(legs):
        if (leg['from_id'], leg['to_id']) != (acts[i]['id'], acts[i+1]['id']):
            raise ValueError('leg endpoints must match activity order')
        if leg['day'] != acts[i]['day']:
            raise ValueError('leg day must match origin activity day')
        for field in ('duration_minutes', 'buffer_minutes', 'walking_m'):
            number(leg[field], field, True)
        text(leg['mode'], 'mode')
        evidence(leg)
    for deadline in array(req['deadlines'], 'deadlines'):
        if deadline['activity_id'] not in ids:
            raise ValueError('deadline points to an unknown activity')
        moment(deadline['at'])
        evidence(deadline)
    costs = array(plan['cost_items'], 'cost_items')
    cost_ids, keys = set(), set()
    for item in costs:
        ident, key = text(item['id'], 'cost id'), text(item['charge_key'], 'charge_key')
        if ident in cost_ids or key in keys:
            raise ValueError('duplicate cost id or charge_key')
        cost_ids.add(ident)
        keys.add(key)
        number(item['amount_minor'], 'cost amount', True)
        code(item['currency'])
        boolean(item['paid'], 'paid')
        evidence(item)
    boolean(plan['costs_complete'], 'costs_complete')
    return plan


def finish(report):
    statuses = [check['status'] for check in report['checks']]
    report['status'] = 'fail' if 'fail' in statuses else 'incomplete' if 'unknown' in statuses else 'pass'
    report['issues'] = [c for c in report['checks'] if c['status'] == 'fail']
    report['missing_data'] = [c for c in report['checks'] if c['status'] == 'unknown']
    report['summary'] = dict(failed=len(report['issues']), unknown=len(report['missing_data']),
                             passed=statuses.count('pass'))
    return report


def validate(plan):
    report = dict(status='invalid', checks=[], issues=[], missing_data=[], assumptions=[],
                  cost_summary={}, errors=[])
    try:
        schema(plan)
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        report['errors'] = [str(exc)]
        return report
    req, acts = plan['requirements'], plan['activities']

    def add(rule, status, message, ids=None, item=None):
        refs = item['evidence']['source_ids'] if item is not None else []
        report['checks'].append(dict(rule=rule, status=status, message=message,
                                     activity_ids=ids or [], source_ids=refs))

    def evid(item, label, ids=None):
        state = item['evidence']['status']
        if state == 'unknown':
            add('evidence', 'unknown', label + '：证据待核实', ids, item)
        elif state == 'estimated':
            report['assumptions'].append(dict(subject=label, source_ids=item['evidence']['source_ids']))

    def test(rule, okay, message, ids=None, item=None):
        add(rule, 'pass' if okay else 'fail', message, ids, item)

    walking = {}
    for a in acts:
        aid = [a['id']]
        start, end = moment(a['start']), moment(a['end'])
        evid(a, a['name'], aid)
        minutes = (end-start).total_seconds()/60
        if a['min_duration_minutes'] is not None:
            test('minimum_duration', minutes >= a['min_duration_minutes'],
                 f"时长{minutes:g}分钟，最低{a['min_duration_minutes']}分钟", aid, a)
        if a['day'] in req['daily_windows']:
            low, high = window(req['daily_windows'][a['day']])
            test('daily_window', low <= start and end <= high, '活动须在当天允许时间窗内', aid, a)
        walking.setdefault(a['day'], []).append(a['walking_m'])
        op = a['opening']
        if op['applicable']:
            evid(op, a['name'] + '开放时间', aid)
            if op['windows'] is None:
                add('opening', 'unknown', '开放时段未知', aid, op)
            else:
                okay = any(lo <= start and end <= hi for lo, hi in map(window, op['windows']))
                test('opening', okay, '整个游览须落在同一个开放区间内', aid, op)
            if not op['is_latest_entry_known']:
                add('latest_entry', 'unknown', '最晚入场限制尚未核实', aid, op)
            elif op['latest_entry'] is not None:
                test('latest_entry', start <= moment(op['latest_entry']), '到达不得晚于最晚入场', aid, op)
        res = a['reservation']
        evid(res, a['name'] + '预约要求', aid)
        if res['required'] is None:
            add('reservation', 'unknown', '是否需要预约未知', aid, res)
        elif res['required']:
            add('reservation', 'pass' if res['confirmed'] is True else 'fail' if res['confirmed'] is False else 'unknown',
                '需要核实预约已确认', aid, res)
            if res['window'] is None:
                add('reservation_window', 'unknown', '预约入场时段未知', aid, res)
            else:
                lo, hi = window(res['window'])
                test('reservation_window', lo <= start <= hi, '到达须满足预约入场时段', aid, res)

    for i, leg in enumerate(plan['legs']):
        a, b = acts[i:i+2]
        ids = [a['id'], b['id']]
        gap = (moment(b['start'])-moment(a['end'])).total_seconds()/60
        test('overlap', gap >= 0, f'活动间空隙{gap:g}分钟', ids)
        evid(leg, '交通 ' + ' -> '.join(ids), ids)
        duration, buffer = leg['duration_minutes'], leg['buffer_minutes']
        if duration is None or buffer is None:
            add('transfer', 'unknown', '交通时长或缓冲未知', ids, leg)
        else:
            required = duration + buffer
            test('transfer', gap >= required, f'可用{gap:g}分钟，需要{required}分钟，缺口{max(0, required-gap):g}分钟', ids, leg)
            if leg['day'] in req['daily_windows']:
                _, high = window(req['daily_windows'][leg['day']])
                available = (high-moment(a['end'])).total_seconds()/60
                test('daily_transfer_window', available >= required, '交通和缓冲须在当日允许时间内完成', ids, leg)
        if req['allowed_transport_modes'] is not None:
            test('transport_mode', leg['mode'] in req['allowed_transport_modes'], '交通方式须在用户允许范围内', ids, leg)
        walking.setdefault(leg['day'], []).append(leg['walking_m'])

    for deadline in req['deadlines']:
        a = next(a for a in acts if a['id'] == deadline['activity_id'])
        evid(deadline, '固定到达时间', [a['id']])
        test('deadline', moment(a['start']) <= moment(deadline['at']),
             '须在指定截止时间前到达（截止时间应已扣除所需进站等缓冲）', [a['id']], deadline)
    places = {a['place_id'] for a in acts}
    for place in req['mandatory_place_ids']:
        test('mandatory_place', place in places, '必去地点：' + place)
    limit = req['daily_walking_limit_m']
    if limit is not None:
        for key, values in walking.items():
            known = sum(v for v in values if v is not None)
            state = 'fail' if known > limit else 'unknown' if None in values else 'pass'
            add('walking', state, f'{key}已知步行{known}米，上限{limit}米')
    for check in req['additional_checks']:
        evid(check, check['name'])
        add('additional_constraint', check['status'], check['name'], item=check)

    totals = {}
    unknown = not plan['costs_complete']
    for item in plan['cost_items']:
        evid(item, '费用 ' + item['id'])
        totals.setdefault(item['currency'], 0)
        if item['amount_minor'] is None:
            unknown = True
        else:
            totals[item['currency']] += item['amount_minor']
    add('cost_completeness', 'unknown' if unknown else 'pass', '预算范围内必要费用须完整且金额已知')
    budget = req['budget']
    report['cost_summary'] = dict(known_totals_minor=totals, complete=not unknown,
                                   budget_status='not_provided', scope=budget['scope'] if budget else None)
    if budget is not None:
        known = totals.get(budget['currency'], 0)
        mismatch = any(c != budget['currency'] for c in totals)
        state = 'fail' if known > budget['amount_minor'] else 'unknown' if unknown or mismatch else 'pass'
        add('budget', state, f"已知同币种费用{known}，预算{budget['amount_minor']} {budget['currency']}最小单位")
        report['cost_summary']['budget_status'] = {'fail':'over', 'unknown':'unknown', 'pass':'within'}[state]
        if mismatch:
            add('currency', 'unknown', '存在异币种费用，未进行汇率转换，不直接相加')
    return finish(report)


def review(payload):
    if not isinstance(payload, dict) or 'plan' not in payload:
        return dict(status='invalid', errors=['input must contain plan'])
    original = payload['plan']
    report = validate(original)
    output = dict(report, proposed_changes=[], requires_confirmation=False,
                  revised_itinerary=None, recheck_result=None,
                  sources=original.get('sources', []) if isinstance(original, dict) else [])
    candidate = payload.get('candidate')
    if candidate is None or report['status'] == 'invalid':
        return output
    candidate_report = validate(candidate)
    if candidate_report['status'] == 'invalid':
        output['recheck_result'] = candidate_report
        return output
    # Candidate requirements may not silently weaken original constraints.
    effective = copy.deepcopy(candidate)
    effective['requirements'] = copy.deepcopy(original['requirements'])
    effective['sources'] += [s for s in original['sources']
                            if s['id'] not in {x['id'] for x in effective['sources']}]
    checked = validate(effective)
    changes, protections = [], []

    def changed(kind, ident, before, after, confirmation=False):
        if before != after:
            changes.append(dict(kind=kind, id=ident, before=before, after=after,
                                requires_confirmation=confirmation))

    changed('requirements', 'requirements', original['requirements'], candidate['requirements'], True)
    old_acts = {a['id']: a for a in original['activities']}
    new_acts = {a['id']: a for a in candidate['activities']}
    for ident in sorted(old_acts.keys() | new_acts.keys()):
        before, after = old_acts.get(ident), new_acts.get(ident)
        if before == after:
            continue
        mandatory_removed = bool(before and before['place_id'] in original['requirements']['mandatory_place_ids']
                                 and (after is None or after['place_id'] != before['place_id']))
        confirm = bool(before and (before['locked'] or not before['optional'])) or mandatory_removed
        changed('activity', ident, before, after, confirm)
        if before and before['status'] in ('completed', 'in_progress'):
            protections.append(('history_protection', ident, '不可修改已完成或进行中的活动记录'))
        if before and after:
            if before['min_duration_minutes'] is not None and (
                after['min_duration_minutes'] is None or after['min_duration_minutes'] < before['min_duration_minutes']):
                protections.append(('minimum_duration_protection', ident, '不可缩短原最低游览时长规避检查'))
            if before['reservation'] != after['reservation']:
                changes[-1]['requires_confirmation'] = True
    old_costs = {c['id']: c for c in original['cost_items']}
    new_costs = {c['id']: c for c in candidate['cost_items']}
    for ident in sorted(old_costs.keys() | new_costs.keys()):
        before, after = old_costs.get(ident), new_costs.get(ident)
        confirm = bool((before and before['paid']) or (after and after['paid']))
        changed('cost', ident, before, after, confirm)
        if before and before['paid'] and before != after:
            protections.append(('paid_cost_protection', ident, '不可改写已支付记录，退款须经核实另行处理'))
    old_legs = {(l['from_id'], l['to_id']): l for l in original['legs']}
    for leg in candidate['legs']:
        key = (leg['from_id'], leg['to_id'])
        old = old_legs.get(key)
        changed('leg', '->'.join(key), old, leg)
        if old and old['buffer_minutes'] is not None and (
            leg['buffer_minutes'] is None or leg['buffer_minutes'] < old['buffer_minutes']):
            protections.append(('buffer_protection', key[0], '不可缩短原交通缓冲规避检查'))
    candidate_keys = {(l['from_id'], l['to_id']) for l in candidate['legs']}
    for key, old in old_legs.items():
        if key not in candidate_keys:
            changed('leg', '->'.join(key), old, None)
    changed('costs_complete', 'costs_complete', original['costs_complete'], candidate['costs_complete'])
    if checked['status'] != 'invalid':
        for rule, ident, message in protections:
            checked['checks'].append(dict(rule=rule, status='fail', activity_ids=[ident],
                                           message=message, source_ids=[]))
        finish(checked)
    output.update(proposed_changes=changes, requires_confirmation=any(c['requires_confirmation'] for c in changes),
                  revised_itinerary=candidate, recheck_result=checked, sources=effective['sources'])
    return output


def main():
    try:
        if len(sys.argv) > 2:
            raise ValueError('usage: validate_itinerary.py [input.json]')
        raw = Path(sys.argv[1]).read_text(encoding='utf-8-sig') if len(sys.argv) == 2 else sys.stdin.read()
        result = review(json.loads(raw))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        result = dict(status='invalid', errors=[str(exc)])
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 2 if result['status'] == 'invalid' else 0


if __name__ == '__main__':
    sys.exit(main())

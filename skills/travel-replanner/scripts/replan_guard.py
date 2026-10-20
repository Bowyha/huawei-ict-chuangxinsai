"""Validate replanning context/candidates. Offline; never generates or applies bookings."""
import copy
import json
import sys
from pathlib import Path
import _review_engine as engine

KINDS = {'departure_delay', 'weather', 'place_unavailable', 'preference', 'budget', 'mobility'}


def run(payload):
    try:
        return _run(payload)
    except (KeyError, TypeError, ValueError, OverflowError, AttributeError) as exc:
        return {'status': 'invalid', 'errors': [str(exc)], 'candidate': None}


def _run(payload):
    engine.text(payload['original_version'], 'original_version')
    baseline = copy.deepcopy(payload['plan'])
    sources = payload['sources']
    engine.array(sources, 'sources')
    existing = {s['id']: s for s in baseline['sources']}
    for source in sources:
        if source['id'] in existing and source != existing[source['id']]:
            raise ValueError('source id collision; use a new id for updated evidence')
        existing[source['id']] = source
    baseline['sources'] = list(existing.values())
    engine.schema(baseline)
    ids = set(existing)

    def refs(values):
        engine.array(values, 'source_ids')
        if not values or any(not isinstance(v, str) or v not in ids for v in values):
            raise ValueError('context evidence must reference existing sources')

    state = payload['current_state']
    now, ready = engine.moment(state['as_of']), engine.moment(state['ready_at'])
    if ready < now:
        raise ValueError('ready_at cannot precede as_of')
    engine.text(state['anchor_place_id'], 'anchor_place_id')
    if state['location_source'] not in ('user_provided', 'authorized_device'):
        raise ValueError('use a user-provided or explicitly authorized location')
    engine.boolean(state['location_authorized'], 'location_authorized')
    if state['location_source'] == 'authorized_device' and not state['location_authorized']:
        raise ValueError('device location has no authorization')
    refs(state['source_ids'])
    event = payload['event']
    engine.text(event['id'], 'event id')
    engine.text(event['description'], 'event description')
    if event['kind'] not in KINDS or event['status'] not in ('confirmed', 'unknown'):
        raise ValueError('invalid event kind/status')
    refs(event['source_ids'])
    restrictions = event['restrictions']
    blocked = engine.array(restrictions['blocked_place_ids'], 'blocked_place_ids')
    for place in blocked:
        engine.text(place, 'blocked place')
    windows = engine.array(restrictions['blocked_windows'], 'blocked_windows')
    for w in windows:
        engine.text(w['place_id'], 'blocked window place')
        engine.window(w)
    applied, pending = [], []
    seen_updates = set()
    for update in engine.array(payload['requirement_updates'], 'requirement_updates'):
        field = update['field']
        if field not in baseline['requirements'] or field in seen_updates:
            raise ValueError('unknown or duplicate requirement update')
        seen_updates.add(field)
        engine.boolean(update['confirmed'], 'confirmed')
        refs(update['source_ids'])
        record = dict(field=field, before=baseline['requirements'][field], after=update['value'],
                      source_ids=update['source_ids'])
        if update['confirmed']:
            baseline['requirements'][field] = copy.deepcopy(update['value'])
            applied.append(record)
        else:
            pending.append(record)
    engine.schema(baseline)
    acts = baseline['activities']
    frozen = [a for a in acts if a['status'] != 'planned']
    planned = [a for a in acts if a['status'] == 'planned']
    if acts != frozen + planned:
        raise ValueError('completed/in_progress activities must form a continuous prefix')
    active = [a for a in frozen if a['status'] == 'in_progress']
    if len(active) > 1 or (active and frozen[-1]['id'] != active[0]['id']):
        raise ValueError('at most one in_progress activity, last in frozen prefix')
    for a in frozen:
        if a['status'] == 'completed' and engine.moment(a['end']) > now:
            raise ValueError('completed activity ends in the future; verify actual state')
        if a['status'] == 'in_progress':
            if engine.moment(a['start']) > now or ready < engine.moment(a['end']):
                raise ValueError('in_progress timing conflicts with as_of/ready_at')
    warnings = []
    if event['status'] == 'unknown':
        warnings.append('event_not_confirmed')
    if event['kind'] in ('weather', 'place_unavailable') and not blocked and not windows:
        warnings.append('event_needs_structured_restrictions')
    if frozen and frozen[-1]['place_id'] != state['anchor_place_id']:
        warnings.append('anchor_differs_from_last_frozen_place_update_actual_progress_first')
    output = dict(status='ready', mode='prepare', original_version=payload['original_version'],
                  event_id=event['id'], frozen_activity_ids=[a['id'] for a in frozen],
                  adjustable_activity_ids=[a['id'] for a in planned],
                  stale_activity_ids=[a['id'] for a in planned if engine.moment(a['start']) < ready],
                  applied_requirement_updates=applied, pending_requirement_updates=pending,
                  missing_data=warnings, guard_issues=[], validation=None, candidate=None,
                  requires_confirmation=bool(pending), sources=baseline['sources'],
                  baseline_for_planning=baseline)
    if not planned and not active:
        output.update(status='finished', mode='prepare')
        return output
    candidate = payload.get('candidate')
    if candidate is None:
        output['status'] = 'partial' if warnings else 'needs_confirmation' if pending else 'ready'
        return output
    candidate = copy.deepcopy(candidate)
    # Context evidence may be used by the candidate; never silently replace an existing source.
    candidate_sources = {s['id']: s for s in candidate['sources']}
    for source in baseline['sources']:
        if source['id'] in candidate_sources and candidate_sources[source['id']] != source:
            raise ValueError('candidate rewrote an existing source')
        candidate_sources[source['id']] = source
    candidate['sources'] = list(candidate_sources.values())
    report = engine.review({'plan': baseline, 'candidate': candidate})
    recheck = report.get('recheck_result')
    output.update(mode='review', validation=report, candidate=candidate,
                  requires_confirmation=bool(pending) or report.get('requires_confirmation', False))
    if not recheck or recheck['status'] == 'invalid':
        output['status'] = 'invalid'
        return output
    ids.update(candidate_sources)
    output['sources'] = candidate['sources']
    problems = output['guard_issues']
    future = [a for a in candidate['activities'] if a['status'] == 'planned']
    frozen_map = {a['id']: a for a in frozen}
    for a in candidate['activities']:
        if a['status'] != 'planned' and a['id'] not in frozen_map:
            problems.append('candidate_fabricated_progress:' + a['id'])
    old_historical_legs = baseline['legs'][:max(0, len(frozen)-1)]
    if candidate['legs'][:len(old_historical_legs)] != old_historical_legs:
        problems.append('historical_legs_modified')
    for a in future:
        if engine.moment(a['start']) < ready:
            problems.append('future_activity_before_ready:' + a['id'])
        if a['place_id'] in blocked:
            problems.append('blocked_place_retained:' + a['id'])
        for w in windows:
            lo, hi = engine.window(w)
            if a['place_id'] == w['place_id'] and engine.moment(a['start']) < hi and engine.moment(a['end']) > lo:
                problems.append('blocked_time_overlap:' + a['id'])
    if not future:
        # Dropping all optional activities is a choice, never an implicit "trip finished".
        output['requires_confirmation'] = True
    else:
        leg = payload.get('start_leg')
        if leg is None:
            warnings.append('current_anchor_transfer_missing')
        else:
            if leg['from_place_id'] != state['anchor_place_id'] or leg['to_activity_id'] != future[0]['id']:
                raise ValueError('start_leg endpoints must match current anchor and first planned activity')
            engine.text(leg['mode'], 'start_leg mode')
            for key in ('duration_minutes', 'buffer_minutes', 'walking_m'):
                engine.number(leg[key], key, True)
            evidence = leg['evidence']
            if evidence['status'] not in ('verified', 'estimated', 'unknown'):
                raise ValueError('invalid start_leg evidence')
            if evidence['status'] != 'unknown':
                refs(evidence['source_ids'])
            else:
                engine.array(evidence['source_ids'], 'source_ids')
                if any(not isinstance(v, str) or v not in ids for v in evidence['source_ids']):
                    raise ValueError('unknown start_leg evidence contains an unresolved source')
                warnings.append('current_anchor_transfer_unverified')
            duration, buffer = leg['duration_minutes'], leg['buffer_minutes']
            gap = (engine.moment(future[0]['start'])-ready).total_seconds()/60
            if duration is None or buffer is None:
                warnings.append('current_anchor_transfer_time_unknown')
            elif gap < duration + buffer:
                problems.append('insufficient_time_from_current_anchor')
            modes = baseline['requirements']['allowed_transport_modes']
            if modes is not None and leg['mode'] not in modes:
                problems.append('current_anchor_transport_not_allowed')
            if frozen:
                boundary = next((l for l in candidate['legs'] if l['from_id'] == frozen[-1]['id'] and l['to_id'] == future[0]['id']), None)
                if boundary is None or any(boundary[k] != leg[k] for k in ('duration_minutes','buffer_minutes','walking_m','mode')):
                    problems.append('boundary_leg_must_match_current_anchor_transfer')
            else:
                # This transfer has no activity pair and is not counted by the shared engine.
                limit = baseline['requirements']['daily_walking_limit_m']
                if limit is not None:
                    key = ready.date().isoformat()
                    values = [a['walking_m'] for a in candidate['activities'] if a['day'] == key]
                    values += [l['walking_m'] for l in candidate['legs'] if l['day'] == key]
                    values.append(leg['walking_m'])
                    if sum(v for v in values if v is not None) > limit:
                        problems.append('walking_limit_including_current_anchor_exceeded')
                    elif None in values:
                        warnings.append('walking_including_current_anchor_unknown')
            day_window = baseline['requirements']['daily_windows'].get(ready.date().isoformat())
            if day_window:
                lo, hi = engine.window(day_window)
                if ready < lo or ready > hi:
                    problems.append('current_departure_outside_daily_window')
            output['start_leg_assumption'] = evidence['status'] == 'estimated'
    if problems or recheck['status'] == 'fail':
        output['status'] = 'blocked'
    elif warnings or recheck['status'] == 'incomplete':
        output['status'] = 'partial'
    elif output['requires_confirmation']:
        output['status'] = 'needs_confirmation'
    else:
        output['status'] = 'ready'
    return output


def main():
    try:
        if len(sys.argv) > 2:
            raise ValueError('usage: replan_guard.py [input.json]')
        raw = Path(sys.argv[1]).read_text(encoding='utf-8-sig') if len(sys.argv) == 2 else sys.stdin.read()
        result = run(json.loads(raw))
    except (OSError, ValueError) as exc:
        result = {'status': 'invalid', 'errors': [str(exc)], 'candidate': None}
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 2 if result['status'] == 'invalid' else 0


if __name__ == '__main__':
    sys.exit(main())

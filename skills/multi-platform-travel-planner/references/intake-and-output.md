# Intake and Output Reference

Use this reference for incomplete prompts, complex constraints, follow-up changes, and file-ready travel reports.

## Intake fields

| Field | Required | Default when omitted |
|---|---|---|
| Destination | Yes | Ask if absent |
| Duration | Yes | Ask if absent |
| Total budget | Yes for budget planning | If absent, provide a tiered estimate and label it |
| Party size | No | 1 traveler |
| Intercity transport included | No | Show excluded total and a separate placeholder/estimate |
| Dates or season | No | Recommend the best period and warn that prices are date-sensitive |
| Arrival/departure times | No | Assume arrival 09:00 and departure 18:00 |
| Origin city | No | Needed only for intercity fare calculation |
| Interests | No | Balanced food, landmark, culture, and relaxed walking |
| Walking/mobility | No | Moderate walking, no special accessibility needs |
| Local transport | No | Metro/bus/walking first |
| Accommodation | No | Clean budget lodging near a major transit hub |
| Sources/platforms | No | Public web plus official sources; add named platforms |
| Output | No | Concise report in chat |

State every consequential default under “规划假设”. Do not ask a chain of questions when assumptions can produce a useful first draft.

## Planning units

Each itinerary row should include:

- Time block, allowing buffers.
- Origin → destination sequence.
- Recommended transport and approximate duration.
- Activity and why it fits.
- Nearby dish or food district.
- Estimated cost per person and for the group when applicable.
- Reservation, closure, weather, or accessibility note.

## Output templates

### Fast answer

Use for simple requests:

1. Feasibility and assumptions.
2. Day-by-day route.
3. Budget summary.
4. Best time and two cautions.
5. Sources.

### Comparison report

Use when the user asks to compare Douyin, Xiaohongshu, and browser results:

1. Research scope and access status per platform.
2. Repeated recommendations across sources.
3. Platform-specific emphasis.
4. Official verification and conflicts.
5. Final retained/removed candidates with reasons.
6. Optimized itinerary and budget.

### File-ready report

Use descriptive headings, repeated table headers, currency units, page-friendly tables, and a final “价格与开放信息核验日期” note. Put citations or source links near the relevant sections. Do not let decorative layout hide assumptions or estimates.

## Follow-up modifications

Apply changes as a minimal diff:

| User change | Recalculate |
|---|---|
| Lower budget | Tickets, lodging, meals, transit, contingency |
| Arrival/departure change | First/last day, transfers, meals, total cost |
| Elderly/children | Walking, stairs, rest, queues, taxis, closing time |
| Rain | Outdoor stops, indoor substitutes, transit buffers |
| Food-heavy | Meal timing, markets/food districts, reduce duplicate attractions |
| Add remote attraction | Travel time, early start, last transport, opportunity cost |

End with a short “本次调整” summary rather than rewriting explanations that did not change.


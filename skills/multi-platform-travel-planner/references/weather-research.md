# Multi-Source Travel Weather Research

Read this reference when weather affects a travel plan, the trip is within 10 days, or the user asks which hours are suitable for an outdoor activity.

The goal is an actionable traveler decision, not a generic weather summary. Answer questions such as “when can I walk without rain?”, “which hours have strong sun?”, “should I move this attraction indoors?”, and “when should I recheck?”.

## 1. Resolve the forecast location

Map every weather-sensitive stop to its district, county, or prefecture-level city. Query the actual itinerary areas rather than applying one city-center forecast to remote mountains, islands, coastlines, or counties.

Use location evidence in this order:

1. A destination or area explicitly named by the user.
2. The district/county containing a named attraction.
3. A browser or device location the user has authorized and that is demonstrably local.
4. A city supplied by the user after automatic location fails.

Do not treat an IP-derived location as authoritative. Reject it when it conflicts with the user's country, timezone, itinerary, or shows a proxy/cloud data-center location. Never expose IP addresses or precise coordinates in the answer.

## 2. Use complementary source types

Obtain as many of the following as are available and useful:

| Source type | Main role | Required checks |
|---|---|---|
| Official observation | Current temperature, precipitation, wind, humidity, visibility | Observation time and station/area |
| Official radar | Rain location, intensity, movement, and short-term approach | Latest frame and recent sequence |
| Satellite/cloud imagery | Broad cloud systems, clear zones, and developing weather | Product time and image type |
| Official warning service | Rainstorm, thunderstorm, wind, heat, typhoon, snow, fog | Issuer, affected area, issue/expiry time |
| Official hourly forecast | Next 3–24 hours of precipitation, temperature, wind, humidity | Publication time and interval |
| Official daily forecast | Next 2–7 days and broad trend | Publication time and uncertainty |
| Local meteorological service/app | Finer district, county, traffic, scenic-area, or nowcast detail | Authority and update time |
| Secondary weather provider | Cross-check, feels-like temperature, UV, air quality, missing hours | Never override newer official warnings |

Use social posts only as reports of conditions at a place and time. Do not use them as the sole weather forecast.

If a structured weather tool fails twice or cannot resolve Chinese districts/counties, stop retrying the same request. Switch to official public pages, local services, browser-visible radar, or a secondary provider.

## 3. Match data horizon to the decision

| Horizon | Primary evidence | Appropriate claim |
|---|---|---|
| Now to 2 hours | Current observation, warning, recent radar frames | Immediate rain approach or short outdoor window |
| 3 to 24 hours | Hourly forecast plus radar/nowcast near departure | Best time blocks, heat, rain, wind, sunset |
| 2 to 7 days | Daily forecast and warnings; hourly detail when available | Day selection and broad backup plan |
| 8 to 15 days | Trend products from authoritative providers | Directional planning only; lower confidence |
| Beyond 15 days | Climate normals and seasonal hazards | Best season, not a day-specific forecast |

Do not present a long-range climate estimate as a precise forecast.

## 4. Interpret radar and cloud products carefully

Check the newest product time before interpreting an image. Compare several recent frames when animation or timestamps are available; a single frame shows location but not reliable motion.

Record:

- Whether precipitation echoes cover the destination.
- Whether nearby echoes appear to approach, weaken, strengthen, or move away.
- Approximate distance/direction only when the map supports it.
- Whether the latest image is fresh enough for a near-term decision.
- Any gaps, blocked sectors, stale products, or unreadable legends.

Do not infer “no rain all evening” from one clear radar frame. Combine it with the hourly forecast and warnings. Discard an image whose timestamp belongs to a previous day or clearly predates the decision window.

## 5. Identify useful outdoor windows

Divide the relevant day into decision blocks, normally 1–3 hours. For each block, capture:

- Forecast condition and precipitation amount/probability when available.
- Temperature and feels-like temperature.
- Humidity, wind speed/gusts, visibility, and air quality when relevant.
- Sunrise/sunset and UV or strong-sun exposure.
- Warning overlap.
- Recommendation: preferred, usable with precautions, or avoid.

A “rain-free window” means the available hourly forecast has no meaningful precipitation signal and current radar/warnings do not contradict it. State it as a confidence-based judgment, never a guarantee.

Use these confidence labels:

- **High:** recent official radar/observation and hourly forecast agree; no relevant warning.
- **Medium:** hourly sources agree but radar, observation, or warning coverage is missing/stale.
- **Low:** sources conflict, the period is too far away, or only a single secondary source is available.

For heat/sun, consider temperature, feels-like temperature, humidity, UV, cloud cover, shade, and solar time. Do not equate “cloudy” with “no UV”. For wind, distinguish average wind from gusts and pay special attention to coasts, mountains, bridges, ferries, cableways, and exposed viewpoints.

## 6. Resolve conflicts

When sources disagree:

1. Compare publication and observation times.
2. Prefer current official warnings and observations for immediate safety.
3. Prefer a newer official hourly forecast over an older daily summary.
4. Use a secondary provider to expose uncertainty, not to hide it.
5. State the range or disagreement and lower confidence.
6. Plan against the more disruptive plausible condition when safety or a remote route is involved.

Never mix values from different dates or locations into one hourly table.

## 7. Produce a traveler weather brief

For a named outdoor activity, output:

1. **Decision first:** go, go with precautions, delay, switch indoors, or recheck later.
2. **Data timestamp and scope:** local time, district/county, source update times.
3. **Next few hours:** a table of time, rain signal, temperature/feels-like, wind, sun/UV, and action.
4. **Best outdoor window:** start/end, confidence, and why.
5. **Avoid window:** rain, heat, lightning, wind, fog, snow, poor air, or darkness reason.
6. **Radar/cloud interpretation:** only what the current products support.
7. **Next 3–7 days:** daily trend and which day is best for outdoor activities.
8. **Packing/route changes:** rain gear, sun protection, layers, hydration, transport buffer, indoor substitute.
9. **Recheck instruction:** normally 30–60 minutes before departure for convective rain, and immediately when a warning is issued.
10. **Sources:** cite volatile facts close to the relevant claim.

When exact hourly observations are unavailable, use bounded ranges or clearly labeled interpolation. Never invent precipitation probabilities, radar motion, UV values, or precise microclimate differences.

## 8. Update the itinerary

Convert the weather brief into a minimal itinerary adjustment:

- Move outdoor landmarks into the best weather window.
- Put museums, markets, malls, covered streets, or cafés in rain/heat periods.
- Avoid remote mountains, water activities, ferries, or exposed viewpoints under relevant warnings.
- Preserve geographic clustering; do not create long cross-city transfers merely to chase a small forecast difference.
- Give a nearby fallback for every weather-sensitive block.

Weather data changes quickly. Include the verification time and do not reuse a previous trip's forecast without refreshing it.


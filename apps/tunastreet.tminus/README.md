# tunastreet.tminus — T-MINUS (#184)

ESP-Brookesia v0.8 JavaScript runtime app. 368×448 true-black launch clock.

## Backend (`http://192.168.1.121:8092`)

| Endpoint | Shape |
|---|---|
| `GET /tminus/now` | `{id, vehicle, mission, pad, t0_unix, server_unix, status, idx, count}` |
| `POST /tminus/step` | body `{"dir": 1\|-1}` → same shape |
| `GET /health` | `{ok, app:"tminus"}` |

T-0 is Launch Library 2.

## Gestures

- Tap the clock or `»` = next launch. `«` = previous.
- Swipe left/right = same if JSON-UI gesture fires (taps are the guaranteed path).
- Swipe up/down is never intercepted.

## Sandbox

Same as `tunastreet.xviewer`: QuickJS global script, no fetch/setTimeout.
`Http` RequestAsync + events, `SystemGui`, `SystemTimer`. Clock ticks from
`server_unix` + a 1 s timer so a broken `Date` on device still counts.

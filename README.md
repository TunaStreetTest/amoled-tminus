# amoled-tminus

**T-MINUS** — launch clock for the Waveshare ESP32-S3 Touch AMOLED 1.8″ V2.

Issue [#184](https://github.com/cldr-steven-matison/DesktopShare/issues/184).
Plan: [amoled-tminus-plan.md](https://github.com/cldr-steven-matison/DesktopShare/blob/issue-184-tminus/amoled-tminus-plan.md).

Not the X viewer. Not Ember. T-0 is Launch Library 2.

```
tap the clock / »     → next upcoming launch
«                     → previous
swipe L / R           → same if the gesture fires (taps always work)
swipe up (bottom)     → Brookesia home (never intercepted)
```

| Path | What |
|---|---|
| `apps/tunastreet.tminus/` | Brookesia v0.8 runtime JS package — this is the app |
| `backend/` | FastAPI, Launch Library 2, `0.0.0.0:8092` |

```bash
bash scripts/run.sh
```

Panel contract: `http://192.168.1.121:8092`

- `GET /tminus/now`
- `POST /tminus/step` `{"dir": 1|-1}`
- `GET /health`

No keys. Port 8092 already has the Windows firewall inbound rule.

Stage `apps/tunastreet.tminus/` into the platform littlefs `apps/` tree and keep
`tunastreet.xviewer`. Flash is `littlefs_data` only @ `0xaa1000`. Ask before
every flash.

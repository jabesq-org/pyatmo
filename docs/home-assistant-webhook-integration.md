# Consuming pyatmo webhook processing from Home Assistant

Implementation guide for wiring `pyatmo`'s webhook support into the Home Assistant Netatmo
integration.

Both halves of this document are **verified against source**: the pyatmo contract was measured
against the implementation, and the Home Assistant details were read from
`homeassistant/components/netatmo/` (HA `b955e776e78`, which pins `pyatmo==9.5.0`).

---

## 0. What the integration does today

Worth establishing first, because it is not what the pyatmo-side design assumes.

**The integration does not touch pyatmo model objects from webhooks.** `async_handle_webhook`
(`webhook.py:50`) decodes the payload and fans it out over dispatcher signals
`signal-netatmo-webhook-{event_type}`. Each platform then parses the **raw payload** and writes HA
entity attributes directly:

- `climate.py:247 handle_event` — reads `data["home"]["rooms"][…]["therm_setpoint_mode"]` and sets
  `_attr_hvac_mode`, `_attr_preset_mode`, `_attr_target_temperature`, then `async_write_ha_state()`
- `light.py:106 handle_event` — sets `_attr_is_on` from `data["sub_type"]`
- `camera.py:142 handle_event` — same shape for monitoring/streaming state

Polling is separate: `NetatmoDataHandler.async_fetch_data` (`coordinator.py:249`) calls the
`AsyncAccount.async_update_*` method for a publisher, which mutates the pyatmo model, then
`_notify_subscribers` invokes each entity's `async_update_callback()`, which **re-derives `_attr_*`
from the pyatmo object** (`entity.py` — entities hold `self.device`, typed `Room`/`Module`).

Two consequences:

1. **`NetatmoDataHandler` is not a `DataUpdateCoordinator`.** It is a bespoke class built on
   `async_track_time_interval` plus a `deque` queue of `NetatmoPublisher` entries. There is no
   `coordinator.data`, no `async_set_updated_data`, and no `async_request_refresh`.
2. **A lost-update race already exists, independent of pyatmo.** A poll that fetched *before* a
   webhook arrived but completes *after* it calls `_notify_subscribers`, which re-derives `_attr_*`
   from a pyatmo model that never saw the webhook — reverting the optimistic value.

Adopting `process_webhook` **narrows** that existing race rather than introducing one: the merge lands
in the pyatmo model, so re-derivation reproduces the webhook state instead of discarding it. The
remaining window is only until the next *fetch*, not the next *notify*.

---

## 1. API surface

```python
from pyatmo import LifecycleStatus, WebhookEvent, WebhookKind, WebhookResult

result: WebhookResult = await data_handler.account.process_webhook(payload)
```

Requires a `pyatmo` bump — the manifest currently pins `9.5.0`.

### `WebhookResult`

| Field | Type | Meaning |
|---|---|---|
| `home_id` | `str \| None` | Resolved from top-level `home_id` or nested `home.id` |
| `event_type` | `str \| None` | `None` if absent or wrongly typed |
| `push_type` | `str \| None` | |
| `kind` | `WebhookKind` | Routing category |
| `touched_ids` | `list[str]` | Ids the merge actually wrote (empty if nothing changed) |
| `events` | `list[WebhookEvent]` | Only for `kind is EVENT`; currently 0 or 1 entry |
| `needs_refresh` | `bool` | pyatmo could not merge — refetch to learn the new state |
| `lifecycle` | `LifecycleStatus \| None` | Only for `kind is LIFECYCLE` |

### `WebhookKind` → action

Matrix produced by running each payload shape, not read off the code:

| `kind` | Trigger | `needs_refresh` | `events` | Your action |
|---|---|---|---|---|
| `STATE` | `set_point`, `cancel_set_point`, `therm_mode`, `on`, `off`, `light_mode` | `False` | 0 | Model already merged — notify subscribers |
| `EVENT` | 36 types (`person`, `movement`, `smoke`, `siren_sounding`, …) | `False` | 1 | Fire the bus event; no model change |
| `TOPOLOGY_DIRTY` | `schedule` | **`True`** | 0 | `async_force_update(...)` |
| `LIFECYCLE` | `webhook_activation`, `webhook_deactivation`, `*-connection` | see below | 0 | Track webhook state; force update on reconnect |
| `UNKNOWN` | anything unrecognised or malformed | `False` | 0 | Debug-log and drop |

| `push_type` | `lifecycle` | `needs_refresh` |
|---|---|---|
| `webhook_activation` | `ACTIVATION` | `False` |
| `webhook_deactivation` | `DEACTIVATION` | `False` |
| `NACamera-connection`, `NOC-connection`, `NDB-connection` | `CONNECTION` | **`True`** |

This maps **1:1 onto `NetatmoDataHandler.handle_event`** (`coordinator.py:235`), which already sets
`self._webhook = True/False` on activation/deactivation and calls `async_force_update(ACCOUNT)` for
`CAMERA_CONNECTION_WEBHOOKS`. `needs_refresh` is exactly that existing decision, expressed as data.

### `WebhookEvent`

`event_type`, `push_type`, `home_id`, `module_id`, `camera_id`, `device_id`, `person_ids`, `sub_type`,
`snapshot_url`, `message`, `raw`.

Every scalar is `str | None` and guaranteed to be a string or `None` — a wrongly-typed value from
Netatmo is coerced to `None` rather than passed through. `person_ids` contains only strings. `raw` is
the original payload dict **by reference**, as an escape hatch for unmodelled fields.

`WebhookEvent` and `WebhookResult` are `frozen=True` but **not hashable** (`person_ids`, `raw`,
`touched_ids`, `events` are mutable, so `hash()` raises `TypeError`). Compare by value; never use them
as dict keys or set members.

---

## 2. The hard constraint: answer Netatmo immediately

Netatmo deactivates an endpoint that does not respond promptly.

The current handler already respects this — dispatcher sends are synchronous callbacks and it awaits
no network I/O. **Keep it that way.** `process_webhook` is safe here: it performs no I/O and never
suspends, enforced upstream by `test_process_webhook_never_suspends`, so it cannot silently regress.

Do **not**, before returning:

- `await data_handler.async_fetch_data(...)` or any `account.async_update_*` call. `pyatmo.auth`
  retries HTTP 429 with backoff capped at 60 s; one rate-limited fetch can stall past Netatmo's
  tolerance and cost the webhook.
- Acquire a lock that a poll can hold across an HTTP request, for the same reason.

`async_force_update` is safe: it is a `@callback` that only sets `next_scan = time()` and rotates the
queue (`coordinator.py:229`). It does not perform I/O.

---

## 3. Suggested handler shape

```python
from pyatmo import LifecycleStatus, WebhookKind

from .coordinator import ACCOUNT, HOME


async def async_handle_webhook(
    hass: HomeAssistant, webhook_id: str, request: Request
) -> None:
    """Handle webhook callback. Must return promptly."""
    try:
        data = await request.json()
    except ValueError as err:
        _LOGGER.error("Error in data: %s", err)
        return

    entry = next(
        (
            entry
            for entry in hass.config_entries.async_loaded_entries(DOMAIN)
            if entry.data.get(CONF_WEBHOOK_ID) == webhook_id
        ),
        None,
    )
    if entry is None:
        return
    data_handler = entry.runtime_data

    # No I/O, never suspends: safe on the response path.
    result = await data_handler.account.process_webhook(data)

    if result.kind is WebhookKind.LIFECYCLE:
        data_handler.set_webhook_state(result.lifecycle)      # new helper

    if result.kind is WebhookKind.EVENT:
        for event in result.events:
            async_send_event(data_handler, event, data)

    if result.needs_refresh:
        data_handler.async_force_update(ACCOUNT)
    elif result.touched_ids and result.home_id:
        # pyatmo merged into the model; make entities re-derive from it.
        data_handler.notify_home_subscribers(result.home_id)  # new helper
```

Two small helpers on `NetatmoDataHandler`:

```python
    @callback
    def set_webhook_state(self, lifecycle: LifecycleStatus | None) -> None:
        """Track webhook availability from a LIFECYCLE result."""
        if lifecycle is LifecycleStatus.ACTIVATION:
            self._webhook = True
        elif lifecycle is LifecycleStatus.DEACTIVATION:
            self._webhook = False
        elif lifecycle is LifecycleStatus.CONNECTION:
            self.async_force_update(ACCOUNT)

    @callback
    def notify_home_subscribers(self, home_id: str) -> None:
        """Re-render entities for a home after an in-model merge."""
        signal_name = f"{HOME}-{home_id}"
        if signal_name in self.publisher:
            self._notify_subscribers(signal_name)
```

`f"{HOME}-{home_id}"` is the signal name convention entities already use — see
`climate.py:206`, `self._signal_name = f"{HOME}-{self.home.entity_id}"`.

---

## 4. What this replaces

The per-platform `handle_event` methods currently re-parse the raw payload to compute entity state.
With `process_webhook`, the model is already correct, so those methods collapse into the existing
`async_update_callback()` path.

| Today | With `process_webhook` |
|---|---|
| `climate.py:247-330` parses `home.rooms[].therm_setpoint_*` and sets three `_attr_*` fields | pyatmo merges the setpoint fields; `async_update_callback()` re-derives them |
| `light.py:106` sets `_attr_is_on` from `data["sub_type"]` | pyatmo sets `module.floodlight`; re-derive |
| `camera.py:142` sets monitoring/streaming state | pyatmo sets `module.monitoring`; re-derive |

Migrate one platform at a time — nothing forces a single cut-over, since dispatcher signals and
`process_webhook` can coexist during the transition.

**Keep the `schedule` handling in `climate.py:254-275` as it is.** It reads
`data_handler.schedules[...]`, which is integration state pyatmo knows nothing about. pyatmo only
reports `TOPOLOGY_DIRTY` / `needs_refresh` for that event.

**Keep the bus event.** `NETATMO_EVENT` with `{"type", "data", ATTR_DEVICE_ID}` is public API for user
automations and `device_trigger.py`. Source its fields from `WebhookEvent` if convenient, but keep
`"data"` as the raw payload — `event.raw` is exactly that dict, so nothing changes for consumers.

---

## 5. The residual staleness window

For `kind is STATE`, pyatmo merges rather than refetching — deliberate, given how hard the integration
already works to stay under the rate limit (`_rate_limit`, `poll_count`, `next_scan += 60` in
`coordinator.py:222`).

A poll that fetched **before** the webhook and completes after it will still overwrite the merge, then
`_notify_subscribers` re-renders the older values. Reproduced upstream: a room at
`therm_setpoint_mode == "away"` / `12` merges to `"manual"` / `25`, then a poll suspended mid-flight
completes and reverts it.

Self-healing — Netatmo is authoritative and already applied the change, so the next poll shows the
truth. Symptom is a setpoint that flicks back for up to one `HOME` interval (300 s ÷ interval factor).

Does **not** help:

- `async_set_updated_data` — **does not exist here**; `NetatmoDataHandler` is not a
  `DataUpdateCoordinator`. Even in an integration that had it, it cannot cancel a fetch already in
  flight, and these entities read pyatmo objects rather than `coordinator.data`.
- A lock inside pyatmo — it would have to wrap the fetch, putting the 429 backoff on the response
  path (§2).

**Does** help, and only you can do it since you own the handler: keep the response immediate, but
order the *merge* after any in-flight fetch. An `asyncio.Lock` held by both `async_fetch_data` and a
post-response merge task achieves it; because the lock is taken after the handler has returned,
blocking on it is harmless.

Given the failure is self-healing and the window already exists today, accepting it is defensible.
Adopting `process_webhook` makes it strictly better than the status quo either way.

---

## 6. Mapping `touched_ids`

`touched_ids` holds only ids pyatmo actually wrote — empty when the payload resolved to no known
entity, or when every value was rejected. The **namespace depends on `event_type`**:

| `event_type` | ids are |
|---|---|
| `set_point`, `cancel_set_point` | room ids |
| `therm_mode` | the home id |
| `on`, `off`, `light_mode` | module ids |
| any `EVENT` kind | module / camera / device ids |

For this integration the simplest use is the one in §3 — ignore the individual ids and notify the
`f"{HOME}-{home_id}"` publisher, since `async_update_callback()` is cheap and already re-derives
everything from the model. Per-id targeting is only worth it if that proves too coarse.

Ids do not collide across namespaces (44 room, 194 module, 7 home ids across pyatmo's fixtures, zero
overlap), but branch on `event_type` rather than guessing from an id's shape — some module ids are
numeric, not MAC-formatted.

An empty `touched_ids` with `kind is STATE` is normal, not an error.

---

## 7. Cleanups this enables

- **`SUBEVENT_TYPE_MAP` is dead code.** `webhook.py:44` maps `"outdoor"` and `"therm_mode"` to `""`,
  so `data.get(SUBEVENT_TYPE_MAP[event_type], [])` is always `data.get("", [])` → `[]`, and the
  sub-event loop at `webhook.py:79` never executes. Confirmed by evaluating it. Presumably the value
  was once a real key. Delete it or restore the intended key.
- **Duplicated constants.** `CAMERA_CONNECTION_WEBHOOKS` (`const.py:214`) and the `EVENT_TYPE_*` /
  `WEBHOOK_*` families now exist upstream. Importing from pyatmo removes the risk of the two lists
  drifting when Netatmo adds a push type.
- **Classification logic.** pyatmo's `classify()` covers 6 STATE types, 36 EVENT types, `schedule`,
  and the three `*-connection` push types, so the per-platform `push_type`/`event_type` matching can
  be replaced by a `kind` check.

## 8. Gotchas

- **`camera_id` vs `device_id`.** pyatmo resolves a camera as `camera_id or device_id`. Real payloads
  have them equal; do not rely on both being present. Note `camera.py:152` already returns early when
  `camera_id` is missing — pyatmo behaves the same way, yielding empty `touched_ids`.
- **`connection` is LIFECYCLE, `disconnection` is EVENT.** A reconnect sets `needs_refresh=True`
  because state may have changed while the camera was away; a disconnection is a plain event. The
  asymmetry is intentional and matches what `handle_event` does today.
- **`UNKNOWN` is not a failure.** Netatmo adds push types; unrecognised ones surface as `UNKNOWN` so
  the integration keeps working. Debug-log, do not warn per push.
- **Malformed input never raises.** A wrongly-typed scalar is treated as absent and logged at pyatmo's
  DEBUG level. If a payload seems ignored, enable `pyatmo` debug logging and look for
  `Discarding non-string value` / `Discarding non-numeric value`.
- **`raw` is shared.** `event.raw` is the same dict you passed in. Do not mutate it if you keep the
  event.
- **`async_force_update` needs a registered publisher.** It indexes `self.publisher[signal_name]` and
  will `KeyError` if nothing has subscribed to that signal yet. Guard as
  `notify_home_subscribers` does above.

## 9. Homes that cannot be polled

`/homesdata` lists homes that `/homestatus` refuses, in two different ways. Measured
against a live account on 2026-08-13, three of six homes could not be polled: one
returned `{"error":{"code":21,"message":"Invalid home_id"}}`, and two answered `200`
with no `body` at all. Both are reproducible on every poll.

Two ways to avoid spending calls on one:

- `Home.has_status` is `False` when a home carries no modules, which is what the
  unpollable homes have in common. Check it before scheduling a poll. Device
  category plays no part: `/homestatus` does report weather modules, so excluding
  them would hide a home that polls fine.
- `InvalidHomeError` is raised when the API rejects a home id. It is deterministic
  -- the same id fails every time -- so stop polling that home rather than retrying
  it. It subclasses `ApiError`, so existing handlers still catch it.

`NoDeviceError`, raised for the empty-body case, is deliberately **not** a signal to
stop. It also covers an empty `homes` list and empty weather or air-care data, where
one odd response must not disable a working publisher.

The library deliberately does not skip the call itself. It has no scheduler, and a
silent no-op would hide the situation from every caller.

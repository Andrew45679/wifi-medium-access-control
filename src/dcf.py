# Handles DCF backoff, channel sensing, and transmission results.
import heapq


ARRIVAL_PRIORITY = 2
BACKOFF_PRIORITY = 3
TRANSMISSION_START_PRIORITY = 4


# Add an event in time and priority order.
def schedule_event(sched, slot, priority, station_id, event):
    heapq.heappush(sched, (slot, priority, station_id, event))


# Choose a random backoff or a fixed test value.
def draw_backoff(station, rng, backoffs):
    if backoffs is None:
        station.backoff = int(rng.integers(0, station.cw))
    elif isinstance(backoffs, dict):
        station.backoff = int(backoffs.get(station.id, 0))
    else:
        station.backoff = int(backoffs)


# Schedule expiry after DIFS and backoff.
def schedule_countdown(station, slot, cfg, sched):
    station.countdown_start = slot
    station.countdown_expire = slot + cfg.difs_slots + station.backoff
    station.countdown_active = True
    schedule_event(sched, station.countdown_expire, BACKOFF_PRIORITY, station.id, "backoff_expire",)


# Start backoff when the station can contend.
def start_countdown(station, slot, cfg, rng, backoffs, channel, sched):
    # Skip stations without a queued frame or with work in progress.
    if (not station.queue or station.countdown_active or station.transmitting 
        or station.awaiting_ack or station.backoff_pending):
        return

    draw_backoff(station, rng, backoffs)
    station.backoff_pending = True
    if not channel.is_busy(station.id, slot):
        schedule_countdown(station, slot, cfg, sched)


# Resume pending backoff when the channel is idle.
def on_idle(station, slot, cfg, sched):
    if (station.queue and station.backoff_pending and not station.countdown_active
        and not station.transmitting and not station.awaiting_ack):
        schedule_countdown(station, slot, cfg, sched)


# Ignore expired countdown events.
def on_backoff_expire(station, slot):
    if not station.countdown_active or station.countdown_expire != slot:
        return False

    station.countdown_active = False
    station.countdown_expire = None
    station.backoff = 0
    station.backoff_pending = False
    return True


# Update station state after success or collision.
def on_result(station, slot, success, cfg, rng, backoffs, channel, sched):
    station.transmitting = False
    station.awaiting_ack = False

    if success:
        # Success removes the frame and resets CW.
        arrival = station.queue.popleft()
        station.delays.append(slot - arrival)
        station.successes += 1
        station.cw = cfg.cw0
        station.collisions = 0
    else:
        # Collision keeps the frame queued and grows CW.
        station.collisions += 1
        station.cw = min(station.cw * 2, cfg.cwmax)

    station.backoff_pending = False
    if station.queue:
        start_countdown(station, slot, cfg, rng, backoffs, channel, sched)


# Freeze backoff and save the remaining slots.
def on_busy(station, slot, cfg):
    if not station.countdown_active:
        return

    # Count only backoff slots after DIFS.
    backoff_start = station.countdown_start + cfg.difs_slots
    elapsed_backoff = max(0, slot - backoff_start)
    station.backoff = max(0, station.backoff - elapsed_backoff)
    station.countdown_active = False
    station.countdown_expire = None

# Runs the slotted-time simulation and processes its events.
import heapq
import math

import numpy as np

from src.dcf import (
    ARRIVAL_PRIORITY,
    BACKOFF_PRIORITY,
    TRANSMISSION_START_PRIORITY,
    on_backoff_expire,
    on_busy,
    on_idle,
    on_result,
    schedule_event,
    start_countdown,
)
from src.station import Station


# Generate arrivals and run the event queue.
def run(cfg, n, rate, seed, channel, arrivals=None, backoffs=None, rts_cts=False):
    # Validate inputs.
    if n < 0:
        raise ValueError("n must be non-negative")
    if cfg.slot_us <= 0:
        raise ValueError("slot_us must be positive")
    if rate < 0:
        raise ValueError("Arrival rate must be non-negative")

    # Use the seed for repeatable random choices.
    rng = np.random.default_rng(seed)
    stations = [Station(station_id=i, cw0=cfg.cw0) for i in range(n)]
    sched = []
    duration_slots = math.floor(cfg.sim_time_s / (cfg.slot_us / 1e6))

    if arrivals is None:
        # Generate independent Poisson arrivals for each station.
        slot_seconds = cfg.slot_us / 1e6
        arrivals = []
        if rate > 0:
            # Draw exponential gaps between arrivals.
            for station_id in range(n):
                arrival_time = 0.0
                while True:
                    arrival_time += rng.exponential(1 / rate)
                    arrival_slot = math.ceil(arrival_time / slot_seconds)
                    # Stop after the simulation duration.
                    if arrival_slot > duration_slots:
                        break
                    arrivals.append((station_id, arrival_slot))

    # Validate and schedule arrivals.
    for station_id, arrival_slot in arrivals:
        if not 0 <= station_id < n:
            raise ValueError(f"Invalid station id in arrivals: {station_id}")
        if arrival_slot < 0:
            raise ValueError("Arrival slots must be non-negative")
        schedule_event(sched, arrival_slot, ARRIVAL_PRIORITY, station_id, "arrival",)

    while sched:
        # Process the earliest event first.
        slot, _, station_id, event = heapq.heappop(sched)
        # Stop at the configured duration.
        if slot > duration_slots:
            break

        station = stations[station_id]

        if event == "arrival":
            # Queue the frame and start contention.
            station.queue.append(slot)
            start_countdown(station, slot, cfg, rng, backoffs, channel, sched)

        elif event == "backoff_expire":
            # Start transmission after a valid backoff expiry.
            if rts_cts:
                # Handle the case when RTS/CTS is used.
                if not on_backoff_expire(station, slot):
                    continue
                schedule_event(sched, slot, TRANSMISSION_START_PRIORITY, station_id, "rts_start")
            else:
                # Handle the case when RTS/CTS is not used.
                if not on_backoff_expire(station, slot):
                    continue
                schedule_event(sched, slot, TRANSMISSION_START_PRIORITY, station_id, "transmission_start",)

        elif event == "transmission_start":        
            # Start transmission and notify stations if the channel was idle.
            was_busy = channel.is_physically_busy(slot)
            station.transmitting = True
            station.attempts += 1
            end_slot = channel.transmit(station_id, slot)
            if not was_busy:
                # Freeze other countdowns while the channel is busy.
                for waiting_station in stations:
                    on_busy(waiting_station, slot, cfg)
            schedule_event(sched, end_slot, 0, station_id, "transmission_end",)

        elif event == "transmission_end":
            success = channel.end_transmission(station_id)
            if success:
                # Schedule the ACK after SIFS.
                station.awaiting_ack = True
                ack_slot = slot + cfg.sifs_slots + cfg.ack_slots
                channel.reserve_control(ack_slot)
                schedule_event(sched, ack_slot, 1, station_id, "ack",)
            else:
                # Collided frames retry without an ACK.
                on_result(station, slot, False, cfg, rng, backoffs, channel, sched)
            if not channel.is_physically_busy(slot):
                # Resume waiting backoffs when the channel is idle.
                for waiting_station in stations:
                    on_idle(waiting_station, slot, cfg, sched)

        elif event == "ack":
            # Record success when the ACK arrives.
            channel.release_control(slot)
            on_result(station, slot, True, cfg, rng, backoffs, channel, sched)
            if not channel.is_physically_busy(slot):
                # Resume waiting backoffs after the ACK.
                for waiting_station in stations:
                    on_idle(waiting_station, slot, cfg, sched)

        elif event == "rts_start":
            # Start RTS transmission and notify stations if the channel was idle.
            was_busy = channel.is_physically_busy(slot)
            station.transmitting = True
            station.attempts += 1
            end_slot = channel.transmit(station_id, slot, duration_slots=cfg.rts_slots)
            if not was_busy:
                # Freeze other countdowns while the channel is busy.
                for waiting_station in stations:
                    on_busy(waiting_station, slot, cfg)
            schedule_event(sched, end_slot, 0, station_id, "rts_end",)

        elif event == "rts_end":
            success = channel.end_transmission(station_id)
            if success:
                # Schedule the CTS after SIFS.
                cts_slot = slot + cfg.sifs_slots + cfg.cts_slots
                whole_slots = cfg.sifs_slots + cfg.cts_slots + cfg.sifs_slots + channel.frame_slots + cfg.sifs_slots + cfg.ack_slots
                end_slot = slot + whole_slots
                channel.reserve_nav(station_id, end_slot)
                channel.reserve_control(end_slot)
                schedule_event(sched, cts_slot, 1, station_id, "cts",)
            else:
                # Collided RTS frames retry without a CTS.
                on_result(station, slot, False, cfg, rng, backoffs, channel, sched)

                if not channel.is_physically_busy(slot):
                    # Resume waiting backoffs when the channel is idle.
                    for waiting_station in stations:
                        on_idle(waiting_station, slot, cfg, sched)

        elif event == "cts":
            # Record the CTS and schedule the data transmission after SIFS.
            data_slot = slot + cfg.sifs_slots
            channel.reserve_control(data_slot)
            schedule_event(sched, data_slot, 1, station_id, "data_start",)

        elif event == "data_start":
            was_busy = channel.is_physically_busy(slot)
            station.transmitting = True
            end_slot = channel.transmit(station_id, slot)
            schedule_event(sched, end_slot, 0, station_id, "transmission_end",)


    return stations

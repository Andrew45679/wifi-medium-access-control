# Deterministic tests for channel behavior and the DCF simulation timeline.
import numpy as np

from src.channel import Channel
from src.config import Config
from src.dcf import (
    BACKOFF_PRIORITY,
    on_busy,
    on_idle,
    on_result,
    start_countdown,
)
from src.simulator import run
from src.station import Station


def test_overlapping_transmissions_both_collide():
    channel = Channel(frame_slots=5)

    channel.transmit(station_id=0, slot=10)
    channel.transmit(station_id=1, slot=12)

    assert channel.end_transmission(0) is False
    assert channel.end_transmission(1) is False


def test_fixed_arrival_and_backoff_complete_successful_transmission():
    stations = run(
        cfg=Config(),
        n=1,
        rate=0,
        seed=1,
        channel=Channel(frame_slots=5),
        arrivals=[(0, 0)],
        backoffs=0,
    )

    station = stations[0]
    assert station.successes == 1
    assert station.collisions == 0
    assert station.attempts == 1
    assert station.delays == [11]


def test_non_overlapping_transmissions_do_not_collide():
    channel = Channel(frame_slots=5)

    channel.transmit(station_id=0, slot=10)
    assert channel.end_transmission(0) is True
    channel.transmit(station_id=1, slot=15)

    assert channel.end_transmission(1) is True


def test_backoff_is_selected_inside_contention_window():
    cfg = Config()
    station = Station(station_id=0, cw0=cfg.cw0)
    station.queue.append(0)
    sched = []

    start_countdown(
        station,
        slot=0,
        cfg=cfg,
        rng=np.random.default_rng(7),
        backoffs=None,
        channel=Channel(),
        sched=sched,
    )

    assert 0 <= station.backoff < cfg.cw0
    assert sched == [
        (
            cfg.difs_slots + station.backoff,
            BACKOFF_PRIORITY,
            station.id,
            "backoff_expire",
        )
    ]


def test_collision_keeps_frame_and_doubles_contention_window():
    cfg = Config()
    station = Station(station_id=0, cw0=cfg.cw0)
    station.queue.append(0)
    station.attempts = 1
    sched = []

    on_result(
        station,
        slot=5,
        success=False,
        cfg=cfg,
        rng=np.random.default_rng(7),
        backoffs=0,
        channel=Channel(),
        sched=sched,
    )

    assert len(station.queue) == 1
    assert station.collisions == 1
    assert station.cw == min(2 * cfg.cw0, cfg.cwmax)
    assert station.attempts == 1
    assert len(sched) == 1


def test_busy_period_preserves_backoff_then_resumes_after_difs():
    cfg = Config()
    station = Station(station_id=0, cw0=cfg.cw0)
    station.queue.append(0)
    station.backoff = 5
    station.backoff_pending = True
    station.countdown_active = True
    station.countdown_start = 0
    station.countdown_expire = cfg.difs_slots + station.backoff

    on_busy(station, slot=6, cfg=cfg)
    assert station.backoff == 2

    sched = []
    on_idle(station, slot=12, cfg=cfg, sched=sched)
    assert sched == [
        (12 + cfg.difs_slots + 2, BACKOFF_PRIORITY, station.id, "backoff_expire")
    ]


def test_simultaneous_backoff_expiries_collide_in_simulator():
    cfg = Config(sim_time_s=0.00004, difs_slots=1, cw0=2)
    stations = run(
        cfg=cfg,
        n=2,
        rate=0,
        seed=1,
        channel=Channel(frame_slots=3),
        arrivals=[(0, 0), (1, 0)],
        backoffs=0,
    )

    assert [station.collisions for station in stations] == [1, 1]
    assert [station.attempts for station in stations] == [1, 1]


def test_waiting_station_freezes_backoff_until_medium_idle_after_ack():
    cfg = Config(sim_time_s=0.0002, difs_slots=1, sifs_slots=1, ack_slots=2)
    stations = run(
        cfg=cfg,
        n=2,
        rate=0,
        seed=1,
        channel=Channel(frame_slots=1),
        arrivals=[(0, 0), (1, 0)],
        backoffs={0: 0, 1: 5},
    )

    assert [station.successes for station in stations] == [1, 1]
    assert stations[1].delays == [15]


def test_poisson_arrivals_are_reproducible_from_seed():
    cfg = Config(sim_time_s=0.0002)

    def simulate(seed):
        return run(
            cfg=cfg,
            n=2,
            rate=500_000,
            seed=seed,
            channel=Channel(frame_slots=1),
        )

    first = simulate(seed=7)
    second = simulate(seed=7)
    assert [
        (station.successes, station.attempts, station.delays)
        for station in first
    ] == [
        (station.successes, station.attempts, station.delays)
        for station in second
    ]


def test_nav_reservation_defers_other_stations():
    channel = Channel()
    channel.reserve_nav(station_id=0, until_slot=20)

    assert channel.is_busy(station_id=1, slot=19)
    assert not channel.is_busy(station_id=1, slot=20)
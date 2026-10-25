import pytest

from src.channel import Channel
from src.config import Config
from src.metrics import Metrics
from src.simulator import run
from src.station import Station


def test_simulator_output_can_be_measured_as_station_and_network_throughput():
    cfg = Config(
        sim_time_s=0.001,
        difs_slots=1,
        sifs_slots=1,
        ack_slots=2,
    )
    stations = run(
        cfg=cfg,
        n=1,
        rate=0,
        seed=1,
        channel=Channel(frame_slots=5),
        arrivals=[(0, 0)],
        backoffs=0,
    )

    assert stations[0].successes == 1
    assert stations[0].delays == [9]
    assert Metrics.mean_packet_delay(stations[0]) == 9
    assert Metrics.per_station_throughput(stations, cfg) == {0: 12.0}
    assert Metrics.network_throughput(stations, cfg) == 12.0


def test_mean_packet_delay_averages_successful_packet_delays():
    station = Station(station_id=0, cw0=8)
    station.delays = [11, 19]

    assert Metrics.mean_packet_delay(station) == 15


def test_mean_packet_delay_is_zero_when_no_packets_succeed():
    station = Station(station_id=0, cw0=8)

    assert Metrics.mean_packet_delay(station) == 0.0


def test_collision_probability_is_zero_when_station_has_no_attempts():
    station = Station(station_id=0, cw0=8)

    assert Metrics.collision_probability(station) == 0.0


def test_collision_probability_is_collisions_divided_by_attempts():
    station = Station(station_id=0, cw0=8)
    station.attempts = 4
    station.collisions = 1

    assert Metrics.collision_probability(station) == 0.25


def test_percentile_packet_delay_returns_95th_percentile():
    station = Station(station_id=0, cw0=8)
    station.delays = list(range(1, 21))

    assert Metrics.percentile_packet_delay(station) == 19


def test_percentile_packet_delay_is_zero_when_no_packets_succeed():
    station = Station(station_id=0, cw0=8)

    assert Metrics.percentile_packet_delay(station) == 0.0


def test_jains_fairness_index_is_one_for_equal_station_throughput():
    stations = [
        Station(station_id=0, cw0=8),
        Station(station_id=1, cw0=8),
    ]
    for station in stations:
        station.successes = 4

    assert Metrics.jains_fairness_index(stations) == 1.0


def test_jains_fairness_index_handles_unequal_station_throughput():
    stations = [
        Station(station_id=0, cw0=8),
        Station(station_id=1, cw0=8),
        Station(station_id=2, cw0=8),
    ]
    stations[0].successes = 2
    stations[1].successes = 1

    assert Metrics.jains_fairness_index(stations) == pytest.approx(0.6)


@pytest.mark.parametrize("stations", [[], [Station(station_id=0, cw0=8)]])
def test_jains_fairness_index_is_zero_for_empty_or_zero_throughput(stations):
    assert Metrics.jains_fairness_index(stations) == 0.0


def test_network_throughput_sums_successful_payload_throughput():
    cfg = Config(sim_time_s=1)
    stations = [
        Station(station_id=0, cw0=cfg.cw0),
        Station(station_id=1, cw0=cfg.cw0),
    ]
    stations[0].successes = 2
    stations[1].successes = 3

    assert Metrics.per_station_throughput(stations, cfg) == {0: 0.024, 1: 0.036}
    assert Metrics.network_throughput(stations, cfg) == 0.06


def test_throughput_requires_positive_simulation_duration():
    with pytest.raises(ValueError, match="sim_time_s must be positive"):
        Metrics.network_throughput([], Config(sim_time_s=0))

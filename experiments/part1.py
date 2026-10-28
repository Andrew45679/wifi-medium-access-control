import csv
import math
from pathlib import Path
from types import SimpleNamespace

import matplotlib.pyplot as plt
import numpy as np

from src.channel import Channel
from src.config import Config
from src.metrics import Metrics
from src.simulator import run


cfg = Config()
station_count = 2
arrival_rates = [100, 200, 300, 500, 800, 1000]
seeds = [1, 2, 3, 4, 5]
topologies = {
    "single_collision_domain": None,
    "hidden_terminals": [[False, False], [False, False]],
}
rts_cts_options = [False, True]
root = Path(__file__).resolve().parents[1]


class CollisionTrackingChannel(Channel):
    def __init__(self, frame_slots, sensing_matrix=None):
        super().__init__(frame_slots, sensing_matrix=sensing_matrix)
        self.collided_attempts = {station_id: 0 for station_id in range(station_count)}
        self.collided_stations = set()

    def transmit(self, station_id, slot, duration_slots=None):
        end_slot = super().transmit(station_id, slot, duration_slots)
        for active_id in self.active:
            if (
                not self.results[active_id]
                and active_id not in self.collided_stations
            ):
                self.collided_attempts[active_id] += 1
                self.collided_stations.add(active_id)
        return end_slot

    def end_transmission(self, station_id):
        result = super().end_transmission(station_id)
        self.collided_stations.discard(station_id)
        return result


def calculate_metrics():
    """Run all arrival-rate, topology, RTS/CTS, and seed combinations."""
    slot_seconds = cfg.slot_us / 1_000_000
    frame_slots = math.ceil(
        (cfg.data_bytes * 8 / cfg.channel_rate_bps) / slot_seconds
    )
    results = []

    for arrival_rate in arrival_rates:
        for topology, sensing_matrix in topologies.items():
            for rts_cts in rts_cts_options:
                for seed in seeds:
                    channel = CollisionTrackingChannel(
                        frame_slots, sensing_matrix=sensing_matrix
                    )
                    stations = run(
                        cfg=cfg,
                        n=station_count,
                        rate=arrival_rate,
                        seed=seed,
                        channel=channel,
                        rts_cts=rts_cts,
                    )
                    throughputs = Metrics.per_station_throughput(stations, cfg)

                    for station in stations:
                        attempts = station.attempts
                        collisions = channel.collided_attempts[station.id]
                        results.append(
                            {
                                "arrival_rate": arrival_rate,
                                "topology": topology,
                                "rts_cts": rts_cts,
                                "seed": seed,
                                "station_id": station.id,
                                "successes": station.successes,
                                "attempts": attempts,
                                "throughput_mbps": throughputs[station.id],
                                "collided_attempts": collisions,
                                "collision_probability": (
                                    Metrics.collision_probability(
                                        SimpleNamespace(
                                            attempts=attempts,
                                            collisions=collisions,
                                        )
                                    )
                                ),
                            }
                        )

    return results


def save_results(results):
    """Write per-station results to results/part1_results.csv."""
    output_file = root / "results" / "part1_results.csv"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "arrival_rate",
        "topology",
        "rts_cts",
        "seed",
        "station_id",
        "successes",
        "attempts",
        "throughput_mbps",
        "collided_attempts",
        "collision_probability",
    ]

    with output_file.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(results)


def plot_metric(results, metric, rts_cts, ylabel, title, filename):
    """Plot both stations and topologies for one RTS/CTS setting."""
    for topology in topologies:
        for station_id, station_name in enumerate(("A", "B")):
            averages = []
            for arrival_rate in arrival_rates:
                values = [
                    result[metric]
                    for result in results
                    if result["arrival_rate"] == arrival_rate
                    and result["topology"] == topology
                    and result["rts_cts"] == rts_cts
                    and result["station_id"] == station_id
                ]
                averages.append(np.mean(values))

            plt.plot(
                arrival_rates,
                averages,
                marker="o",
                label=f"Station {station_name} - {topology.replace('_', ' ')}",
            )

    plt.xlabel("Arrival rate, λ (frames/s)")
    plt.ylabel(ylabel)
    mode = "with RTS/CTS" if rts_cts else "without RTS/CTS"
    plt.title(f"{title} {mode}")
    plt.xticks(arrival_rates)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(root / "figures" / filename, dpi=300)
    plt.close()


def make_plots(results):
    """Generate metric figures split by RTS/CTS mode."""
    figures_dir = root / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    for rts_cts in rts_cts_options:
        mode = "with_rts_cts" if rts_cts else "without_rts_cts"
        plot_metric(
            results,
            "throughput_mbps",
            rts_cts,
            "Throughput (Mbps)",
            "CSMA/CA Throughput",
            f"part1_throughput_{mode}.png",
        )
        plot_metric(
            results,
            "collision_probability",
            rts_cts,
            "Collision probability",
            "CSMA/CA Collision Probability",
            f"part1_collision_probability_{mode}.png",
        )


if __name__ == "__main__":
    experiment_results = calculate_metrics()
    save_results(experiment_results)
    make_plots(experiment_results)

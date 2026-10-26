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
station_counts = [2, 5, 10, 20, 40]
loads = [300, 800]
seeds = [1, 2, 3, 4, 5]
results = []
root = Path(__file__).resolve().parents[1]


class CollisionTrackingChannel(Channel):
    def __init__(self, frame_slots):
        """Initialize a channel that counts each collided attempt once."""
        super().__init__(frame_slots)
        self.collided_attempts = 0
        self.collided_stations = set()

    def transmit(self, station_id, slot):
        """Transmit a frame and record each newly collided attempt."""
        end_slot = super().transmit(station_id, slot)
        for active_id in self.active:
            if not self.results[active_id] and active_id not in self.collided_stations:
                self.collided_attempts += 1
                self.collided_stations.add(active_id)
        return end_slot

    def end_transmission(self, station_id):
        """End a frame and clear its collision-tracking state."""
        result = super().end_transmission(station_id)
        self.collided_stations.discard(station_id)
        return result


def calculate_metrics():
    """Run every station-count, load, and seed combination and collect metrics."""
    slot_seconds = cfg.slot_us / 1_000_000
    frame_slots = math.ceil(
        (cfg.data_bytes * 8 / cfg.channel_rate_bps) / slot_seconds
    )

    for n in station_counts:
        for load in loads:
            for seed in seeds:
                channel = CollisionTrackingChannel(frame_slots)
                stations = run(
                    cfg=cfg,
                    n=n,
                    rate=load / n,
                    seed=seed,
                    channel=channel,
                )

                delays = [delay for station in stations for delay in station.delays]
                attempts = sum(station.attempts for station in stations)
                delay_results = SimpleNamespace(delays=delays)
                collision_results = SimpleNamespace(
                    attempts=attempts,
                    collisions=channel.collided_attempts,
                )
                throughputs = Metrics.per_station_throughput(stations, cfg)

                results.append(
                    {
                        "n": n,
                        "load": load,
                        "seed": seed,
                        "stations": stations,
                        "throughputs": throughputs,
                        "aggregate_throughput": Metrics.network_throughput(
                            stations, cfg
                        ),
                        "collided_attempts": channel.collided_attempts,
                        "total_attempts": attempts,
                        "collision_probability": Metrics.collision_probability(
                            collision_results
                        ),
                        "mean_delay_ms": (
                            Metrics.mean_packet_delay(delay_results)
                            * cfg.slot_us
                            / 1000
                        ),
                        "percentile_95_delay_ms": (
                            Metrics.percentile_packet_delay(delay_results)
                            * cfg.slot_us
                            / 1000
                        ),
                        "jains_fairness": Metrics.jains_fairness_index(stations),
                    }
                )


def save_results():
    """Write station and run metrics to results/part2_results.csv."""
    output_file = root / "results" / "part2_results.csv"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "n", "load", "seed", "station_id", "successes", "attempts",
        "throughput_mbps", "aggregate_throughput_mbps", "collided_attempts",
        "total_attempts", "collision_probability", "mean_delay_ms",
        "percentile_95_delay_ms", "jains_fairness",
    ]

    with output_file.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        for result in results:
            for station in result["stations"]:
                writer.writerow(
                    {
                        "n": result["n"],
                        "load": result["load"],
                        "seed": result["seed"],
                        "station_id": station.id,
                        "successes": station.successes,
                        "attempts": station.attempts,
                        "throughput_mbps": result["throughputs"][station.id],
                        "aggregate_throughput_mbps": result[
                            "aggregate_throughput"
                        ],
                        "collided_attempts": result["collided_attempts"],
                        "total_attempts": result["total_attempts"],
                        "collision_probability": result[
                            "collision_probability"
                        ],
                        "mean_delay_ms": result["mean_delay_ms"],
                        "percentile_95_delay_ms": result[
                            "percentile_95_delay_ms"
                        ],
                        "jains_fairness": result["jains_fairness"],
                    }
                )


def plot_metric(metric, ylabel, title, filename):
    """Plot one metric against station count for each offered load."""
    for load in loads:
        averages = []
        for n in station_counts:
            values = [
                result[metric]
                for result in results
                if result["n"] == n and result["load"] == load
            ]
            averages.append(np.mean(values))
        plt.plot(station_counts, averages, marker="o", label=f"Λ = {load}")

    plt.xlabel("Number of stations (N)")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.xticks(station_counts)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(root / "figures" / filename, dpi=300)
    plt.close()


def make_plots():
    """Generate the four Part II figures in the figures directory."""
    figures_dir = root / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    plot_metric(
        "aggregate_throughput",
        "Aggregate throughput (Mbps)",
        "Dense DCF Aggregate Throughput",
        "part2_throughput.png",
    )
    plot_metric(
        "collision_probability",
        "Collision probability",
        "Dense DCF Collision Probability",
        "part2_collision_probability.png",
    )
    plot_metric(
        "jains_fairness",
        "Jain's Fairness Index",
        "Dense DCF Throughput Fairness",
        "part2_fairness.png",
    )

    for load in loads:
        mean_delays = []
        percentile_delays = []
        for n in station_counts:
            run_results = [
                result
                for result in results
                if result["n"] == n and result["load"] == load
            ]
            mean_delays.append(
                np.mean([result["mean_delay_ms"] for result in run_results])
            )
            percentile_delays.append(
                np.mean(
                    [result["percentile_95_delay_ms"] for result in run_results]
                )
            )
        plt.plot(
            station_counts,
            mean_delays,
            marker="o",
            label=f"Mean, Λ = {load}",
        )
        plt.plot(
            station_counts,
            percentile_delays,
            marker="o",
            linestyle="--",
            label=f"95th percentile, Λ = {load}",
        )

    plt.xlabel("Number of stations (N)")
    plt.ylabel("Packet delay (ms)")
    plt.title("Dense DCF Packet Delay")
    plt.xticks(station_counts)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(figures_dir / "part2_delay.png", dpi=300)
    plt.close()


if __name__ == "__main__":
    calculate_metrics()
    save_results()
    make_plots()

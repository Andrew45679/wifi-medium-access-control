import csv
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from src.channel import Channel
from src.config import Config
from src.simulator import run


cfg = Config()
station_counts = [2, 5, 10, 20, 40]
loads = [300, 800]
seeds = [1, 2, 3, 4, 5]
results = []
root = Path(__file__).resolve().parents[1]


class CollisionTrackingChannel(Channel):
    def __init__(self, frame_slots):
        super().__init__(frame_slots)
        self.collided_attempts = 0
        self._counted_collisions = set()

    def transmit(self, station_id, slot):
        end_slot = super().transmit(station_id, slot)

        for active_id in self.active:
            if not self.results[active_id] and active_id not in self._counted_collisions:
                self.collided_attempts += 1
                self._counted_collisions.add(active_id)

        return end_slot

    def end_transmission(self, station_id):
        success = super().end_transmission(station_id)
        self._counted_collisions.discard(station_id)
        return success


def calculate_metrics():
    slot_seconds = cfg.slot_us / 1_000_000
    frame_seconds = cfg.data_bytes * 8 / cfg.channel_rate_bps
    frame_slots = math.ceil(frame_seconds / slot_seconds)

    for n in station_counts:
        for load in loads:
            rate_per_station = load / n

            for seed in seeds:
                channel = CollisionTrackingChannel(frame_slots)
                stations = run(
                    cfg=cfg,
                    n=n,
                    rate=rate_per_station,
                    seed=seed,
                    channel=channel,
                )

                all_delays_ms = [
                    delay * cfg.slot_us / 1000
                    for station in stations
                    for delay in station.delays
                ]
                station_throughputs = [
                    station.successes
                    * cfg.data_bytes
                    * 8
                    / cfg.sim_time_s
                    / 1_000_000
                    for station in stations
                ]
                total_attempts = sum(station.attempts for station in stations)
                fairness_denominator = n * sum(
                    throughput**2 for throughput in station_throughputs
                )

                results.append(
                    {
                        "n": n,
                        "load": load,
                        "seed": seed,
                        "stations": stations,
                        "station_throughputs": station_throughputs,
                        "aggregate_throughput": sum(station_throughputs),
                        "collided_attempts": channel.collided_attempts,
                        "total_attempts": total_attempts,
                        "collision_probability": (
                            channel.collided_attempts / total_attempts
                            if total_attempts
                            else 0
                        ),
                        "mean_delay": (
                            float(np.mean(all_delays_ms))
                            if all_delays_ms
                            else 0
                        ),
                        "percentile_95_delay": (
                            float(np.percentile(all_delays_ms, 95))
                            if all_delays_ms
                            else 0
                        ),
                        "jains_fairness": (
                            sum(station_throughputs) ** 2
                            / fairness_denominator
                            if fairness_denominator
                            else 0
                        ),
                    }
                )


def save_results():
    output_file = root / "results" / "results.csv"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "n",
        "load",
        "seed",
        "station_id",
        "successes",
        "attempts",
        "throughput_mbps",
        "aggregate_throughput_mbps",
        "collided_attempts",
        "total_attempts",
        "collision_probability",
        "mean_delay_ms",
        "percentile_95_delay_ms",
        "jains_fairness",
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
                        "throughput_mbps": result["station_throughputs"][
                            station.id
                        ],
                        "aggregate_throughput_mbps": result[
                            "aggregate_throughput"
                        ],
                        "collided_attempts": result["collided_attempts"],
                        "total_attempts": result["total_attempts"],
                        "collision_probability": result[
                            "collision_probability"
                        ],
                        "mean_delay_ms": result["mean_delay"],
                        "percentile_95_delay_ms": result[
                            "percentile_95_delay"
                        ],
                        "jains_fairness": result["jains_fairness"],
                    }
                )


def plot_metric(metric, ylabel, title, filename):
    for load in loads:
        values = []
        for n in station_counts:
            run_values = [
                result[metric]
                for result in results
                if result["n"] == n and result["load"] == load
            ]
            values.append(np.mean(run_values))

        plt.plot(station_counts, values, marker="o", label=f"Λ = {load}")

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
    for load in loads:
        means = []
        percentiles_95 = []
        for n in station_counts:
            run_results = [
                result
                for result in results
                if result["n"] == n and result["load"] == load
            ]
            means.append(np.mean([result["mean_delay"] for result in run_results]))
            percentiles_95.append(
                np.mean(
                    [result["percentile_95_delay"] for result in run_results]
                )
            )

        plt.plot(
            station_counts,
            means,
            marker="o",
            label=f"Mean, Λ = {load}",
        )
        plt.plot(
            station_counts,
            percentiles_95,
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

    plot_metric(
        "jains_fairness",
        "Jain's Fairness Index",
        "Dense DCF Throughput Fairness",
        "part2_fairness.png",
    )


if __name__ == "__main__":
    calculate_metrics()
    save_results()
    make_plots()

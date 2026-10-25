# Throughput, collision probability, packet delay, Jain's index

class Metrics:
    @staticmethod
    def station_throughput(station, cfg):
        """Return one station's successful-payload throughput in Mbps."""
        if cfg.sim_time_s <= 0:
            raise ValueError("sim_time_s must be positive")

        return (
            station.successes * cfg.data_bytes * 8 / (cfg.sim_time_s * 1_000_000)
        )

    @classmethod
    def per_station_throughput(cls, stations, cfg):
        """Return successful-payload throughput in Mbps keyed by station ID."""
        if cfg.sim_time_s <= 0:
            raise ValueError("sim_time_s must be positive")

        return {
            station.id: cls.station_throughput(station, cfg)
            for station in stations
        }

    @classmethod
    def network_throughput(cls, stations, cfg):
        """Return aggregate network throughput in Mbps."""
        return sum(cls.per_station_throughput(stations, cfg).values())
    
    @staticmethod
    def collision_probability(station):
        """Return the probability of a collision for this station."""
        if station.attempts == 0:
            return 0.0
        return station.collisions / station.attempts
    
    @staticmethod
    def mean_packet_delay(station):
        """Return mean successful-packet delay in slots, from queue arrival to ACK."""
        if not station.delays:
            return 0.0
        return sum(station.delays) / len(station.delays)

    @staticmethod
    def percentile_packet_delay(station):
        """Return the 95th percentile delay of successfully transmitted packets in slots."""
        if not station.delays:
            return 0.0
        sorted_delays = sorted(station.delays)
        index = int(0.95 * len(sorted_delays)) - 1
        return sorted_delays[index]

    @staticmethod
    def jains_fairness_index(stations):
        """Return Jain's fairness index for the network throughput of all stations."""
        throughputs = [station.successes for station in stations]
        n = len(throughputs)
        if n == 0:
            return 0.0
        sum_throughput = sum(throughputs)
        sum_squared_throughput = sum(t ** 2 for t in throughputs)
        if sum_squared_throughput == 0:
            return 0.0
        return (sum_throughput ** 2) / (n * sum_squared_throughput)
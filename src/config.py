# Shared simulation settings.
"""
Configuration parameters for the simulation.
"""

from dataclasses import dataclass
 
 
@dataclass(frozen=True)
class Config:

    # Timing settings.
    slot_us: int = 10
    sim_time_s: int = 10
    difs_slots: int = 3
    sifs_slots: int = 1
 
    # Frame and control settings.
    data_bytes: int = 1500
    ack_slots: int = 2
    rts_slots: int = 2
    cts_slots: int = 2
 
    channel_rate_bps: int = 12_000_000
 
    # Contention-window limits.
    cw0: int = 8
    cwmax: int = 1024
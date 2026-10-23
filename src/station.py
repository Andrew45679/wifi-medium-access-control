# Stores one station's queue, DCF state, and statistics.
"""
Represents a Wi-Fi station and its transmission state.
"""

from collections import deque


class Station:
    # Set up a station with its ID and initial contention window.
    def __init__(self, station_id, cw0):
        # Station ID
        self.id = station_id

        # Transmit queue: arrival slot of each waiting frame (head = oldest).
        self.queue = deque()

        # Current contention window (slots)
        self.cw = cw0          
        # current backoff counter (slots until next transmission attempt)
        self.backoff = 0   
        # Number of consecutive collisions for the current frame   
        self.collisions = 0      

        # Successful frames sent
        self.successes = 0     
        # transmission attempts
        self.attempts = 0  

        # Delay of each successfully transmitted frame, measured in slots
        self.delays = []

        # Whether the station has a backoff countdown scheduled
        self.countdown_active = False

        # Whether the station is transmitting or waiting for its ACK
        self.transmitting = False

        # Track pending backoff and ACK state.
        self.backoff_pending = False
        self.awaiting_ack = False
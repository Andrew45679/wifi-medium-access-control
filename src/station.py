"""
Represents a Wi-Fi station and its transmission state.
"""

from collections import deque


class Station:
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
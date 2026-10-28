
# Tracks channel use, collisions, and reservations.
class Channel:
    # Set the frame duration.
    def __init__(self, frame_slots=50, sensing_matrix=None):
        # Frame duration in slots.
        self.frame_slots = frame_slots

        if sensing_matrix is not None:
            matrix = tuple(tuple(row) for row in sensing_matrix)
            if any(len(row) != len(matrix) for row in matrix):
                raise ValueError("sensing_matrix must be square")
            self.sensing_matrix = matrix
        else:
            self.sensing_matrix = None

        # Active frames by station: (start, end).
        self.active = {}

        # Transmission results by station.
        self.results = {}
        # NAV end slot by station.
        self.nav_until = {}
        # End of the control exchange.
        self.control_busy_until = 0

    # Check if this station senses a busy channel.
    def is_busy(self, station_id, slot):
        # Check transmissions this station can sense.
        for other_id, (start, end) in self.active.items():
            if (
                other_id != station_id
                and self._can_sense(station_id, other_id)
                and start <= slot < end
            ):
                return True

        # Check other stations' NAV.
        for other_id, until in self.nav_until.items():
            if (
                other_id != station_id
                and self._can_sense(station_id, other_id)
                and until > slot
            ):
                return True

        # Check control activity.
        return self.control_busy_until > slot

    def _can_sense(self, listener_id, transmitter_id):
        if self.sensing_matrix is None:
            return True
        if not (
            0 <= listener_id < len(self.sensing_matrix)
            and 0 <= transmitter_id < len(self.sensing_matrix)
        ):
            raise ValueError("station id is outside sensing_matrix")
        return bool(self.sensing_matrix[listener_id][transmitter_id])

    # Set or extend a station's NAV.
    def reserve_nav(self, station_id, until_slot):
        self.nav_until[station_id] = max(
            until_slot, self.nav_until.get(station_id, until_slot)
        )

    # Reserve the channel for control.
    def reserve_control(self, until_slot):
        self.control_busy_until = max(self.control_busy_until, until_slot)

    # Clear the reservation when it ends.
    def release_control(self, slot):
        if self.control_busy_until <= slot:
            self.control_busy_until = 0

    # Check if a transmission or control exchange is active.
    def is_physically_busy(self, slot):
        return bool(self.active) or self.control_busy_until > slot

    # Start a frame and detect overlaps.
    def transmit(self, station_id, slot, duration_slots=None):
        if duration_slots is None:
            duration_slots = self.frame_slots
        end = slot + duration_slots
        collided = False

        # Mark overlapping transmissions as collided.
        for other_id, (other_start, other_end) in self.active.items():
            overlaps = slot < other_end and other_start < end
            if overlaps:
                self.results[other_id] = False
                collided = True

        self.active[station_id] = (slot, end)
        self.results[station_id] = not collided

        return end

    # End a frame and return its result.
    def end_transmission(self, station_id):
        success = self.results.get(station_id, False)
        self.active.pop(station_id, None)
        return success

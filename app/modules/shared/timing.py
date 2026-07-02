import math
import random
from typing import Optional

from app.modules.shared.config import get_config


class TimingService:
    def __init__(self):
        self.config = get_config()

    def calculate_delay(
        self,
        post_age_hours: float,
        base_delay: float = 300.0,
    ) -> float:
        s_curve_cfg = self.config.get("s_curve", default={})

        if not s_curve_cfg.get("enabled", True):
            return self._apply_entropy(base_delay)

        remaining = max(4 - post_age_hours, 0.25)

        s_curve_weight = self._sigmoid(remaining)

        jitter_sigma = self.config.get("timing", "jitter_sigma", default=120)
        gaussian_jitter = random.gauss(jitter_sigma / 2, jitter_sigma)

        micro_min = self.config.get("timing", "micro_jitter_min_ms", default=100)
        micro_max = self.config.get("timing", "micro_jitter_max_ms", default=900)
        micro_jitter = random.randint(micro_min, micro_max) / 1000

        skip_chance = self.config.get("timing", "skip_cycle_chance", default=0.08)
        if random.random() < skip_chance:
            return self.calculate_delay(post_age_hours, base_delay * 2)

        clump_chance = self.config.get("timing", "clump_chance", default=0.15)
        if random.random() < clump_chance:
            return random.uniform(0.2, 0.5) * base_delay

        delay = s_curve_weight * base_delay + gaussian_jitter + micro_jitter
        return max(0, delay)

    def _sigmoid(self, x: float) -> float:
        steepness = 8 / max(x, 1)
        return 1 - (1 / (1 + math.exp(-steepness * (x - 0.3))))

    def _apply_entropy(self, base_delay: float) -> float:
        jitter_sigma = self.config.get("timing", "jitter_sigma", default=120)
        jitter = random.gauss(jitter_sigma / 2, jitter_sigma)
        return max(0, base_delay + jitter)

    def get_vote_schedule(
        self,
        num_votes: int,
        window_hours: float = 4.0,
    ) -> list[float]:
        s_curve_cfg = self.config.get("s_curve", default={})

        if not s_curve_cfg.get("enabled", True):
            return [self._apply_entropy(window_hours * 3600 / num_votes) for _ in range(num_votes)]

        initial_burst = s_curve_cfg.get("initial_burst", 0.30)
        peak = s_curve_cfg.get("peak", 0.45)
        decay = s_curve_cfg.get("decay", 0.20)
        tail = s_curve_cfg.get("tail", 0.05)

        window_seconds = window_hours * 3600

        burst_count = int(num_votes * initial_burst)
        peak_count = int(num_votes * peak)
        decay_count = int(num_votes * decay)
        tail_count = num_votes - burst_count - peak_count - decay_count

        burst_window = window_seconds * 0.125
        peak_window = window_seconds * 0.375
        decay_window = window_seconds * 0.375
        tail_window = window_seconds * 0.125

        schedule = []

        for i in range(burst_count):
            t = random.uniform(0, burst_window)
            schedule.append((t, "burst"))

        for i in range(peak_count):
            t = burst_window + random.uniform(0, peak_window)
            schedule.append((t, "peak"))

        for i in range(decay_count):
            t = burst_window + peak_window + random.uniform(0, decay_window)
            schedule.append((t, "decay"))

        for i in range(tail_count):
            t = burst_window + peak_window + decay_window + random.uniform(0, tail_window)
            schedule.append((t, "tail"))

        schedule.sort(key=lambda x: x[0])
        return [t for t, _ in schedule]

    def get_randomized_delay(self, min_s: float = 0.5, max_s: float = 3.0) -> float:
        return random.uniform(min_s, max_s)


def get_timing_service() -> TimingService:
    return TimingService()

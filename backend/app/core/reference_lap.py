"""Reference lap selection for track layout detection.

Auto-picks the best reference lap based on:
- Valid lap (completed, no off-track)
- Near fastest time (within threshold)
- Clean driving (no spins, consistent steering)
- Consistent braking zones
"""

import logging

from app.models.session import Lap
from app.models.signal import SignalSlice

logger = logging.getLogger(__name__)


class ReferenceLapSelector:
    """Selects optimal reference lap for segment detection."""

    # Time threshold: reference lap must be within X% of fastest
    TIME_THRESHOLD_PERCENT: float = 3.0
    # Maximum steering rate for clean lap (degrees per second, normalized)
    MAX_STEERING_RATE: float = 500.0
    # Steering consistency threshold (std dev of steering rate)
    STEERING_CONSISTENCY_THRESHOLD: float = 200.0
    # Minimum brake pressure to consider braking zone
    BRAKE_THRESHOLD: float = 0.1
    # Minimum samples for valid analysis
    MIN_SAMPLES: int = 100

    def select_reference_lap(
        self,
        laps: list[Lap],
        steering_signal: SignalSlice | None = None,
        brake_signal: SignalSlice | None = None,
        preferred_lap: int | None = None,
    ) -> int | None:
        """Select best reference lap from available laps.

        Scoring criteria:
        - Fast lap bonus: 100 × (best_time / lap_time)
        - Valid lap bonus: +50 points
        - Clean steering bonus: +30 points (if steering rate OK)
        - Consistency bonus: +20 points

        Args:
            laps: List of available laps
            steering_signal: Optional steering data for analysis
            brake_signal: Optional brake data for analysis
            preferred_lap: User override lap number

        Returns:
            Best lap number or None if no valid lap found
        """
        if not laps:
            logger.warning("No laps available for reference selection")
            return None

        # User override takes precedence
        if preferred_lap is not None:
            for lap in laps:
                if lap.lap_number == preferred_lap and lap.valid:
                    logger.info(f"Using user-preferred reference lap: {preferred_lap}")
                    return preferred_lap
            logger.warning(f"Preferred lap {preferred_lap} not found or invalid")

        # Get valid laps with times
        valid_laps = [lap for lap in laps if lap.valid and lap.lap_time and lap.lap_time > 0]
        if not valid_laps:
            logger.warning("No valid laps with lap times found")
            return None

        # Find fastest lap time
        best_time = min(lap.lap_time for lap in valid_laps if lap.lap_time)

        # Score each lap
        lap_scores: list[tuple[int, float]] = []

        for lap in valid_laps:
            if not lap.lap_time:
                continue

            score = self._calculate_lap_score(lap, best_time, steering_signal, brake_signal)
            lap_scores.append((lap.lap_number, score))
            logger.debug(f"Lap {lap.lap_number}: score {score:.1f}, time {lap.lap_time:.3f}s")

        if not lap_scores:
            return None

        # Sort by score descending
        lap_scores.sort(key=lambda x: x[1], reverse=True)
        best_lap = lap_scores[0][0]

        logger.info(f"Selected reference lap {best_lap} with score {lap_scores[0][1]:.1f}")
        return best_lap

    def _calculate_lap_score(
        self,
        lap: Lap,
        best_time: float,
        steering_signal: SignalSlice | None,
        brake_signal: SignalSlice | None,
    ) -> float:
        """Calculate quality score for a lap."""
        if not lap.lap_time:
            return 0.0

        score = 0.0

        # Speed score: 100 × (best / current)
        speed_ratio = best_time / lap.lap_time
        score += 100.0 * speed_ratio

        # Valid lap bonus
        if lap.valid:
            score += 50.0

        # Clean steering analysis (if signal available)
        if steering_signal and len(steering_signal.values) >= self.MIN_SAMPLES:
            steering_score = self._analyze_steering(steering_signal)
            score += steering_score

        # Brake consistency analysis (if signal available)
        if brake_signal and len(brake_signal.values) >= self.MIN_SAMPLES:
            brake_score = self._analyze_braking(brake_signal)
            score += brake_score

        return score

    def _analyze_steering(self, steering_signal: SignalSlice) -> float:
        """Analyze steering signal for cleanliness.

        Returns:
            Score bonus (0-50) based on steering quality
        """
        values = steering_signal.values
        if len(values) < 2:
            return 0.0

        # Calculate steering rate (change per sample)
        rates = [abs(values[i] - values[i - 1]) for i in range(1, len(values))]
        max_rate = max(rates) if rates else 0.0
        avg_rate = sum(rates) / len(rates) if rates else 0.0

        # Check for full-lock spins (very high rates)
        if max_rate > self.MAX_STEERING_RATE:
            # Significant penalty for spins
            return 0.0

        # Bonus for smooth steering
        if avg_rate < self.STEERING_CONSISTENCY_THRESHOLD:
            return 30.0

        return 15.0  # Partial bonus

    def _analyze_braking(self, brake_signal: SignalSlice) -> float:
        """Analyze brake signal for consistency.

        Returns:
            Score bonus (0-20) based on braking quality
        """
        values = brake_signal.values
        if len(values) < self.MIN_SAMPLES:
            return 0.0

        # Count braking zones
        braking_zones = 0
        in_braking = False

        for val in values:
            if val > self.BRAKE_THRESHOLD and not in_braking:
                braking_zones += 1
                in_braking = True
            elif val <= self.BRAKE_THRESHOLD:
                in_braking = False

        # Expected braking zones for a typical track: 8-15
        if 6 <= braking_zones <= 20:
            return 20.0  # Normal range
        elif braking_zones > 30:
            return 0.0  # Way too many (likely brake riding)
        else:
            return 10.0  # Unusual but possible

    def is_lap_clean(
        self,
        lap: Lap,
        steering_signal: SignalSlice | None = None,
    ) -> bool:
        """Check if a lap appears clean (no spins, completed)."""
        if not lap.valid or not lap.lap_time:
            return False

        if steering_signal and len(steering_signal.values) >= 2:
            values = steering_signal.values
            rates = [abs(values[i] - values[i - 1]) for i in range(1, len(values))]
            max_rate = max(rates) if rates else 0.0

            if max_rate > self.MAX_STEERING_RATE:
                return False

        return True

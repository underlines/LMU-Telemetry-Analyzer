"""Segment cache service for two-tier caching.

Tier 1: Track Layout Cache - stored per track, versioned
Tier 2: Lap Metrics Cache - stored per session/lap

Storage: Parquet files in ./cache/ directory (project local)
"""

import logging
from pathlib import Path

import duckdb

from app.core.config import get_cache_dir
from app.models.segment import LapSegmentMetrics, TrackLayout

logger = logging.getLogger(__name__)


class SegmentCache:
    """Two-tier cache for track layouts and lap metrics."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        """Initialize cache with optional custom directory."""
        self.cache_dir = cache_dir or get_cache_dir()
        self.layouts_dir = self.cache_dir / "layouts"
        self.metrics_dir = self.cache_dir / "metrics"

        # Ensure directories exist
        self.layouts_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_dir.mkdir(parents=True, exist_ok=True)

    def _get_layout_path(self, track_key: str) -> Path:
        """Generate cache file path for a track layout."""
        return self.layouts_dir / f"{track_key}.parquet"

    def _get_metrics_path(self, session_id: str, lap_number: int) -> Path:
        """Generate cache file path for lap metrics."""
        session_dir = self.metrics_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir / f"lap_{lap_number}.parquet"

    def _make_track_key(self, track_name: str, layout: str | None, version: int) -> str:
        """Generate unique key for track layout."""
        safe_name = track_name.replace(" ", "_").replace("/", "_")
        if layout:
            safe_layout = layout.replace(" ", "_").replace("/", "_")
            return f"{safe_name}_{safe_layout}_v{version}"
        return f"{safe_name}_v{version}"

    # =========================================================================
    # Tier 1: Track Layout Cache
    # =========================================================================

    def get_layout(self, track_name: str, layout: str | None, version: int) -> TrackLayout | None:
        """Retrieve cached track layout.

        Args:
            track_name: Track name
            layout: Layout variant (optional)
            version: Layout version

        Returns:
            TrackLayout if cached, None otherwise
        """
        track_key = self._make_track_key(track_name, layout, version)
        cache_path = self._get_layout_path(track_key)

        if not cache_path.exists():
            return None

        try:
            conn = duckdb.connect(str(cache_path), read_only=True)

            # Read layout metadata
            meta_result = conn.execute(
                "SELECT track_name, track_layout, version, track_length, "
                "reference_lap_number, reference_session_id FROM layout_meta"
            ).fetchone()

            if not meta_result:
                conn.close()
                return None

            track_name, track_layout, version, track_length, ref_lap, ref_session = meta_result

            # Read segments
            segments = []
            seg_results = conn.execute(
                "SELECT segment_id, segment_type, start_dist, end_dist, "
                "entry_dist, apex_dist, exit_dist FROM segments ORDER BY start_dist"
            ).fetchall()

            for row in seg_results:
                from app.models.segment import Segment

                seg_id, seg_type, start_d, end_d, entry_d, apex_d, exit_d = row
                segments.append(
                    Segment(
                        segment_id=seg_id,
                        segment_type=seg_type,
                        start_dist=start_d,
                        end_dist=end_d,
                        entry_dist=entry_d,
                        apex_dist=apex_d,
                        exit_dist=exit_d,
                    )
                )

            conn.close()

            return TrackLayout(
                track_name=track_name,
                track_layout=track_layout,
                version=version,
                track_length=float(track_length),
                segments=segments,
                reference_lap_number=int(ref_lap),
                reference_session_id=ref_session,
            )

        except Exception as e:
            logger.warning(f"Error reading layout cache for {track_key}: {e}")
            return None

    def save_layout(self, layout: TrackLayout) -> None:
        """Cache a track layout.

        Args:
            layout: TrackLayout to cache
        """
        track_key = self._make_track_key(
            layout.track_name, layout.track_layout, layout.version
        )
        cache_path = self._get_layout_path(track_key)

        try:
            conn = duckdb.connect(str(cache_path))
            conn.execute("DROP TABLE IF EXISTS layout_meta")
            conn.execute("DROP TABLE IF EXISTS segments")

            # Create layout metadata table
            conn.execute("""
                CREATE TABLE layout_meta (
                    track_name VARCHAR,
                    track_layout VARCHAR,
                    version INTEGER,
                    track_length DOUBLE,
                    reference_lap_number INTEGER,
                    reference_session_id VARCHAR
                )
            """)

            # Insert metadata
            conn.execute(
                "INSERT INTO layout_meta VALUES (?, ?, ?, ?, ?, ?)",
                [
                    layout.track_name,
                    layout.track_layout,
                    layout.version,
                    layout.track_length,
                    layout.reference_lap_number,
                    layout.reference_session_id,
                ],
            )

            # Create segments table
            conn.execute("""
                CREATE TABLE segments (
                    segment_id VARCHAR,
                    segment_type VARCHAR,
                    start_dist DOUBLE,
                    end_dist DOUBLE,
                    entry_dist DOUBLE,
                    apex_dist DOUBLE,
                    exit_dist DOUBLE
                )
            """)

            # Insert segments
            for seg in layout.segments:
                conn.execute(
                    "INSERT INTO segments VALUES (?, ?, ?, ?, ?, ?, ?)",
                    [
                        seg.segment_id,
                        seg.segment_type,
                        seg.start_dist,
                        seg.end_dist,
                        seg.entry_dist,
                        seg.apex_dist,
                        seg.exit_dist,
                    ],
                )

            conn.close()
            logger.info(f"Saved layout cache: {cache_path}")

        except Exception as e:
            logger.error(f"Error saving layout cache for {track_key}: {e}")
            raise

    def invalidate_layout(self, track_name: str, layout: str | None, version: int) -> bool:
        """Invalidate (delete) a cached layout.

        Args:
            track_name: Track name
            layout: Layout variant
            version: Layout version

        Returns:
            True if cache was deleted, False if not found
        """
        track_key = self._make_track_key(track_name, layout, version)
        cache_path = self._get_layout_path(track_key)

        if cache_path.exists():
            cache_path.unlink()
            logger.info(f"Invalidated layout cache: {cache_path}")
            return True
        return False

    # =========================================================================
    # Tier 2: Lap Metrics Cache
    # =========================================================================

    def get_lap_metrics(
        self,
        session_id: str,
        lap_number: int,
        layout_version: int,
    ) -> LapSegmentMetrics | None:
        """Retrieve cached lap metrics.

        Args:
            session_id: Session identifier
            lap_number: Lap number
            layout_version: Expected layout version

        Returns:
            LapSegmentMetrics if cached and version matches, None otherwise
        """
        cache_path = self._get_metrics_path(session_id, lap_number)

        if not cache_path.exists():
            return None

        try:
            conn = duckdb.connect(str(cache_path), read_only=True)

            # Check layout version
            version_result = conn.execute(
                "SELECT layout_version FROM meta WHERE session_id = ? AND lap_number = ?",
                [session_id, lap_number],
            ).fetchone()

            if not version_result or version_result[0] != layout_version:
                # Version mismatch - invalidate
                conn.close()
                self.invalidate_lap_metrics(session_id, lap_number)
                return None

            # Read lap metadata
            meta_result = conn.execute(
                "SELECT track_length, total_time FROM meta WHERE session_id = ? AND lap_number = ?",
                [session_id, lap_number],
            ).fetchone()

            if not meta_result:
                conn.close()
                return None

            track_length, total_time = meta_result

            # Read segment metrics
            from app.models.segment import SegmentMetrics

            segments = []
            seg_results = conn.execute(
                "SELECT segment_id, entry_speed, mid_speed, exit_speed, min_speed, max_speed, "
                "segment_time, time_delta_to_reference, braking_distance, max_brake_pressure, "
                "throttle_application, steering_smoothness, avg_speed FROM segment_metrics "
                "ORDER BY segment_id"
            ).fetchall()

            for row in seg_results:
                (
                    seg_id,
                    entry_spd,
                    mid_spd,
                    exit_spd,
                    min_spd,
                    max_spd,
                    seg_time,
                    time_delta,
                    brake_dist,
                    max_brake,
                    throttle_app,
                    steering_smooth,
                    avg_spd,
                ) = row

                segments.append(
                    SegmentMetrics(
                        segment_id=seg_id,
                        lap_number=lap_number,
                        session_id=session_id,
                        entry_speed=entry_spd,
                        mid_speed=mid_spd,
                        exit_speed=exit_spd,
                        min_speed=min_spd,
                        max_speed=max_spd,
                        segment_time=seg_time,
                        time_delta_to_reference=time_delta,
                        braking_distance=brake_dist,
                        max_brake_pressure=max_brake,
                        throttle_application=throttle_app,
                        steering_smoothness=steering_smooth,
                        avg_speed=avg_spd,
                    )
                )

            conn.close()

            return LapSegmentMetrics(
                session_id=session_id,
                lap_number=lap_number,
                layout_version=layout_version,
                track_length=float(track_length),
                total_time=float(total_time) if total_time else None,
                segments=segments,
            )

        except Exception as e:
            logger.warning(f"Error reading metrics cache for {session_id} lap {lap_number}: {e}")
            return None

    def save_lap_metrics(self, metrics: LapSegmentMetrics) -> None:
        """Cache lap metrics.

        Args:
            metrics: LapSegmentMetrics to cache
        """
        cache_path = self._get_metrics_path(metrics.session_id, metrics.lap_number)

        try:
            conn = duckdb.connect(str(cache_path))
            conn.execute("DROP TABLE IF EXISTS meta")
            conn.execute("DROP TABLE IF EXISTS segment_metrics")

            # Create metadata table
            conn.execute("""
                CREATE TABLE meta (
                    session_id VARCHAR,
                    lap_number INTEGER,
                    layout_version INTEGER,
                    track_length DOUBLE,
                    total_time DOUBLE
                )
            """)

            conn.execute(
                "INSERT INTO meta VALUES (?, ?, ?, ?, ?)",
                [
                    metrics.session_id,
                    metrics.lap_number,
                    metrics.layout_version,
                    metrics.track_length,
                    metrics.total_time,
                ],
            )

            # Create segment metrics table
            conn.execute("""
                CREATE TABLE segment_metrics (
                    segment_id VARCHAR,
                    entry_speed DOUBLE,
                    mid_speed DOUBLE,
                    exit_speed DOUBLE,
                    min_speed DOUBLE,
                    max_speed DOUBLE,
                    segment_time DOUBLE,
                    time_delta_to_reference DOUBLE,
                    braking_distance DOUBLE,
                    max_brake_pressure DOUBLE,
                    throttle_application DOUBLE,
                    steering_smoothness DOUBLE,
                    avg_speed DOUBLE
                )
            """)

            # Insert segment metrics
            for seg in metrics.segments:
                conn.execute(
                    "INSERT INTO segment_metrics VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [
                        seg.segment_id,
                        seg.entry_speed,
                        seg.mid_speed,
                        seg.exit_speed,
                        seg.min_speed,
                        seg.max_speed,
                        seg.segment_time,
                        seg.time_delta_to_reference,
                        seg.braking_distance,
                        seg.max_brake_pressure,
                        seg.throttle_application,
                        seg.steering_smoothness,
                        seg.avg_speed,
                    ],
                )

            conn.close()
            logger.debug(f"Saved metrics cache: {cache_path}")

        except Exception as e:
            logger.error(f"Error saving metrics cache for {metrics.session_id}: {e}")
            raise

    def invalidate_lap_metrics(self, session_id: str, lap_number: int) -> bool:
        """Invalidate cached metrics for a specific lap.

        Args:
            session_id: Session identifier
            lap_number: Lap number

        Returns:
            True if cache was deleted, False if not found
        """
        cache_path = self._get_metrics_path(session_id, lap_number)

        if cache_path.exists():
            cache_path.unlink()
            logger.info(f"Invalidated metrics cache: {cache_path}")
            return True
        return False

    def invalidate_session_metrics(self, session_id: str) -> int:
        """Invalidate all metrics for a session.

        Args:
            session_id: Session identifier

        Returns:
            Number of cache files deleted
        """
        session_dir = self.metrics_dir / session_id
        if not session_dir.exists():
            return 0

        count = 0
        for cache_file in session_dir.glob("lap_*.parquet"):
            cache_file.unlink()
            count += 1

        logger.info(f"Invalidated {count} metrics caches for session {session_id}")
        return count

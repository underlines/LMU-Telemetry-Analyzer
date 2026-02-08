/**
 * Auto-generated from OpenAPI spec
 * Run `npm run generate-types` to regenerate from backend
 */

export interface Lap {
  lap_number: number;
  start_time: number;
  end_time?: number;
  lap_time?: number;
  valid: boolean;
}

export interface Session {
  id: string;
  file_path: string;
  recording_time?: string;
  session_time?: string;
  session_type?: string;
  track_name?: string;
  track_layout?: string;
  driver_name?: string;
  car_name?: string;
  car_class?: string;
  weather_conditions?: string;
  lap_count: number;
}

export interface SessionList {
  sessions: Session[];
  total: number;
}

export interface LapList {
  session_id: string;
  laps: Lap[];
  total: number;
}

export interface SessionDetail extends Session {
  channels: Array<{
    name: string;
    frequency: number;
    unit?: string;
  }>;
  events: Array<{
    name: string;
    unit?: string;
  }>;
}

export interface SignalMetadata {
  name: string;
  frequency: number;
  unit?: string;
  min_value?: number;
  max_value?: number;
}

export interface SignalSlice {
  channel: string;
  lap_number: number;
  session_id: string;
  timestamps: number[];
  normalized_time: number[];
  values: number[];
  distance?: number[];
  unit?: string;
  sampling_rate: number;
}

export interface SignalList {
  session_id: string;
  signals: SignalMetadata[];
  total: number;
}

export interface LapComparisonRequest {
  target_lap: number;
  reference_lap: number;
  channels: string[];
  normalize_time?: boolean;
  use_distance?: boolean;
  max_points?: number;
}

export interface LapComparison {
  channel: string;
  unit?: string;
  target_lap: number;
  target_timestamps: number[];
  target_values: number[];
  target_distance?: number[];
  reference_lap: number;
  reference_timestamps: number[];
  reference_values: number[];
  reference_distance?: number[];
  normalized_x: number[];
}

export interface ComparisonResponse {
  session_id: string;
  target_lap: number;
  reference_lap: number;
  comparisons: LapComparison[];
}

export interface Segment {
  segment_id: string;
  segment_type: 'corner' | 'straight' | 'complex';
  start_dist: number;
  end_dist: number;
  entry_dist?: number;
  apex_dist?: number;
  exit_dist?: number;
}

export interface TrackLayout {
  track_name: string;
  track_layout?: string;
  version: number;
  track_length: number;
  segments: Segment[];
  reference_lap_number: number;
  reference_session_id: string;
}

export interface SegmentMetrics {
  segment_id: string;
  lap_number: number;
  session_id: string;
  entry_speed?: number;
  mid_speed?: number;
  exit_speed?: number;
  min_speed?: number;
  max_speed?: number;
  segment_time: number;
  time_delta_to_reference?: number;
  braking_distance?: number;
  max_brake_pressure?: number;
  throttle_application?: number;
  steering_smoothness?: number;
  avg_speed?: number;
}

export interface LapSegmentMetrics {
  session_id: string;
  lap_number: number;
  layout_version: number;
  track_length: number;
  total_time?: number;
  segments: SegmentMetrics[];
}

export interface SegmentComparisonRequest {
  target_lap: number;
  reference_lap: number;
  segment_ids?: string[];
}

export interface SegmentComparison {
  segment_id: string;
  target_lap: number;
  reference_lap: number;
  target_time: number;
  reference_time: number;
  time_delta: number;
  target_min_speed?: number;
  reference_min_speed?: number;
  min_speed_delta?: number;
  key_differences: string[];
}

export interface SegmentComparisonResponse {
  session_id: string;
  target_lap: number;
  reference_lap: number;
  track_length: number;
  total_time_delta: number;
  comparisons: SegmentComparison[];
  largest_time_loss_segments: string[];
  largest_time_gain_segments: string[];
}

export interface ServiceCheck {
  name: string;
  status: 'healthy' | 'unhealthy' | 'degraded' | 'unknown';
  response_time_ms?: number;
  message?: string;
}

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  version: string;
  checks: ServiceCheck[];
}

export interface DependencyStatus {
  name: string;
  required: boolean;
  available: boolean;
  message?: string;
}

export interface ReadinessStatus {
  ready: boolean;
  timestamp: string;
  dependencies: DependencyStatus[];
}

export interface TelemetryStats {
  total_sessions: number;
  total_files: number;
  total_laps: number;
  cached_layouts: number;
  cache_size_mb: number;
}

export interface TelemetryMetrics {
  timestamp: string;
  stats: TelemetryStats;
}

export interface ApiError {
  detail: string;
}

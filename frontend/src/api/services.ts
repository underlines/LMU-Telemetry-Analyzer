import apiClient from './client';
import type {
  SessionList,
  SessionDetail,
  LapList,
  SignalList,
  SignalSlice,
  ComparisonResponse,
  LapComparisonRequest,
  TrackLayout,
  LapSegmentMetrics,
  SegmentComparisonResponse,
  SegmentComparisonRequest,
  HealthStatus,
  ReadinessStatus,
  TelemetryMetrics,
} from '../types/api';

export const sessionsApi = {
  listSessions: async (): Promise<SessionList> => {
    const response = await apiClient.get<SessionList>('/sessions');
    return response.data;
  },

  getSession: async (sessionId: string): Promise<SessionDetail> => {
    const response = await apiClient.get<SessionDetail>(`/sessions/${sessionId}`);
    return response.data;
  },

  getLaps: async (sessionId: string): Promise<LapList> => {
    const response = await apiClient.get<LapList>(`/sessions/${sessionId}/laps`);
    return response.data;
  },
};

export const signalsApi = {
  getSignals: async (sessionId: string): Promise<SignalList> => {
    const response = await apiClient.get<SignalList>(`/signals/sessions/${sessionId}`);
    return response.data;
  },

  getLapSignals: async (
    sessionId: string,
    lapNumber: number,
    channels: string[],
    options?: {
      normalizeTime?: boolean;
      useDistance?: boolean;
      maxPoints?: number;
    }
  ): Promise<SignalSlice[]> => {
    const params = new URLSearchParams();
    channels.forEach((ch) => params.append('channels', ch));
    if (options?.normalizeTime !== undefined) {
      params.append('normalize_time', String(options.normalizeTime));
    }
    if (options?.useDistance !== undefined) {
      params.append('use_distance', String(options.useDistance));
    }
    if (options?.maxPoints !== undefined) {
      params.append('max_points', String(options.maxPoints));
    }

    const response = await apiClient.get<SignalSlice[]>(
      `/signals/sessions/${sessionId}/laps/${lapNumber}?${params.toString()}`
    );
    return response.data;
  },

  compareLaps: async (
    sessionId: string,
    request: LapComparisonRequest
  ): Promise<ComparisonResponse> => {
    const response = await apiClient.post<ComparisonResponse>(
      `/signals/sessions/${sessionId}/compare`,
      request
    );
    return response.data;
  },
};

export const segmentsApi = {
  getTrackLayout: async (
    sessionId: string,
    forceRegenerate?: boolean
  ): Promise<TrackLayout> => {
    const params = forceRegenerate ? '?force_regenerate=true' : '';
    const response = await apiClient.get<TrackLayout>(
      `/segments/sessions/${sessionId}/layout${params}`
    );
    return response.data;
  },

  regenerateLayout: async (
    sessionId: string,
    referenceLap?: number
  ): Promise<TrackLayout> => {
    const params = referenceLap !== undefined ? `?reference_lap=${referenceLap}` : '';
    const response = await apiClient.post<TrackLayout>(
      `/segments/sessions/${sessionId}/layout/regenerate${params}`
    );
    return response.data;
  },

  getLapSegments: async (
    sessionId: string,
    lapNumber: number,
    forceRecompute?: boolean
  ): Promise<LapSegmentMetrics> => {
    const params = forceRecompute ? '?force_recompute=true' : '';
    const response = await apiClient.get<LapSegmentMetrics>(
      `/segments/sessions/${sessionId}/laps/${lapNumber}/segments${params}`
    );
    return response.data;
  },

  compareLapSegments: async (
    sessionId: string,
    request: SegmentComparisonRequest
  ): Promise<SegmentComparisonResponse> => {
    const response = await apiClient.post<SegmentComparisonResponse>(
      `/segments/sessions/${sessionId}/compare`,
      request
    );
    return response.data;
  },
};

export const healthApi = {
  getHealth: async (): Promise<HealthStatus> => {
    const response = await apiClient.get<HealthStatus>('/health', {
      baseURL: '', // Health endpoints are at root
    });
    return response.data;
  },

  getReady: async (): Promise<ReadinessStatus> => {
    const response = await apiClient.get<ReadinessStatus>('/ready', {
      baseURL: '',
    });
    return response.data;
  },

  getMetrics: async (): Promise<TelemetryMetrics> => {
    const response = await apiClient.get<TelemetryMetrics>('/metrics', {
      baseURL: '',
    });
    return response.data;
  },
};

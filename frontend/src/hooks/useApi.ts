import { useQuery, useMutation, type UseQueryOptions } from '@tanstack/react-query';
import {
  sessionsApi,
  signalsApi,
  segmentsApi,
  healthApi,
} from '../api/services';
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

const queryKeys = {
  sessions: {
    all: ['sessions'] as const,
    list: () => [...queryKeys.sessions.all, 'list'] as const,
    detail: (id: string) => [...queryKeys.sessions.all, 'detail', id] as const,
    laps: (id: string) => [...queryKeys.sessions.all, 'laps', id] as const,
  },
  signals: {
    all: ['signals'] as const,
    list: (sessionId: string) => [...queryKeys.signals.all, 'list', sessionId] as const,
    lap: (sessionId: string, lapNumber: number, channels: string[], samplingPercent?: number) =>
      [...queryKeys.signals.all, 'lap', sessionId, lapNumber, [...channels].sort().join(','), samplingPercent ?? 20] as const,
    compare: (sessionId: string, targetLap: number, referenceLap: number) =>
      [...queryKeys.signals.all, 'compare', sessionId, targetLap, referenceLap] as const,
  },
  segments: {
    all: ['segments'] as const,
    layout: (sessionId: string) => [...queryKeys.segments.all, 'layout', sessionId] as const,
    metrics: (sessionId: string, lapNumber: number) =>
      [...queryKeys.segments.all, 'metrics', sessionId, lapNumber] as const,
    compare: (sessionId: string, targetLap: number, referenceLap: number) =>
      [...queryKeys.segments.all, 'compare', sessionId, targetLap, referenceLap] as const,
  },
  health: {
    all: ['health'] as const,
    status: () => [...queryKeys.health.all, 'status'] as const,
    ready: () => [...queryKeys.health.all, 'ready'] as const,
    metrics: () => [...queryKeys.health.all, 'metrics'] as const,
  },
};

// Sessions hooks
export const useSessions = (options?: UseQueryOptions<SessionList, Error>) => {
  return useQuery<SessionList, Error>({
    queryKey: queryKeys.sessions.list(),
    queryFn: sessionsApi.listSessions,
    ...options,
  });
};

export const useSession = (
  sessionId: string,
  options?: UseQueryOptions<SessionDetail, Error>
) => {
  return useQuery<SessionDetail, Error>({
    queryKey: queryKeys.sessions.detail(sessionId),
    queryFn: () => sessionsApi.getSession(sessionId),
    enabled: !!sessionId,
    ...options,
  });
};

export const useLaps = (
  sessionId: string,
  options?: UseQueryOptions<LapList, Error>
) => {
  return useQuery<LapList, Error>({
    queryKey: queryKeys.sessions.laps(sessionId),
    queryFn: () => sessionsApi.getLaps(sessionId),
    enabled: !!sessionId,
    ...options,
  });
};

// Signals hooks
export const useSignals = (
  sessionId: string,
  options?: UseQueryOptions<SignalList, Error>
) => {
  return useQuery<SignalList, Error>({
    queryKey: queryKeys.signals.list(sessionId),
    queryFn: () => signalsApi.getSignals(sessionId),
    enabled: !!sessionId,
    ...options,
  });
};

export const useLapSignals = (
  sessionId: string,
  lapNumber: number,
  channels: string[],
  options?: {
    normalizeTime?: boolean;
    useDistance?: boolean;
    samplingPercent?: number;
  } & UseQueryOptions<SignalSlice[], Error>
) => {
  const { normalizeTime, useDistance, samplingPercent, ...queryOptions } = options || {};

  return useQuery<SignalSlice[], Error>({
    queryKey: queryKeys.signals.lap(sessionId, lapNumber, channels, samplingPercent),
    queryFn: () =>
      signalsApi.getLapSignals(sessionId, lapNumber, channels, {
        normalizeTime,
        useDistance,
        samplingPercent,
      }),
    enabled: !!sessionId && !!channels.length,
    ...queryOptions,
  });
};

export const useCompareLaps = (
  sessionId: string,
  request: LapComparisonRequest,
  options?: UseQueryOptions<ComparisonResponse, Error>
) => {
  return useQuery<ComparisonResponse, Error>({
    queryKey: queryKeys.signals.compare(sessionId, request.target_lap, request.reference_lap),
    queryFn: () => signalsApi.compareLaps(sessionId, request),
    enabled: !!sessionId && !!request.channels.length,
    ...options,
  });
};

// Segments hooks
export const useTrackLayout = (
  sessionId: string,
  options?: { forceRegenerate?: boolean } & UseQueryOptions<TrackLayout, Error>
) => {
  const { forceRegenerate, ...queryOptions } = options || {};

  return useQuery<TrackLayout, Error>({
    queryKey: queryKeys.segments.layout(sessionId),
    queryFn: () => segmentsApi.getTrackLayout(sessionId, forceRegenerate),
    enabled: !!sessionId,
    ...queryOptions,
  });
};

export const useRegenerateLayout = () => {
  return useMutation({
    mutationFn: ({
      sessionId,
      referenceLap,
    }: {
      sessionId: string;
      referenceLap?: number;
    }) => segmentsApi.regenerateLayout(sessionId, referenceLap),
  });
};

export const useLapSegments = (
  sessionId: string,
  lapNumber: number,
  options?: { forceRecompute?: boolean } & UseQueryOptions<LapSegmentMetrics, Error>
) => {
  const { forceRecompute, ...queryOptions } = options || {};

  return useQuery<LapSegmentMetrics, Error>({
    queryKey: queryKeys.segments.metrics(sessionId, lapNumber),
    queryFn: () => segmentsApi.getLapSegments(sessionId, lapNumber, forceRecompute),
    enabled: !!sessionId && lapNumber >= 0,
    ...queryOptions,
  });
};

export const useCompareSegments = (
  sessionId: string,
  request: SegmentComparisonRequest,
  options?: UseQueryOptions<SegmentComparisonResponse, Error>
) => {
  return useQuery<SegmentComparisonResponse, Error>({
    queryKey: queryKeys.segments.compare(sessionId, request.target_lap, request.reference_lap),
    queryFn: () => segmentsApi.compareLapSegments(sessionId, request),
    enabled: !!sessionId,
    ...options,
  });
};

// Health hooks
export const useHealth = (options?: UseQueryOptions<HealthStatus, Error>) => {
  return useQuery<HealthStatus, Error>({
    queryKey: queryKeys.health.status(),
    queryFn: healthApi.getHealth,
    refetchInterval: 30000, // Refetch every 30 seconds
    ...options,
  });
};

export const useReady = (options?: UseQueryOptions<ReadinessStatus, Error>) => {
  return useQuery<ReadinessStatus, Error>({
    queryKey: queryKeys.health.ready(),
    queryFn: healthApi.getReady,
    ...options,
  });
};

export const useMetrics = (options?: UseQueryOptions<TelemetryMetrics, Error>) => {
  return useQuery<TelemetryMetrics, Error>({
    queryKey: queryKeys.health.metrics(),
    queryFn: healthApi.getMetrics,
    refetchInterval: 60000, // Refetch every minute
    ...options,
  });
};

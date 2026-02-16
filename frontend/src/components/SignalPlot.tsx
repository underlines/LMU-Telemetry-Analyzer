import { useEffect, useMemo, useRef, useState } from 'react';
import { Box, Paper, Typography, FormControl, InputLabel, Select, MenuItem, Alert, Chip } from '@mui/material';
import * as echarts from 'echarts';
import type { ECharts, EChartsOption } from 'echarts';
import { useSignals, useLapSignals } from '../hooks/useApi';

interface SignalPlotProps {
  sessionId: string;
  lapNumber: number;
}

// Sampling percentage options
const SAMPLING_OPTIONS = [1, 5, 20, 50, 80, 95, 100];

export default function SignalPlot({ sessionId, lapNumber }: SignalPlotProps): JSX.Element {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstanceRef = useRef<ECharts | null>(null);
  const [selectedChannels, setSelectedChannels] = useState<string[]>([]);
  const [useDistance, setUseDistance] = useState(false);
  const [samplingPercent, setSamplingPercent] = useState(20);

  const { data: signalsList } = useSignals(sessionId);

  // Compute default channels from available signals
  const defaultChannels = useMemo(() => {
    if (signalsList?.signals && signalsList.signals.length > 0) {
      return signalsList.signals.slice(0, 3).map((s) => s.name);
    }
    return [];
  }, [signalsList]);

  // Use selected channels if user has made a selection, otherwise use defaults
  const channelsToFetch = selectedChannels.length > 0 ? selectedChannels : defaultChannels;

  const { data: signalData, isLoading, isFetching } = useLapSignals(
    sessionId,
    lapNumber,
    channelsToFetch,
    { normalizeTime: true, useDistance, samplingPercent }
  );

  // Initialize chart once on mount
  useEffect(() => {
    if (chartRef.current && !chartInstanceRef.current) {
      try {
        chartInstanceRef.current = echarts.init(chartRef.current);
        // Force initial resize to get proper dimensions
        setTimeout(() => {
          chartInstanceRef.current?.resize();
        }, 100);
      } catch (e) {
        console.error('Failed to initialize ECharts:', e);
      }
    }

    return () => {
      if (chartInstanceRef.current) {
        chartInstanceRef.current.dispose();
        chartInstanceRef.current = null;
      }
    };
  }, []);

  // Update chart when data changes
  useEffect(() => {
    if (!chartInstanceRef.current) return;

    if (!signalData || signalData.length === 0) {
      // Clear chart when no data
      chartInstanceRef.current.clear();
      return;
    }

    // Resize before setting options to ensure proper dimensions
    chartInstanceRef.current.resize();

    const series = signalData.map((slice) => ({
      name: slice.channel,
      type: 'line',
      smooth: true,
      symbol: 'none',
      data: slice.values.map((value, index) => [
        useDistance
          ? (slice.distance?.[index] ?? slice.normalized_time[index])
          : slice.normalized_time[index],
        value,
      ]),
    }));

    const option: EChartsOption = {
      title: {
        text: `Lap ${lapNumber} Signals`,
        left: 'center',
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
        },
      },
      legend: {
        data: signalData.map((s) => s.channel),
        top: 30,
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true,
      },
      xAxis: {
        type: 'value',
        name: useDistance ? 'Distance (m)' : 'Time (s)',
        nameLocation: 'middle',
        nameGap: 30,
      },
      yAxis: {
        type: 'value',
        name: 'Value',
      },
      series,
      dataZoom: [
        {
          type: 'inside',
          start: 0,
          end: 100,
        },
        {
          start: 0,
          end: 100,
        },
      ],
    };

    chartInstanceRef.current.setOption(option, true);
  }, [signalData, lapNumber, useDistance]);

  // Handle window resize
  useEffect(() => {
    const handleResize = (): void => {
      chartInstanceRef.current?.resize();
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const availableChannels = signalsList?.signals.map((s) => s.name) || [];
  const hasData = signalData && signalData.length > 0;
  const showInitialPrompt = channelsToFetch.length === 0;

  // Calculate sampling info from the highest-count channel
  const samplingInfo = useMemo(() => {
    if (!signalData || signalData.length === 0) {
      return { maxTotal: 0, currentSamples: 0 };
    }
    const maxTotal = Math.max(...signalData.map((s) => s.total_samples));
    // Get samples from the channel with max total_samples
    const maxChannel = signalData.find((s) => s.total_samples === maxTotal);
    return { maxTotal, currentSamples: maxChannel?.values.length ?? 0 };
  }, [signalData]);

  return (
    <Box>
      <Box display="flex" gap={2} mb={2} flexWrap="wrap">
        <FormControl sx={{ minWidth: 200 }}>
          <InputLabel id="channels-label">Channels</InputLabel>
          <Select
            labelId="channels-label"
            multiple
            value={selectedChannels}
            label="Channels"
            onChange={(e) => setSelectedChannels(typeof e.target.value === 'string' ? e.target.value.split(',') : e.target.value)}
            renderValue={(selected) => (
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                {(selected as string[]).map((value) => (
                  <Chip key={value} label={value} size="small" />
                ))}
              </Box>
            )}
          >
            {availableChannels.map((channel) => (
              <MenuItem key={channel} value={channel}>
                {channel}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <FormControl sx={{ minWidth: 150 }}>
          <InputLabel id="axis-label">X-Axis</InputLabel>
          <Select
            labelId="axis-label"
            value={useDistance ? 'distance' : 'time'}
            label="X-Axis"
            onChange={(e) => setUseDistance(e.target.value === 'distance')}
          >
            <MenuItem value="time">Time (seconds)</MenuItem>
            <MenuItem value="distance">Distance (meters)</MenuItem>
          </Select>
        </FormControl>

        <FormControl sx={{ minWidth: 150 }}>
          <InputLabel id="sampling-label">Sampling</InputLabel>
          <Select
            labelId="sampling-label"
            value={samplingPercent}
            label="Sampling"
            onChange={(e) => setSamplingPercent(Number(e.target.value))}
          >
            {SAMPLING_OPTIONS.map((percent) => (
              <MenuItem key={percent} value={percent}>
                {percent}%
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      <Paper elevation={2} sx={{ position: 'relative' }}>
        {/* Sampling info label */}
        {hasData && (
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{
              position: 'absolute',
              top: 8,
              right: 16,
              zIndex: 1,
              backgroundColor: 'background.paper',
              px: 1,
              borderRadius: 1,
            }}
          >
            Sampling: {samplingPercent}% ({samplingInfo.currentSamples.toLocaleString()} of {samplingInfo.maxTotal.toLocaleString()} samples)
          </Typography>
        )}
        {/* Chart container - always rendered */}
        <Box
          ref={chartRef}
          sx={{
            width: '100%',
            height: 500,
            display: hasData ? 'block' : 'none',
          }}
        />

        {/* Overlay for loading/no data states */}
        {!hasData && (
          <Box
            sx={{
              width: '100%',
              height: 500,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              p: 3,
            }}
          >
            {showInitialPrompt ? (
              <Alert severity="info">
                Select channels from the dropdown above to view signal plots.
              </Alert>
            ) : isLoading || isFetching ? (
              <Alert severity="info">Loading signal data...</Alert>
            ) : (
              <Alert severity="warning">
                No data available for selected channels. The channels may not exist in this session.
              </Alert>
            )}
          </Box>
        )}
      </Paper>

      <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
        Tip: Scroll to zoom, drag to pan. Click legend to toggle channels.
      </Typography>
    </Box>
  );
}

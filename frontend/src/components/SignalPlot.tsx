import { useEffect, useRef, useState } from 'react';
import { Box, Paper, Typography, FormControl, InputLabel, Select, MenuItem, Alert, Chip } from '@mui/material';
import * as echarts from 'echarts';
import { useSignals, useLapSignals } from '../hooks/useApi';

interface SignalPlotProps {
  sessionId: string;
  lapNumber: number;
}

export default function SignalPlot({ sessionId, lapNumber }: SignalPlotProps): JSX.Element {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstanceRef = useRef<echarts.ECharts | null>(null);
  const [selectedChannels, setSelectedChannels] = useState<string[]>(['Speed', 'Throttle', 'Brake']);
  const [useDistance, setUseDistance] = useState(false);

  const { data: signalsList } = useSignals(sessionId);
  const { data: signalData, isLoading } = useLapSignals(
    sessionId,
    lapNumber,
    selectedChannels,
    { normalizeTime: true, useDistance }
  );

  // Initialize chart
  useEffect(() => {
    if (chartRef.current && !chartInstanceRef.current) {
      chartInstanceRef.current = echarts.init(chartRef.current);
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
    if (!chartInstanceRef.current || !signalData) return;

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

    const option: echarts.EChartsOption = {
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
      </Box>

      {isLoading ? (
        <Alert severity="info">Loading signal data...</Alert>
      ) : (
        <Paper elevation={2}>
          <Box ref={chartRef} sx={{ width: '100%', height: 500 }} />
        </Paper>
      )}

      <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
        Tip: Scroll to zoom, drag to pan. Click legend to toggle channels.
      </Typography>
    </Box>
  );
}

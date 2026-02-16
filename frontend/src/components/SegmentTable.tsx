import { Box, Paper, Typography, Alert } from '@mui/material';
import { DataGrid, type GridColDef } from '@mui/x-data-grid';
import type { LapSegmentMetrics, TrackLayout, SegmentMetrics } from '../types/api';

interface SegmentTableProps {
  segments?: LapSegmentMetrics;
  layout?: TrackLayout;
}

const columns: GridColDef<SegmentMetrics>[] = [
  {
    field: 'segment_id',
    headerName: 'Segment',
    width: 100,
  },
  {
    field: 'segment_type',
    headerName: 'Type',
    width: 100,
    valueGetter: (_value: string | undefined, row: SegmentMetrics) => {
      // Get segment type from layout
      return 'Corner'; // Placeholder
    },
  },
  {
    field: 'segment_time',
    headerName: 'Time (s)',
    width: 100,
    type: 'number',
    valueFormatter: (value: number | undefined) =>
      value !== undefined ? value.toFixed(3) : '-',
  },
  {
    field: 'time_delta_to_reference',
    headerName: 'Delta (s)',
    width: 100,
    type: 'number',
    cellClassName: (params) => {
      if (params.value === undefined || params.value === null) return '';
      return params.value > 0 ? 'text-negative' : 'text-positive';
    },
    valueFormatter: (value: number | undefined) =>
      value !== undefined ? (value > 0 ? `+${value.toFixed(3)}` : value.toFixed(3)) : '-',
  },
  {
    field: 'min_speed',
    headerName: 'Min Speed',
    width: 100,
    type: 'number',
    valueFormatter: (value: number | undefined) =>
      value !== undefined ? `${value.toFixed(1)} m/s` : '-',
  },
  {
    field: 'max_speed',
    headerName: 'Max Speed',
    width: 100,
    type: 'number',
    valueFormatter: (value: number | undefined) =>
      value !== undefined ? `${value.toFixed(1)} m/s` : '-',
  },
  {
    field: 'avg_speed',
    headerName: 'Avg Speed',
    width: 100,
    type: 'number',
    valueFormatter: (value: number | undefined) =>
      value !== undefined ? `${value.toFixed(1)} m/s` : '-',
  },
  {
    field: 'braking_distance',
    headerName: 'Braking (m)',
    width: 100,
    type: 'number',
    valueFormatter: (value: number | null | undefined) =>
      value !== undefined && value !== null ? value.toFixed(1) : '-',
  },
  {
    field: 'throttle_application',
    headerName: 'Throttle (m)',
    width: 110,
    type: 'number',
    valueFormatter: (value: number | null | undefined) =>
      value !== undefined && value !== null ? value.toFixed(1) : '-',
  },
  {
    field: 'steering_smoothness',
    headerName: 'Smoothness',
    width: 100,
    type: 'number',
    valueFormatter: (value: number | null | undefined) =>
      value !== undefined && value !== null ? value.toFixed(3) : '-',
  },
];

export default function SegmentTable({ segments, layout }: SegmentTableProps): JSX.Element {
  if (!segments || !layout) {
    return (
      <Alert severity="info">
        No segment data available. Layout may still be processing.
      </Alert>
    );
  }

  // Add segment type info to rows
  const rows = segments.segments.map((seg) => {
    const segmentDef = layout.segments.find((s) => s.segment_id === seg.segment_id);
    return {
      ...seg,
      segment_type: segmentDef?.segment_type || 'unknown',
    };
  });

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Track Segments
      </Typography>

      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Track: {layout.track_name} ({layout.track_length.toFixed(0)}m) • Layout v
        {layout.version}
      </Typography>

      <Paper>
        <DataGrid
          rows={rows}
          columns={columns}
          pageSizeOptions={[10, 25, 50]}
          initialState={{
            pagination: { paginationModel: { pageSize: 25 } },
          }}
          disableRowSelectionOnClick
          getRowId={(row) => row.segment_id}
          sx={{
            '& .text-positive': {
              color: 'success.main',
            },
            '& .text-negative': {
              color: 'error.main',
            },
          }}
        />
      </Paper>

      <Box sx={{ mt: 2 }}>
        <Typography variant="caption" color="text.secondary">
          Reference Lap: {layout.reference_lap_number} • Total Lap Time:{' '}
          {segments.total_time?.toFixed(3)}s
        </Typography>
      </Box>
    </Box>
  );
}

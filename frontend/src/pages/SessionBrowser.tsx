import { Box, Container, Typography, Paper, Chip, Alert, CircularProgress } from '@mui/material';
import { DataGrid, GridColDef } from '@mui/x-data-grid';
import { useSessions } from '../hooks/useApi';
import { useNavigate } from 'react-router-dom';
import type { Session } from '../types/api';

const columns: GridColDef<Session>[] = [
  { field: 'id', headerName: 'Session ID', width: 250 },
  { field: 'track_name', headerName: 'Track', width: 200 },
  { field: 'car_name', headerName: 'Car', width: 200 },
  { field: 'driver_name', headerName: 'Driver', width: 150 },
  { field: 'session_type', headerName: 'Type', width: 120 },
  {
    field: 'lap_count',
    headerName: 'Laps',
    width: 80,
    type: 'number',
  },
  {
    field: 'recording_time',
    headerName: 'Recorded',
    width: 180,
    valueGetter: (value: string | undefined) =>
      value ? new Date(value).toLocaleString() : 'Unknown',
  },
];

export default function SessionBrowser(): JSX.Element {
  const { data, isLoading, error } = useSessions();
  const navigate = useNavigate();

  const handleRowClick = (params: { id: string | number }): void => {
    navigate(`/sessions/${params.id}`);
  };

  return (
    <Container maxWidth="xl" sx={{ mt: 4 }}>
      <Typography variant="h4" gutterBottom>
        Telemetry Sessions
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error.message}
        </Alert>
      )}

      <Paper sx={{ height: 600, width: '100%' }}>
        {isLoading ? (
          <Box
            display="flex"
            justifyContent="center"
            alignItems="center"
            height="100%"
          >
            <CircularProgress />
          </Box>
        ) : (
          <DataGrid
            rows={data?.sessions || []}
            columns={columns}
            onRowClick={handleRowClick}
            pageSizeOptions={[10, 25, 50]}
            initialState={{
              pagination: { paginationModel: { pageSize: 10 } },
            }}
            disableRowSelectionOnClick
            sx={{ cursor: 'pointer' }}
          />
        )}
      </Paper>

      <Box sx={{ mt: 2 }}>
        <Chip
          label={`${data?.total || 0} sessions found`}
          color="primary"
          variant="outlined"
        />
      </Box>
    </Container>
  );
}

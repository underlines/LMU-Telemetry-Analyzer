import { Box, Container, Typography, Paper, Alert } from '@mui/material';
import { useHealth, useMetrics } from '../hooks/useApi';

export default function Dashboard(): JSX.Element {
  const { data: health, isLoading: healthLoading } = useHealth();
  const { data: metrics, isLoading: metricsLoading } = useMetrics();

  return (
    <Container maxWidth="xl" sx={{ mt: 4 }}>
      <Typography variant="h4" gutterBottom>
        LMU Telemetry Analyzer
      </Typography>

      <Typography variant="body1" color="text.secondary" paragraph>
        Local-first telemetry analysis tool for Le Mans Ultimate racing game.
      </Typography>

      <Box sx={{ mt: 4 }}>
        <Typography variant="h5" gutterBottom>
          System Status
        </Typography>

        {healthLoading ? (
          <Alert severity="info">Loading health status...</Alert>
        ) : health?.status === 'healthy' ? (
          <Alert severity="success">
            Backend is healthy (v{health.version})
          </Alert>
        ) : (
          <Alert severity="warning">
            Backend status: {health?.status}
          </Alert>
        )}
      </Box>

      <Box sx={{ mt: 4 }}>
        <Typography variant="h5" gutterBottom>
          Telemetry Statistics
        </Typography>

        {metricsLoading ? (
          <Alert severity="info">Loading metrics...</Alert>
        ) : metrics ? (
          <Paper sx={{ p: 3 }}>
            <Box display="grid" gridTemplateColumns="repeat(auto-fit, minmax(200px, 1fr))" gap={3}>
              <Box>
                <Typography variant="h3" color="primary">
                  {metrics.stats.total_sessions}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Sessions
                </Typography>
              </Box>
              <Box>
                <Typography variant="h3" color="primary">
                  {metrics.stats.total_laps}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Total Laps
                </Typography>
              </Box>
              <Box>
                <Typography variant="h3" color="primary">
                  {metrics.stats.cached_layouts}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Cached Layouts
                </Typography>
              </Box>
              <Box>
                <Typography variant="h3" color="primary">
                  {metrics.stats.cache_size_mb.toFixed(2)} MB
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Cache Size
                </Typography>
              </Box>
            </Box>
          </Paper>
        ) : null}
      </Box>

      <Box sx={{ mt: 4 }}>
        <Typography variant="h5" gutterBottom>
          Quick Actions
        </Typography>
        <Box display="flex" gap={2} flexWrap="wrap">
          <Paper
            component="a"
            href="/sessions"
            sx={{
              p: 3,
              textDecoration: 'none',
              color: 'inherit',
              cursor: 'pointer',
              '&:hover': { bgcolor: 'action.hover' },
            }}
          >
            <Typography variant="h6">Browse Sessions</Typography>
            <Typography variant="body2" color="text.secondary">
              View and analyze telemetry recordings
            </Typography>
          </Paper>

          <Paper
            component="a"
            href="/docs"
            target="_blank"
            sx={{
              p: 3,
              textDecoration: 'none',
              color: 'inherit',
              cursor: 'pointer',
              '&:hover': { bgcolor: 'action.hover' },
            }}
          >
            <Typography variant="h6">API Documentation</Typography>
            <Typography variant="body2" color="text.secondary">
              View Swagger/OpenAPI docs
            </Typography>
          </Paper>
        </Box>
      </Box>
    </Container>
  );
}

import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Container,
  Typography,
  Paper,
  Grid,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Chip,
  Divider,
  Button,
  Alert,
  CircularProgress,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { useSession, useLaps } from '../hooks/useApi';

export default function SessionDetail(): JSX.Element {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();

  const {
    data: session,
    isLoading: sessionLoading,
    error: sessionError,
  } = useSession(sessionId || '');

  const {
    data: lapsData,
    isLoading: lapsLoading,
    error: lapsError,
  } = useLaps(sessionId || '');

  const handleLapClick = (lapNumber: number): void => {
    navigate(`/sessions/${sessionId}/laps/${lapNumber}`);
  };

  const handleBack = (): void => {
    navigate('/');
  };

  if (sessionLoading || lapsLoading) {
    return (
      <Container maxWidth="xl" sx={{ mt: 4 }}>
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
          <CircularProgress />
        </Box>
      </Container>
    );
  }

  if (sessionError || lapsError) {
    return (
      <Container maxWidth="xl" sx={{ mt: 4 }}>
        <Alert severity="error">
          {sessionError?.message || lapsError?.message}
        </Alert>
        <Button startIcon={<ArrowBackIcon />} onClick={handleBack} sx={{ mt: 2 }}>
          Back to Sessions
        </Button>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ mt: 4 }}>
      <Button startIcon={<ArrowBackIcon />} onClick={handleBack} sx={{ mb: 2 }}>
        Back to Sessions
      </Button>

      <Typography variant="h4" gutterBottom>
        Session: {session?.id}
      </Typography>

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, md: 4 }}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Session Info
            </Typography>
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="text.secondary">
                Track
              </Typography>
              <Typography variant="body1">
                {session?.track_name || 'Unknown'}
                {session?.track_layout ? ` (${session.track_layout})` : ''}
              </Typography>
            </Box>
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="text.secondary">
                Car
              </Typography>
              <Typography variant="body1">
                {session?.car_name || 'Unknown'}
                {session?.car_class ? ` - ${session.car_class}` : ''}
              </Typography>
            </Box>
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="text.secondary">
                Driver
              </Typography>
              <Typography variant="body1">{session?.driver_name || 'Unknown'}</Typography>
            </Box>
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="text.secondary">
                Session Type
              </Typography>
              <Typography variant="body1">{session?.session_type || 'Unknown'}</Typography>
            </Box>
            <Box>
              <Typography variant="body2" color="text.secondary">
                Recorded
              </Typography>
              <Typography variant="body1">
                {session?.recording_time
                  ? new Date(session.recording_time).toLocaleString()
                  : 'Unknown'}
              </Typography>
            </Box>
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, md: 4 }}>
          <Paper sx={{ p: 2, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              Available Channels ({session?.channels?.length || 0})
            </Typography>
            <Box sx={{ maxHeight: 400, overflow: 'auto' }}>
              {session?.channels?.map((channel) => (
                <Chip
                  key={channel.name}
                  label={`${channel.name} (${channel.unit || '-'})`}
                  size="small"
                  sx={{ m: 0.5 }}
                />
              ))}
            </Box>
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, md: 4 }}>
          <Paper sx={{ p: 0 }}>
            <Typography variant="h6" sx={{ p: 2, pb: 1 }}>
              Laps ({lapsData?.total || 0})
            </Typography>
            <Divider />
            <List sx={{ maxHeight: 400, overflow: 'auto' }}>
              {lapsData?.laps.map((lap) => (
                <ListItem key={lap.lap_number} disablePadding>
                  <ListItemButton onClick={() => handleLapClick(lap.lap_number)}>
                    <ListItemText
                      primary={`Lap ${lap.lap_number}`}
                      secondary={
                        lap.lap_time
                          ? `Time: ${lap.lap_time.toFixed(3)}s ${lap.valid ? '' : '(Invalid)'}`
                          : 'In progress'
                      }
                    />
                    {!lap.valid && <Chip label="Invalid" size="small" color="warning" />}
                  </ListItemButton>
                </ListItem>
              ))}
            </List>
          </Paper>
        </Grid>
      </Grid>
    </Container>
  );
}

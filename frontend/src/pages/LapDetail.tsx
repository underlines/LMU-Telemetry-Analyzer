import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Container,
  Typography,
  Paper,
  Button,
  Alert,
  CircularProgress,
  Tabs,
  Tab,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { useState } from 'react';
import { useSession, useLapSegments, useTrackLayout } from '../hooks/useApi';
import SignalPlot from '../components/SignalPlot';
import SegmentTable from '../components/SegmentTable';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps): JSX.Element {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`lap-tabpanel-${index}`}
      aria-labelledby={`lap-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

export default function LapDetail(): JSX.Element {
  const { sessionId, lapNumber } = useParams<{ sessionId: string; lapNumber: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState(0);

  const lapNum = parseInt(lapNumber || '0', 10);

  const { data: session } = useSession(sessionId || '');
  const {
    data: segments,
    isLoading: segmentsLoading,
    error: segmentsError,
  } = useLapSegments(sessionId || '', lapNum);
  const {
    data: layout,
    isLoading: layoutLoading,
    error: layoutError,
  } = useTrackLayout(sessionId || '');

  const handleBack = (): void => {
    navigate(`/sessions/${sessionId}`);
  };

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number): void => {
    setActiveTab(newValue);
  };

  // Helper to format error messages
  const getErrorMessage = (error: Error | null): string => {
    if (!error) return 'Unknown error';
    return error.message || 'An unexpected error occurred';
  };

  return (
    <Container maxWidth="xl" sx={{ mt: 4 }}>
      <Button startIcon={<ArrowBackIcon />} onClick={handleBack} sx={{ mb: 2 }}>
        Back to Session
      </Button>

      <Typography variant="h4" gutterBottom>
        Session: {sessionId} - Lap {lapNum}
      </Typography>

      <Typography variant="subtitle1" color="text.secondary" gutterBottom>
        {session?.track_name} • {session?.car_name}
      </Typography>

      <Paper sx={{ mt: 3 }}>
        <Tabs
          value={activeTab}
          onChange={handleTabChange}
          aria-label="lap analysis tabs"
        >
          <Tab label="Signals" />
          <Tab label="Segments" />
          <Tab label="Comparison" />
        </Tabs>

        <TabPanel value={activeTab} index={0}>
          <SignalPlot sessionId={sessionId || ''} lapNumber={lapNum} />
        </TabPanel>

        <TabPanel value={activeTab} index={1}>
          {segmentsLoading || layoutLoading ? (
            <Box display="flex" justifyContent="center" p={4}>
              <CircularProgress />
            </Box>
          ) : segmentsError || layoutError ? (
            <Box p={4}>
              <Alert severity="error" sx={{ mb: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Error Loading Segment Data
                </Typography>
                {segmentsError && (
                  <Typography variant="body2">
                    Segments: {getErrorMessage(segmentsError)}
                  </Typography>
                )}
                {layoutError && (
                  <Typography variant="body2">
                    Layout: {getErrorMessage(layoutError)}
                  </Typography>
                )}
              </Alert>
            </Box>
          ) : (
            <SegmentTable segments={segments} layout={layout} />
          )}
        </TabPanel>

        <TabPanel value={activeTab} index={2}>
          <Box p={4}>
            <Alert severity="info">
              Lap comparison feature coming in Step 4c. Select a reference lap to compare.
            </Alert>
          </Box>
        </TabPanel>
      </Paper>
    </Container>
  );
}

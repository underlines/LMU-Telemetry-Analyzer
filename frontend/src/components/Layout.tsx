import { AppBar, Toolbar, Typography, Container, Box } from '@mui/material';
import { Link as RouterLink, Outlet } from 'react-router-dom';
import { Link } from '@mui/material';
import SpeedIcon from '@mui/icons-material/Speed';

export default function Layout(): JSX.Element {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <AppBar position="static" elevation={1}>
        <Toolbar>
          <SpeedIcon sx={{ mr: 2 }} />
          <Typography
            variant="h6"
            component={RouterLink}
            to="/"
            sx={{
              flexGrow: 1,
              textDecoration: 'none',
              color: 'inherit',
            }}
          >
            LMU Telemetry Analyzer
          </Typography>
          <Box sx={{ display: 'flex', gap: 2 }}>
            <Link
              component={RouterLink}
              to="/sessions"
              color="inherit"
              underline="hover"
            >
              Sessions
            </Link>
            <Link
              component={RouterLink}
              to="/docs"
              color="inherit"
              underline="hover"
              target="_blank"
            >
              API Docs
            </Link>
          </Box>
        </Toolbar>
      </AppBar>

      <Box component="main" sx={{ flexGrow: 1, py: 3 }}>
        <Outlet />
      </Box>

      <Box
        component="footer"
        sx={{
          py: 3,
          px: 2,
          mt: 'auto',
          backgroundColor: 'background.paper',
          borderTop: 1,
          borderColor: 'divider',
        }}
      >
        <Container maxWidth="xl">
          <Typography variant="body2" color="text.secondary" align="center">
            LMU Telemetry Analyzer v0.1.0 • Local-first telemetry analysis tool
          </Typography>
        </Container>
      </Box>
    </Box>
  );
}

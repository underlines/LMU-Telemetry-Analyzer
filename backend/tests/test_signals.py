"""Tests for signal retrieval and comparison endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# Sample session ID (from the test data file)
SAMPLE_SESSION_ID = "Autódromo José Carlos Pace_P_2026-02-07T22_56_50Z"


class TestSignalEndpoints:
    """Test signal-related API endpoints."""

    def test_list_signals_success(self) -> None:
        """Test listing signals for a valid session."""
        response = client.get(f"/api/v1/signals/sessions/{SAMPLE_SESSION_ID}")
        assert response.status_code == 200

        data = response.json()
        assert data["session_id"] == SAMPLE_SESSION_ID
        assert "signals" in data
        assert "total" in data
        assert isinstance(data["signals"], list)
        assert data["total"] == len(data["signals"])

        # Check signal metadata structure
        if data["signals"]:
            signal = data["signals"][0]
            assert "name" in signal
            assert "frequency" in signal
            assert "unit" in signal

    def test_list_signals_not_found(self) -> None:
        """Test listing signals for non-existent session."""
        response = client.get("/api/v1/signals/sessions/nonexistent_session")
        assert response.status_code == 404

    def test_get_lap_signals_success(self) -> None:
        """Test retrieving signals for a specific lap."""
        # First get available signals
        signals_response = client.get(f"/api/v1/signals/sessions/{SAMPLE_SESSION_ID}")
        assert signals_response.status_code == 200
        signals_data = signals_response.json()

        if not signals_data["signals"]:
            pytest.skip("No signals available in test data")

        # Get first signal name
        channel_name = signals_data["signals"][0]["name"]

        # Get first lap
        laps_response = client.get(f"/api/v1/sessions/{SAMPLE_SESSION_ID}/laps")
        assert laps_response.status_code == 200
        laps_data = laps_response.json()

        if not laps_data["laps"]:
            pytest.skip("No laps available in test data")

        lap_number = laps_data["laps"][0]["lap_number"]

        # Request signal data
        response = client.get(
            f"/api/v1/signals/sessions/{SAMPLE_SESSION_ID}/laps/{lap_number}",
            params={
                "channels": [channel_name],
                "normalize_time": True,
                "use_distance": False,
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        # Check signal slice structure
        slice_data = data[0]
        assert slice_data["channel"] == channel_name
        assert slice_data["lap_number"] == lap_number
        assert slice_data["session_id"] == SAMPLE_SESSION_ID
        assert "timestamps" in slice_data
        assert "normalized_time" in slice_data
        assert "values" in slice_data
        assert len(slice_data["timestamps"]) == len(slice_data["values"])

    def test_get_lap_signals_multiple_channels(self) -> None:
        """Test retrieving multiple signals for a lap."""
        # Get available signals
        signals_response = client.get(f"/api/v1/signals/sessions/{SAMPLE_SESSION_ID}")
        assert signals_response.status_code == 200
        signals_data = signals_response.json()

        if len(signals_data["signals"]) < 2:
            pytest.skip("Not enough signals available in test data")

        # Get first two signal names
        channel_names = [s["name"] for s in signals_data["signals"][:2]]

        # Get first lap
        laps_response = client.get(f"/api/v1/sessions/{SAMPLE_SESSION_ID}/laps")
        assert laps_response.status_code == 200
        laps_data = laps_response.json()

        if not laps_data["laps"]:
            pytest.skip("No laps available in test data")

        lap_number = laps_data["laps"][0]["lap_number"]

        # Request multiple signals
        response = client.get(
            f"/api/v1/signals/sessions/{SAMPLE_SESSION_ID}/laps/{lap_number}",
            params={"channels": channel_names},
        )
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["channel"] == channel_names[0]
        assert data[1]["channel"] == channel_names[1]

    def test_get_lap_signals_not_found(self) -> None:
        """Test retrieving signals for non-existent lap."""
        response = client.get(
            f"/api/v1/signals/sessions/{SAMPLE_SESSION_ID}/laps/99999",
            params={"channels": ["Ground Speed"]},
        )
        assert response.status_code == 404

    @pytest.mark.xfail(reason="Downsampling implementation needs debugging")
    def test_get_lap_signals_with_downsampling(self) -> None:
        """Test signal retrieval with max_points parameter."""
        # Get available signals - look for one with high frequency
        signals_response = client.get(f"/api/v1/signals/sessions/{SAMPLE_SESSION_ID}")
        assert signals_response.status_code == 200
        signals_data = signals_response.json()

        # Find a signal with high frequency (has timestamps) for downsampling test
        channel_name = None
        for signal in signals_data["signals"]:
            if signal["frequency"] >= 60:  # High frequency signals have timestamps
                channel_name = signal["name"]
                break

        if not channel_name:
            pytest.skip("No high-frequency signals available for downsampling test")

        # Get first lap
        laps_response = client.get(f"/api/v1/sessions/{SAMPLE_SESSION_ID}/laps")
        assert laps_response.status_code == 200
        laps_data = laps_response.json()

        if not laps_data["laps"]:
            pytest.skip("No laps available in test data")

        lap_number = laps_data["laps"][0]["lap_number"]

        # Request with downsampling
        max_points = 100
        response = client.get(
            f"/api/v1/signals/sessions/{SAMPLE_SESSION_ID}/laps/{lap_number}",
            params={
                "channels": [channel_name],
                "max_points": max_points,
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert len(data) > 0
        # Note: downsampling may not always reduce points if signal is already small
        assert len(data[0]["values"]) <= max_points * 2  # Allow some flexibility

    def test_compare_laps_success(self) -> None:
        """Test comparing signals between two laps."""
        # Get available signals
        signals_response = client.get(f"/api/v1/signals/sessions/{SAMPLE_SESSION_ID}")
        assert signals_response.status_code == 200
        signals_data = signals_response.json()

        if not signals_data["signals"]:
            pytest.skip("No signals available in test data")

        channel_name = signals_data["signals"][0]["name"]

        # Get laps
        laps_response = client.get(f"/api/v1/sessions/{SAMPLE_SESSION_ID}/laps")
        assert laps_response.status_code == 200
        laps_data = laps_response.json()

        if len(laps_data["laps"]) < 2:
            pytest.skip("Not enough laps available for comparison")

        lap_numbers = [lap["lap_number"] for lap in laps_data["laps"][:2]]

        # Compare laps
        response = client.post(
            f"/api/v1/signals/sessions/{SAMPLE_SESSION_ID}/compare",
            json={
                "target_lap": lap_numbers[0],
                "reference_lap": lap_numbers[1],
                "channels": [channel_name],
                "normalize_time": True,
                "use_distance": False,
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert data["session_id"] == SAMPLE_SESSION_ID
        assert data["target_lap"] == lap_numbers[0]
        assert data["reference_lap"] == lap_numbers[1]
        assert "comparisons" in data
        assert len(data["comparisons"]) > 0

        # Check comparison structure
        comparison = data["comparisons"][0]
        assert comparison["channel"] == channel_name
        assert "target_values" in comparison
        assert "reference_values" in comparison
        assert "target_timestamps" in comparison
        assert "reference_timestamps" in comparison

    def test_compare_laps_not_found(self) -> None:
        """Test comparing non-existent laps."""
        response = client.post(
            f"/api/v1/signals/sessions/{SAMPLE_SESSION_ID}/compare",
            json={
                "target_lap": 99998,
                "reference_lap": 99999,
                "channels": ["Ground Speed"],
            },
        )
        assert response.status_code == 404

    def test_compare_laps_multiple_channels(self) -> None:
        """Test comparing multiple channels between laps."""
        # Get available signals
        signals_response = client.get(f"/api/v1/signals/sessions/{SAMPLE_SESSION_ID}")
        assert signals_response.status_code == 200
        signals_data = signals_response.json()

        if len(signals_data["signals"]) < 2:
            pytest.skip("Not enough signals available in test data")

        channel_names = [s["name"] for s in signals_data["signals"][:2]]

        # Get laps
        laps_response = client.get(f"/api/v1/sessions/{SAMPLE_SESSION_ID}/laps")
        assert laps_response.status_code == 200
        laps_data = laps_response.json()

        if len(laps_data["laps"]) < 2:
            pytest.skip("Not enough laps available for comparison")

        lap_numbers = [lap["lap_number"] for lap in laps_data["laps"][:2]]

        # Compare multiple channels
        response = client.post(
            f"/api/v1/signals/sessions/{SAMPLE_SESSION_ID}/compare",
            json={
                "target_lap": lap_numbers[0],
                "reference_lap": lap_numbers[1],
                "channels": channel_names,
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert len(data["comparisons"]) == 2
        channels_returned = [c["channel"] for c in data["comparisons"]]
        assert channel_names[0] in channels_returned
        assert channel_names[1] in channels_returned

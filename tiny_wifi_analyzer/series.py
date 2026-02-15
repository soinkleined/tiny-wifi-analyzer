"""Series data conversion for ApexCharts visualization."""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

# CoreWLAN-compatible band identifiers
CHANNEL_BAND_24 = 1
CHANNEL_BAND_5 = 2
CHANNEL_BAND_6 = 3

# X-axis bounds used by the frontend
CHANNEL_NUMBER_MAX_24 = 16
CHANNEL_NUMBER_MAX_5 = 170
CHANNEL_NUMBER_MAX_6 = 233


def channel_bounds_for_band(band: int) -> Tuple[int, int]:
    """Get the channel number bounds for a given band.

    Args:
        band: Band identifier (CHANNEL_BAND_24, CHANNEL_BAND_5, or
              CHANNEL_BAND_6)

    Returns:
        Tuple of (min_channel, max_channel)
    """
    if band == CHANNEL_BAND_24:
        return 1, CHANNEL_NUMBER_MAX_24
    if band == CHANNEL_BAND_5:
        return 1, CHANNEL_NUMBER_MAX_5
    if band == CHANNEL_BAND_6:
        return 1, CHANNEL_NUMBER_MAX_6
    # Fallback to a safe default range
    return 1, CHANNEL_NUMBER_MAX_5


def channel_half_span_for_width(width_mhz: Optional[int]) -> int:
    """Convert MHz channel width into half-span in channel number steps.

    Channel numbers across 2.4/5/6 GHz are spaced 5 MHz apart. A 20 MHz
    channel covers ~4 channel steps total, so half-span is 2; 40 MHz -> 4;
    80 -> 8; 160 -> 16.

    Args:
        width_mhz: Channel width in MHz (defaults to 20 if None)

    Returns:
        Half-span in channel number steps
    """
    if not width_mhz:
        width_mhz = 20
    # total span in channel steps (5 MHz per step)
    total_steps = int(round(width_mhz / 5))
    half = max(1, total_steps // 2)
    return half


def _clamp_channel(value: int, band: int) -> int:
    """Clamp a channel number to valid bounds for the given band.

    Args:
        value: Channel number to clamp
        band: Band identifier

    Returns:
        Clamped channel number
    """
    lo, hi = channel_bounds_for_band(band)
    return max(lo, min(hi, int(value)))


@dataclass
class _Chan:
    """Internal channel representation."""

    channel_band: int
    channel_number: int
    channel_width: int


@dataclass
class _Net:
    """Internal network representation."""

    ssid: str
    bssid: str
    rssi: int
    channel: _Chan


def to_series(nws: List[Any]) -> List[Dict[str, Any]]:
    """Convert networks to ApexCharts series data with correct spans.

    Expects items resembling PyNetwork:
      - .ssid: str
      - .bssid: str
      - .rssi: int
      - .channel.channel_band: int
      - .channel.channel_number: int
      - .channel.channel_width: int (MHz)

    Args:
        nws: List of network objects

    Returns:
        List of series dictionaries for ApexCharts
    """
    series = []
    for nw in nws:
        try:
            band = nw.channel.channel_band
            center = int(nw.channel.channel_number)
            width_mhz = int(nw.channel.channel_width)
            half = channel_half_span_for_width(width_mhz)
            left = _clamp_channel(center - half, band)
            right = _clamp_channel(center + half, band)
            series.append(
                {
                    "name": nw.bssid,
                    "ssid": nw.ssid,
                    "data": [[left, -100], [center, int(nw.rssi)], [right, -100]],
                }
            )
        except Exception:
            # Skip malformed entries defensively
            continue
    return series

# PoinTT API Integration Guide

This guide explains how to use the PoinTT API integration for controlling IVT/Bosch AC units.

## Quick Start

### 1. Prerequisites

You need:
- Your device ID (e.g., "101638933")
- OAuth access token and refresh token

### 2. Token Setup

Create a `tokens.json` file with your credentials:

```json
{
  "access_token": "your_access_token_here",
  "refresh_token": "your_refresh_token_here"
}
```

The library will automatically:
- Load these tokens on initialization
- Refresh the access token when it expires (every ~1 hour)
- Save the new tokens back to the file

### 3. Basic Usage

```python
import asyncio
import aiohttp
from bosch_thermostat_client.const import POINTTAPI, AC
from bosch_thermostat_client.gateway import gateway_chooser

async def control_ac():
    async with aiohttp.ClientSession() as session:
        # Initialize gateway
        GatewayClass = gateway_chooser(POINTTAPI)
        gateway = GatewayClass(
            device_id="YOUR_DEVICE_ID",
            access_token="YOUR_ACCESS_TOKEN",
            session=session,
            token_file="tokens.json"
        )

        # Initialize
        await gateway.initialize()

        # Get AC circuits
        circuits = await gateway.initialize_circuits(AC)
        ac = circuits[0]  # Get first (and usually only) AC circuit

        # Read current state
        await ac.update()
        print(f"Temperature: {ac.current_temp}°C")
        print(f"Target: {ac.target_temperature}°C")
        print(f"Mode: {ac.operation_mode}")
        print(f"Status: {'ON' if ac.is_on else 'OFF'}")

        # Control the AC
        await ac.set_temperature(22.0)
        await ac.set_operation_mode("heat")
        await ac.set_fan_speed("auto")
        await ac.turn_on()

asyncio.run(control_ac())
```

## Available Properties

### Read-Only Properties
- `current_temp` - Current room temperature
- `is_on` - Whether AC is on or off
- `hvac_action` - Current HVAC action (heat/cool/fan/off)

### Read/Write Properties
- `target_temperature` - Target temperature setpoint
- `operation_mode` - Operation mode (auto/heat/cool/fanOnly)
- `fan_speed` - Fan speed (auto/quiet/low/mid/high)
- `air_flow_horizontal` - Horizontal airflow direction (center/left/right/swing)
- `air_flow_vertical` - Vertical airflow direction (auto/angle1-5/swing)

## Available Methods

### Control Methods
- `await ac.turn_on()` - Turn AC on
- `await ac.turn_off()` - Turn AC off
- `await ac.set_temperature(temp)` - Set target temperature (16.0-30.0°C)
- `await ac.set_operation_mode(mode)` - Set operation mode
- `await ac.set_fan_speed(speed)` - Set fan speed
- `await ac.set_air_flow_horizontal(direction)` - Set horizontal airflow
- `await ac.set_air_flow_vertical(direction)` - Set vertical airflow

### State Management
- `await ac.update()` - Refresh all properties from API

## Testing

Run the included test script:

```bash
python3 test_pointt_integration.py
```

This will:
1. Load tokens from `tokens.json`
2. Initialize the gateway
3. Discover AC circuits
4. Read and display current state

## Token Refresh

The library handles token refresh automatically:
- Checks token expiry before each request
- Refreshes if expired or expires within 5 minutes
- Saves new tokens to the token file
- Uses the refresh token to get new access tokens

## Bulk Endpoints

The PoinTT API uses "bulk endpoints" for efficiency. The library automatically:
- Configures bulk endpoints from the database
- Fetches multiple values in a single API call
- Caches results to minimize API requests

The bulk endpoint `/airConditioning/standardFunctions` returns all AC parameters at once.

## Integration with Home Assistant

To integrate with Home Assistant:
1. Ensure this library works with your setup using the test script
2. Update the `home-assistant-bosch-custom-component` repository
3. Add PoinTT API support to the climate platform

## Troubleshooting

### Token Errors
- Make sure `tokens.json` has both `access_token` and `refresh_token`
- Check file permissions (should be 0600 for security)
- Verify tokens are valid by testing with the API directly

### Connection Errors
- Verify device ID is correct
- Check network connectivity
- Ensure the API endpoint is accessible

### Circuit Not Found
- Verify the `/airConditioning/standardFunctions` endpoint returns data
- Check that the device supports the standard functions

## Architecture Notes

### Key Components

1. **Connector** (`connectors/pointtapi.py`)
   - Handles OAuth authentication and token refresh
   - Makes HTTP requests to PoinTT API
   - Manages bulk endpoints for efficient API usage
   - Special handling for `/acCircuits` endpoint (returns static single circuit)

2. **Gateway** (`gateway/pointtapi.py`)
   - Initializes the connection
   - Discovers and manages circuits
   - Sets up bulk endpoints from database

3. **AC Circuit** (`circuits/pointtapi/ac.py`)
   - Represents a single AC unit
   - Provides properties for reading state
   - Provides methods for controlling the AC

4. **Database** (`db/db_POINTTAPI.json` and `db/pointtapi/050006.json`)
   - Defines gateway structure
   - Maps API endpoints to properties
   - Configures bulk endpoints

### Circuit Discovery

Unlike other Bosch devices that have a `/heatingCircuits` or `/dhwCircuits` endpoint that lists
available circuits, the PoinTT API doesn't have a `/acCircuits` endpoint. Instead:

1. The connector returns a static response for `/acCircuits` with a single circuit reference
2. The database defines the AC circuit structure
3. The circuit initialization uses the `ac1` identifier

This is a workaround specific to PoinTT API's architecture.

## Next Steps

- [ ] Test with real API credentials
- [ ] Verify token refresh works after 1 hour
- [ ] Test all control methods (temperature, mode, fan, airflow)
- [ ] Integrate with Home Assistant
- [ ] Add proper error handling for network failures
- [ ] Add retry logic for transient API errors

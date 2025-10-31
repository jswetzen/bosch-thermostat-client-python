# Bosch Pointt API Client

A comprehensive Python client for interacting with the Bosch Pointt API, providing OAuth 2.0 authentication, token management, and device control functionality.

## Overview

This client encapsulates all the functionality needed to:
- Perform OAuth 2.0 authentication flow
- Store and manage access/refresh tokens
- Make authenticated API requests to Bosch Pointt devices
- Handle token refresh automatically
- Support multiple devices

## Features

- **OAuth 2.0 Flow**: Complete PKCE-enabled OAuth flow with browser integration
- **Token Management**: Automatic token persistence, loading, and refresh
- **Device Control**: High-level methods for common operations (temperature, mode, etc.)
- **Multi-Device Support**: Work with multiple devices using the same tokens
- **Command Line Interface**: Full CLI for all operations
- **Error Handling**: Comprehensive error handling and user feedback
- **Flexible API**: Support for custom API endpoints and methods

## Installation

Ensure you have the required dependencies:

```bash
pip install requests
```

## Quick Start

### 1. Authentication (One-time setup)

```bash
python bosch_pointt_api.py auth --device YOUR_DEVICE_ID
```

This will:
- Open your browser to the Bosch OAuth page
- Prompt you to paste the callback URL
- Exchange the code for access/refresh tokens
- Save tokens to `tokens.pkl`

### 2. Query Your Device

```bash
# Get standard functions (most common)
python bosch_pointt_api.py query standard --device YOUR_DEVICE_ID

# Get current temperature setpoint
python bosch_pointt_api.py query temp --device YOUR_DEVICE_ID

# Get operation mode
python bosch_pointt_api.py query mode --device YOUR_DEVICE_ID
```

### 3. Control Your Device

```bash
# Set temperature to 22.5°C
python bosch_pointt_api.py set-temp 22.5 --device YOUR_DEVICE_ID
```

## Command Line Usage

### Authentication Commands

```bash
# Start OAuth flow (opens browser)
python bosch_pointt_api.py auth --device YOUR_DEVICE_ID

# Start OAuth flow without opening browser
python bosch_pointt_api.py auth --device YOUR_DEVICE_ID --no-browser

# Refresh existing tokens
python bosch_pointt_api.py refresh
```

### Query Commands

```bash
# Get standard functions
python bosch_pointt_api.py query standard --device YOUR_DEVICE_ID

# Get operation mode
python bosch_pointt_api.py query mode --device YOUR_DEVICE_ID

# Get temperature setpoint
python bosch_pointt_api.py query temp --device YOUR_DEVICE_ID

# Get resource information
python bosch_pointt_api.py query resource --device YOUR_DEVICE_ID
```

### Control Commands

```bash
# Set temperature setpoint
python bosch_pointt_api.py set-temp 23.0 --device YOUR_DEVICE_ID
```

### Custom API Requests

```bash
# Custom GET request
python bosch_pointt_api.py custom "/resource/airConditioning/standardFunctions" --device YOUR_DEVICE_ID

# Custom PUT request with data
python bosch_pointt_api.py custom "/resource/airConditioning/temperatureSetpoint" \
  --method PUT --data '{"value": 22.0}' --device YOUR_DEVICE_ID
```

### Options

```bash
# Use custom token file
python bosch_pointt_api.py --token-file my_tokens.pkl query standard --device YOUR_DEVICE_ID

# Get help
python bosch_pointt_api.py --help
python bosch_pointt_api.py auth --help
python bosch_pointt_api.py query --help
```

## Python API Usage

### Basic Usage

```python
from bosch_pointt_api import BoschPointtAPI

# Initialize the client
api = BoschPointtAPI(token_file="tokens.pkl", device_id="YOUR_DEVICE_ID")

# Load existing tokens
api.load_tokens()

# Query device
result = api.get_standard_functions()
print(result)

# Set temperature
api.set_temperature_setpoint(22.5)
```

### Complete OAuth Flow

```python
from bosch_pointt_api import BoschPointtAPI

# Initialize client
api = BoschPointtAPI(device_id="YOUR_DEVICE_ID")

# Generate OAuth URL
auth_url = api.build_auth_url()
print(f"Open this URL: {auth_url}")

# Get callback URL from user (after they authorize)
callback_url = input("Paste callback URL: ")

# Extract code and get tokens
code = api.extract_code_from_url(callback_url)
if code and api.exchange_code_for_tokens(code):
    print("Authentication successful!")
    
    # Now you can make API calls
    result = api.get_standard_functions()
    print(result)
```

### Token Management

```python
from bosch_pointt_api import BoschPointtAPI

api = BoschPointtAPI()

# Load tokens
if api.load_tokens():
    # Check if expired and refresh
    if api.is_token_expired():
        if api.refresh_access_token():
            print("Token refreshed!")
        else:
            print("Need to re-authenticate")
    
    # Make API calls
    api.get_standard_functions()
```

### Working with Multiple Devices

```python
from bosch_pointt_api import BoschPointtAPI

# Initialize without default device
api = BoschPointtAPI(token_file="tokens.pkl")
api.load_tokens()

devices = ["YOUR_DEVICE_ID", "101638934"]

for device_id in devices:
    print(f"Querying device {device_id}:")
    result = api.get_standard_functions(device_id=device_id)
    if result:
        print(f"  Temperature: {result.get('temperature', 'N/A')}")
```

### Custom API Requests

```python
from bosch_pointt_api import BoschPointtAPI

api = BoschPointtAPI(device_id="YOUR_DEVICE_ID")
api.load_tokens()

# Custom GET request
result = api.make_api_request("/resource/airConditioning/standardFunctions")

# Custom PUT request
result = api.make_api_request(
    "/resource/airConditioning/temperatureSetpoint",
    method="PUT",
    data={"value": 23.0}
)
```

## Available API Methods

### High-Level Device Methods

- `get_standard_functions(device_id=None)` - Get standard AC functions
- `get_operation_mode(device_id=None)` - Get current operation mode
- `get_temperature_setpoint(device_id=None)` - Get temperature setpoint
- `set_temperature_setpoint(temperature, device_id=None)` - Set temperature
- `get_resource_info(device_id=None)` - Get general resource information

### Low-Level API Methods

- `make_api_request(endpoint, method="GET", data=None, device_id=None)` - Generic API request

### Authentication Methods

- `build_auth_url()` - Generate OAuth authorization URL
- `extract_code_from_url(url)` - Extract code from callback URL
- `exchange_code_for_tokens(code)` - Exchange code for tokens

### Token Management Methods

- `load_tokens()` - Load tokens from file
- `save_tokens()` - Save tokens to file
- `is_token_expired()` - Check if token is expired
- `refresh_access_token()` - Refresh access token
- `ensure_valid_token()` - Ensure we have a valid token

## Configuration

### Environment Variables

None required - all configuration is done via parameters.

### Token Storage

Tokens are stored in pickle files (default: `tokens.pkl`). The file contains:
- `access_token` - Current access token
- `refresh_token` - Refresh token for getting new access tokens
- `expires` - Token expiration datetime
- `expires_in` - Original expiration time in seconds
- `token_type` - Token type (usually "Bearer")

### Device IDs

Device IDs can be found through the Bosch app or by querying the gateway list endpoint. Common format is numeric (e.g., `YOUR_DEVICE_ID`).

## Error Handling

The client provides comprehensive error handling:

- **Authentication Errors**: Clear messages for OAuth flow issues
- **Token Errors**: Automatic refresh attempts, clear expiration messages
- **API Errors**: HTTP status codes and response details
- **Network Errors**: Connection timeout and retry guidance

## Troubleshooting

### Common Issues

1. **"No tokens available"**
   - Run the auth flow: `python bosch_pointt_api.py auth --device YOUR_DEVICE_ID`

2. **"Token is expired"**
   - The client will try to refresh automatically
   - If refresh fails, re-run the auth flow

3. **"No device ID specified"**
   - Always provide `--device YOUR_DEVICE_ID` or set it in the code

4. **API request fails**
   - Check your device ID is correct
   - Ensure your device is online
   - Verify the API endpoint is correct

### Debug Information

For debugging, the client prints detailed information:
- OAuth URLs
- Token status and expiration
- API request URLs and responses
- Error messages with context

## API Endpoints

Common endpoints used with the Bosch Pointt API:

- `/resource/airConditioning/standardFunctions` - Main device status
- `/resource/airConditioning/operationMode` - Operation mode (heat/cool/auto)
- `/resource/airConditioning/temperatureSetpoint` - Temperature setpoint
- `/resource/` - General resource information

## Migration from Original Scripts

If you were using the original `pointt_api_oauth.py` and `api.py` scripts:

### Old Way:
```python
# Multiple files, manual token management
# Run pointt_api_oauth.py for auth
# Run api.py with hardcoded device ID
```

### New Way:
```python
from bosch_pointt_api import BoschPointtAPI

api = BoschPointtAPI(device_id="YOUR_DEVICE_ID")
# Everything integrated in one class
```

### Command Line Migration:
```bash
# Old: Manual OAuth flow, hardcoded device
# New: 
python bosch_pointt_api.py auth --device YOUR_DEVICE_ID
python bosch_pointt_api.py query standard --device YOUR_DEVICE_ID
```

## Contributing

This is a single-file implementation for simplicity. To extend:

1. Add new API methods to the `BoschPointtAPI` class
2. Add corresponding CLI commands in the `main()` function
3. Update the argument parser as needed

## License

Same as the parent project.

## Support

For issues specific to this client, check:
1. Your device ID is correct
2. Your internet connection is working
3. The Bosch Pointt API is accessible
4. Your tokens haven't been revoked

For Bosch Pointt API documentation, refer to the official Bosch documentation or reverse-engineer the mobile app API calls.
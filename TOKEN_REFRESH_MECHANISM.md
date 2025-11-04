# PoinTT API - Token Refresh Mechanism for Home Assistant

## Summary

✅ **Token refresh DOES work**
✅ **Refreshed tokens ARE accessible via properties**
✅ **HA just needs to check for updates**

The mechanism is working correctly. The issue is that HA needs to actively check if tokens have changed and update `entry.data` accordingly.

---

## How Token Refresh Works

### Automatic Refresh

The connector automatically refreshes tokens before **every API call**:

```python
async def _ensure_valid_token(self):
    """Ensure we have a valid access token, refreshing if necessary."""
    if self._is_token_expired():
        await self._refresh_access_token()

async def get(self, uri):
    """Get data from API endpoint."""
    await self._ensure_valid_token()  # ← Automatic refresh
    # ... make API call ...
```

**When tokens are considered expired:**
- Token expires within 5 minutes (proactive refresh)
- No expiration timestamp set (will refresh on first call)

**What gets updated during refresh:**
- `self._access_token` → New access token
- `self._refresh_token` → New refresh token (if provided by API)
- `self._token_expires_at` → New expiration time (now + 3600 seconds)

---

## How HA Can Access Refreshed Tokens

### Method 1: Direct Properties ✅ RECOMMENDED

```python
# In thermostat_refresh() or after any gateway operation
current_access_token = gateway.access_token    # Returns LIVE value from connector
current_refresh_token = gateway.refresh_token  # Returns LIVE value from connector
current_expires_at = gateway.token_expires_at  # Returns LIVE value from connector

# Compare with stored values
if current_access_token != entry.data['access_token']:
    _LOGGER.info("OAuth tokens refreshed, updating config entry")
    hass.config_entries.async_update_entry(
        entry,
        data={
            **entry.data,
            'access_token': current_access_token,
            'refresh_token': current_refresh_token,
            'token_expires_at': current_expires_at,
        }
    )
```

### Method 2: Helper Method `tokens_changed()` ✅ EASIER

```python
# In thermostat_refresh() or after any gateway operation
if gateway.tokens_changed(
    entry.data['access_token'],
    entry.data.get('refresh_token')
):
    _LOGGER.info("OAuth tokens refreshed, updating config entry")
    hass.config_entries.async_update_entry(
        entry,
        data={
            **entry.data,
            'access_token': gateway.access_token,
            'refresh_token': gateway.refresh_token,
            'token_expires_at': gateway.token_expires_at,
        }
    )
```

### Method 3: Get All Token Info at Once `get_token_info()` ✅ CONVENIENT

```python
# In thermostat_refresh() or after any gateway operation
token_info = gateway.get_token_info()
# Returns: {
#     'access_token': '...',
#     'refresh_token': '...',
#     'token_expires_at': '2025-11-04T20:00:00+00:00',
#     'device_id': '123456789'
# }

# Simple comparison
if token_info['access_token'] != entry.data['access_token']:
    _LOGGER.info("OAuth tokens refreshed, updating config entry")
    hass.config_entries.async_update_entry(
        entry,
        data={**entry.data, **token_info}
    )
```

---

## Where to Check for Token Updates in HA

### Option A: In `thermostat_refresh()` ✅ RECOMMENDED

```python
async def thermostat_refresh(self, event_time=None):
    """Refresh thermostat data (called every SCAN_INTERVAL)."""
    async with self._update_lock:
        try:
            # Perform data updates
            await self.gateway.check_connection()
            # ... other update logic ...

            # Check for token refresh AFTER operations
            if self.gateway.tokens_changed(
                self.entry.data['access_token'],
                self.entry.data.get('refresh_token')
            ):
                _LOGGER.info("OAuth tokens refreshed, updating config entry")
                self.hass.config_entries.async_update_entry(
                    self.entry,
                    data={
                        **self.entry.data,
                        'access_token': self.gateway.access_token,
                        'refresh_token': self.gateway.refresh_token,
                        'token_expires_at': self.gateway.token_expires_at,
                    }
                )

        except Exception as err:
            _LOGGER.error("Error during thermostat refresh: %s", err)
```

**Rationale:**
- `thermostat_refresh()` runs periodically (every SCAN_INTERVAL)
- It makes API calls which trigger `_ensure_valid_token()`
- Perfect place to check for token updates

### Option B: In `async_init_bosch()` ✅ ALSO GOOD

```python
async def async_init_bosch(self) -> bool:
    """Initialize gateway on HA startup."""
    # Validate connection (may trigger token refresh if expired)
    await self.gateway.check_connection()

    # Check if tokens changed (important after HA restart!)
    if self.gateway.tokens_changed(
        self.entry.data['access_token'],
        self.entry.data.get('refresh_token')
    ):
        _LOGGER.info("Tokens refreshed during initialization, updating config entry")
        self.hass.config_entries.async_update_entry(
            self.entry,
            data={
                **self.entry.data,
                'access_token': self.gateway.access_token,
                'refresh_token': self.gateway.refresh_token,
                'token_expires_at': self.gateway.token_expires_at,
            }
        )

    # Continue with normal init...
    if not self.gateway.uuid:
        raise ConfigEntryNotReady(...)
    # ...
```

**Rationale:**
- HA restart with expired tokens → immediate refresh on first `check_connection()`
- Ensures tokens are updated in entry.data right away

---

## Full HA Integration Example

```python
class BoschGatewayEntry:
    """Bosch gateway entry."""

    def __init__(self, hass, config_entry):
        """Initialize."""
        self.hass = hass
        self.entry = config_entry
        self.gateway = None
        # ... other init ...

    async def async_init(self):
        """Initialize gateway."""
        # Create gateway with tokens from config entry
        BoschGateway = bosch.gateway_chooser(device_type=self._device_type)
        self.gateway = BoschGateway(
            session=async_get_clientsession(self.hass),
            session_type=self._protocol,
            host=self.entry.data['address'],
            access_key=self.entry.data.get('access_key'),
            access_token=self.entry.data['access_token'],
            refresh_token=self.entry.data.get('refresh_token'),
            token_file=None,  # HA manages tokens via entry.data
        )

        # Initialize (may trigger token refresh if expired)
        if await self.async_init_bosch():
            # Gateway initialized successfully
            # Set up periodic refresh
            async_track_time_interval(
                self.hass,
                self.thermostat_refresh,
                SCAN_INTERVAL
            )
            return True
        return False

    async def async_init_bosch(self) -> bool:
        """Initialize Bosch gateway."""
        # Check connection (may trigger token refresh)
        await self.gateway.check_connection()

        # IMPORTANT: Check for token updates after initialization
        self._update_tokens_if_changed()

        # Verify gateway is ready
        if not self.gateway.uuid:
            raise ConfigEntryNotReady("Gateway UUID not available")

        # Get capabilities, etc.
        # ...
        return True

    async def thermostat_refresh(self, event_time=None):
        """Refresh thermostat data."""
        async with self._update_lock:
            try:
                # Perform data updates
                await self.gateway.check_connection()
                # ... update sensors, circuits, etc. ...

                # IMPORTANT: Check for token updates after operations
                self._update_tokens_if_changed()

            except Exception as err:
                _LOGGER.error("Error during thermostat refresh: %s", err)

    def _update_tokens_if_changed(self):
        """Update config entry if tokens have changed."""
        if self.gateway.tokens_changed(
            self.entry.data['access_token'],
            self.entry.data.get('refresh_token')
        ):
            _LOGGER.info("OAuth tokens refreshed, updating config entry")
            self.hass.config_entries.async_update_entry(
                self.entry,
                data={
                    **self.entry.data,
                    'access_token': self.gateway.access_token,
                    'refresh_token': self.gateway.refresh_token,
                    'token_expires_at': self.gateway.token_expires_at,
                }
            )
```

---

## Testing Token Refresh

### Test 1: Manual Token Change Detection ✅

```python
# Create gateway
gateway = PoinTTAPIGateway(...)

# Store initial token
stored_token = gateway.access_token

# Simulate token refresh (in real code, this happens automatically)
gateway._connector._access_token = "new_token_xyz"

# Check if token changed
current_token = gateway.access_token
assert current_token != stored_token  # ✓ Property returns updated value
```

**Result:** ✅ **WORKS** - Properties return live values from connector

### Test 2: Helper Methods ✅

```python
# Create gateway with initial tokens
gateway = PoinTTAPIGateway(
    access_token="initial_token",
    refresh_token="initial_refresh",
    ...
)

# Method 1: tokens_changed()
assert gateway.tokens_changed("initial_token") == False
gateway._connector._access_token = "new_token"
assert gateway.tokens_changed("initial_token") == True  # ✓ Detects change

# Method 2: get_token_info()
token_info = gateway.get_token_info()
assert token_info['access_token'] == "new_token"  # ✓ Returns current token
```

**Result:** ✅ **WORKS** - Helper methods correctly detect changes

---

## Common Issues and Solutions

### Issue 1: Tokens Not Updating Across HA Restarts

**Symptom:** After HA restart, gateway uses old (expired) tokens

**Cause:** HA creates gateway with stored tokens but doesn't check if they got refreshed during `check_connection()`

**Solution:** Call `_update_tokens_if_changed()` after `check_connection()` in `async_init_bosch()`

```python
async def async_init_bosch(self) -> bool:
    await self.gateway.check_connection()

    # IMPORTANT: Update entry.data with potentially refreshed tokens
    self._update_tokens_if_changed()  # ← Add this

    if not self.gateway.uuid:
        raise ConfigEntryNotReady(...)
    # ...
```

### Issue 2: Tokens Not Persisting

**Symptom:** Tokens refresh but HA loses them on next restart

**Cause:** HA never calls `async_update_entry()` to save new tokens

**Solution:** Check for token changes in `thermostat_refresh()` and update entry

```python
async def thermostat_refresh(self, event_time=None):
    # ... perform updates ...

    # Check for token refresh
    self._update_tokens_if_changed()  # ← Add this
```

### Issue 3: Don't Know When to Check

**Symptom:** Unsure where/when to check for token updates

**Solution:** Check in 2 places:
1. After `check_connection()` in `async_init_bosch()` (for HA restart)
2. At end of `thermostat_refresh()` (for periodic updates)

---

## Verification Checklist

- [ ] Gateway instantiated with `token_file=None` (HA mode)
- [ ] Gateway instantiated with `refresh_token` from entry.data
- [ ] `_update_tokens_if_changed()` called after `check_connection()` in init
- [ ] `_update_tokens_if_changed()` called at end of `thermostat_refresh()`
- [ ] Tokens stored in entry.data: `access_token`, `refresh_token`, `token_expires_at`
- [ ] HA can restart with stored tokens and continue working

---

## Summary

**The mechanism works!** You just need to:

1. **Check for token changes** after gateway operations
2. **Update entry.data** when tokens change
3. **Do this in 2 places:**
   - After `check_connection()` in initialization
   - After updates in `thermostat_refresh()`

**Helper methods available:**
- `gateway.access_token` - Get current access token
- `gateway.refresh_token` - Get current refresh token
- `gateway.token_expires_at` - Get expiration time
- `gateway.tokens_changed(stored_token)` - Check if changed
- `gateway.get_token_info()` - Get all token info at once

**The properties return LIVE values** from the connector, so token refresh is fully transparent to HA!

# PoinTT API - Home Assistant Integration Readiness Analysis

## Executive Summary

**Status: ⚠️ PARTIAL - Requires Interface Alignment**

The PoinTT API implementation is architecturally sound but requires interface adjustments to align with Home Assistant's integration patterns. The main challenges are:

1. Constructor signature mismatch
2. OAuth token lifecycle management (refresh tokens)
3. Token storage pattern differences
4. Missing required properties

## Home Assistant Integration Pattern

### How HA Uses the Client Library

```python
# 1. Choose gateway class
GatewayClass = gateway_chooser(device_type)

# 2. Instantiate with standard parameters
gateway = GatewayClass(
    session=aiohttp_session,      # HTTP only
    session_type=protocol_constant,  # HTTP, XMPP, etc.
    host=host_or_serial,
    access_key=encryption_key,
    access_token=main_token
)

# 3. Use gateway interface
await gateway.check_connection()
capabilities = await gateway.get_capabilities()
await gateway.raw_put(path, value)
await gateway.close()

# 4. Access per-entity objects
for circuit in gateway.heating_circuits:
    await circuit.update()
```

### Key Requirements

1. **Standardized Constructor**: All gateways must accept same parameters
2. **Static Credentials**: HA stores `access_key` and `access_token` in config entry
3. **Required Properties**: `access_token` and `access_key` must be readable
4. **BaseGateway Methods**: Must support standard interface

---

## Current PoinTT Implementation

### Constructor Signature

**Current:**
```python
PoinTTAPIGateway(
    device_id,
    access_token,
    session=None,
    token_file="tokens.json"
)
```

**Issues:**
- ❌ Missing `session_type` parameter (not used by PoinTT but expected by HA)
- ❌ Missing `access_key` parameter (OAuth doesn't use it)
- ❌ Uses `device_id` instead of `host`
- ❌ Has `token_file` parameter that HA won't pass

### Properties

**Current State:**
- ❌ No `access_token` property (defines `_access_token` but no getter)
- ❌ No `access_key` property (not applicable to OAuth)

**HA Expectation:**
```python
# HA reads these to store in config entry
token = gateway.access_token
key = gateway.access_key
```

### Token Storage

**Standard Connectors (IVT/Nefit/Easycontrol):**
- Static `access_key`: Encryption key for XMPP
- Static `access_token`: Long-lived gateway password/token
- HA stores both in config entry
- No expiration or refresh

**PoinTT API:**
- No `access_key` concept (REST API, no encryption)
- OAuth `access_token`: **Expires after 1 hour**
- OAuth `refresh_token`: Used to obtain new access tokens
- Automatic refresh via `_ensure_valid_token()`
- Currently stores tokens in JSON file

---

## Comparison: PoinTT vs Standard Connectors

### IVT Gateway (Reference Implementation)

```python
class IVTGateway(BaseGateway):
    def __init__(
        self,
        session_type,    # HTTP or XMPP
        host,            # IP or serial number
        access_token,    # Gateway password
        access_key=None, # Encryption key
        password=None,
        session=None,
    ):
        self._access_token = access_token.replace("-", "")
        Connector = connector_ivt_chooser(session_type)
        self._connector = Connector(
            host=host,
            loop=session,
            access_key=self._access_token,
            encryption=Encryption(access_key, password),
        )
```

**Properties:**
- ✅ `access_token`: Returns `self._access_token`
- ✅ `access_key`: Returns `self._connector.encryption_key`

### PoinTT Gateway (Current)

```python
class PoinTTAPIGateway(BaseGateway):
    def __init__(
        self,
        device_id,        # Device ID (not host)
        access_token,     # OAuth token
        session=None,
        token_file="tokens.json",
    ):
        self._device_id = device_id
        self._access_token = access_token  # Will be refreshed!
        Connector = connector_ivt_chooser(POINTTAPI)
        self._connector = Connector(
            host=device_id,
            access_token=access_token,
            loop=session,
            token_file=token_file,
        )
```

**Properties:**
- ❌ No `access_token` property defined
- ❌ No `access_key` property (connector has no `encryption_key` attribute)

---

## Critical Issues for HA Integration

### Issue 1: Token Expiration ⚠️

**The Fundamental Problem:**
- HA stores `gateway.access_token` in config entry at setup time
- PoinTT tokens expire after 1 hour
- HA will keep using expired token from config entry
- Token refresh happens in connector, but HA doesn't see it

**Current Behavior:**
```python
# During HA setup
token = gateway.access_token  # Gets initial token
# HA stores this in config.entry.data['access_token']

# 1 hour later...
# Connector refreshes token internally
# But HA still uses old token from config entry!
```

**Why This Matters:**
- HA won't be able to reconnect after restart (token expired)
- HA won't update config entry with refreshed tokens
- No way for HA to access `refresh_token` for storage

### Issue 2: Missing refresh_token Storage

**What HA Needs:**
```python
{
    "access_token": "current_oauth_token",
    "refresh_token": "long_lived_refresh_token",
    "expires_at": "2025-10-30T15:30:00"
}
```

**What HA Currently Gets:**
```python
{
    "access_token": "expired_token_from_setup",
    "access_key": None  # Doesn't exist for OAuth
}
```

### Issue 3: Constructor Interface Mismatch

**HA Calls:**
```python
gateway = PoinTTAPIGateway(
    session=websession,
    session_type="HTTP",  # ❌ Not accepted
    host="101638933",
    access_key=None,      # ❌ Not accepted
    access_token="token"
)
```

**Current Constructor Expects:**
```python
gateway = PoinTTAPIGateway(
    device_id="101638933",  # ❌ Different parameter name
    access_token="token",
    session=websession,
    token_file="tokens.json"  # ❌ HA won't pass this
)
```

---

## Required Changes for HA Integration

### 1. Align Constructor Signature ✅ EASY

```python
class PoinTTAPIGateway(BaseGateway):
    def __init__(
        self,
        session,         # ✅ Match HA expectation
        session_type,    # ✅ Accept but ignore (always HTTP)
        host,            # ✅ This is device_id for PoinTT
        access_key,      # ✅ Accept but ignore (no encryption)
        access_token,    # ✅ OAuth token
        refresh_token=None,  # ✅ NEW: Accept refresh token from HA
        token_file=None, # ✅ Optional, default to None for HA
    ):
        self._device_id = host  # host is device_id for PoinTT
        self._access_token = access_token
        self._refresh_token = refresh_token

        # token_file only for standalone scripts, not HA
        if token_file is None:
            token_file = f".pointt_tokens_{host}.json"
```

### 2. Add Required Properties ✅ EASY

```python
@property
def access_token(self):
    """Return current OAuth access token."""
    # Return current token (may have been refreshed)
    return self._connector._access_token

@property
def access_key(self):
    """Return None - OAuth doesn't use access_key."""
    return None

@property
def refresh_token(self):
    """Return OAuth refresh token for storage."""
    return self._connector._refresh_token

@property
def token_expires_at(self):
    """Return token expiration timestamp."""
    return self._connector._token_expires_at
```

### 3. Token Lifecycle Management ⚠️ COMPLEX

**Option A: Token File (Current - Won't Work with HA)**
- Connector manages tokens via file
- HA can't access updated tokens
- **Status: ❌ Not HA-compatible**

**Option B: Callback Pattern (Recommended)**
```python
class PoinTTAPIConnector:
    def __init__(self, ..., token_callback=None):
        self._token_callback = token_callback

    async def _refresh_token(self):
        # ... refresh logic ...

        # Notify HA of new tokens
        if self._token_callback:
            await self._token_callback({
                'access_token': self._access_token,
                'refresh_token': self._refresh_token,
                'expires_at': self._token_expires_at.isoformat()
            })
```

**HA Integration Side:**
```python
async def token_update_callback(new_tokens):
    """Update config entry with refreshed tokens."""
    hass.config_entries.async_update_entry(
        entry,
        data={**entry.data, **new_tokens}
    )

gateway = PoinTTAPIGateway(
    ...,
    token_callback=token_update_callback
)
```

**Option C: Polling Pattern (Simple but Less Efficient)**
```python
# In HA coordinator update cycle
async def _async_update_data():
    # Check if tokens changed
    if gateway.access_token != self.entry.data['access_token']:
        # Update config entry
        self.hass.config_entries.async_update_entry(
            self.entry,
            data={
                **self.entry.data,
                'access_token': gateway.access_token,
                'refresh_token': gateway.refresh_token,
            }
        )
```

### 4. Fix check_firmware_validity() ✅ EASY

**Current BaseGateway Implementation:**
```python
async def check_firmware_validity(self):
    """Run query against firmware version."""
    fw = await self._connector.get(self._db.get(BASE_FIRMWARE_VERSION))
    # ...
```

**Issue:** PoinTT API doesn't expose firmware endpoint

**Solution:** Override in PoinTTAPIGateway
```python
async def check_firmware_validity(self):
    """PoinTT API doesn't expose firmware endpoint.

    We hardcode firmware version during initialize(), so validity
    check is implicit (database exists = valid).
    """
    return True  # Always valid since we hardcode known firmware
```

---

## Integration Readiness Checklist

### Core Functionality ✅
- [x] Gateway registered in `gateway_chooser()`
- [x] Inherits from `BaseGateway`
- [x] Implements `initialize()`
- [x] Implements `initialize_circuits()`
- [x] Circuit discovery working
- [x] Value reading/writing working
- [x] Bulk endpoint optimization working
- [x] Automated tests passing

### HA Interface Requirements ⚠️
- [ ] Constructor accepts standard parameters (`session`, `session_type`, `host`, `access_key`, `access_token`)
- [ ] Defines `access_token` property
- [ ] Defines `access_key` property (can return None)
- [ ] Supports token refresh with HA notification
- [ ] Overrides `check_firmware_validity()` to return True

### Token Management 🔴
- [ ] HA can store `refresh_token` in config entry
- [ ] HA gets notified when tokens refresh
- [ ] Gateway works after HA restart with stored tokens
- [ ] Token file approach replaced with HA config entry storage

### Testing Requirements
- [ ] Integration test with HA-style instantiation
- [ ] Token refresh callback test
- [ ] HA restart simulation test (reload from config entry)

---

## Recommendations

### Immediate Actions (Required for HA)

1. **Update Constructor Signature** (1-2 hours)
   - Accept standard HA parameters
   - Map `host` → `device_id`
   - Accept optional `refresh_token`
   - Make `token_file` optional

2. **Add Properties** (30 minutes)
   - `access_token`: Return current token from connector
   - `access_key`: Return None
   - `refresh_token`: Return refresh token from connector
   - `token_expires_at`: Return expiration timestamp

3. **Override check_firmware_validity()** (15 minutes)
   - Return True (firmware hardcoded, always valid)

4. **Implement Token Callback** (2-3 hours)
   - Add callback parameter to connector
   - Call callback after token refresh
   - Update documentation for HA integration

### Testing Strategy

1. **Unit Tests** (HA-style instantiation)
   ```python
   async def test_ha_constructor():
       gateway = PoinTTAPIGateway(
           session=session,
           session_type="HTTP",
           host="101638933",
           access_key=None,
           access_token="token",
           refresh_token="refresh"
       )
       assert gateway.access_token == "token"
       assert gateway.access_key is None
       assert gateway.refresh_token == "refresh"
   ```

2. **Integration Tests** (Token refresh with callback)
   ```python
   async def test_token_refresh_callback():
       callback_called = False
       new_tokens = {}

       async def callback(tokens):
           nonlocal callback_called, new_tokens
           callback_called = True
           new_tokens = tokens

       gateway = PoinTTAPIGateway(..., token_callback=callback)
       # Trigger token refresh
       await gateway._connector._refresh_token()

       assert callback_called
       assert 'access_token' in new_tokens
       assert 'refresh_token' in new_tokens
   ```

3. **HA Simulation Tests** (Restart scenario)
   ```python
   async def test_ha_restart_with_refreshed_token():
       # Simulate HA storing config entry
       config_entry = {
           'access_token': 'initial',
           'refresh_token': 'refresh123'
       }

       # Simulate HA restart - create new gateway from stored tokens
       gateway = PoinTTAPIGateway(
           session=new_session,
           session_type="HTTP",
           host="101638933",
           access_key=None,
           access_token=config_entry['access_token'],
           refresh_token=config_entry['refresh_token']
       )

       # Should auto-refresh and work
       await gateway.check_connection()
       assert gateway.uuid is not None
   ```

### Documentation Updates

1. **HA Integration Guide**
   - Config flow setup with OAuth
   - Token storage in config entry
   - Token refresh handling
   - Example integration code

2. **Migration Guide**
   - How to migrate from token file to HA config entry
   - Backward compatibility notes

---

## Comparison with Other Connectors

### Token Storage Patterns

| Connector | access_key | access_token | Expiration | Storage |
|-----------|------------|--------------|------------|---------|
| IVT (XMPP) | AES encryption key | Gateway password | None | HA config entry |
| Nefit (XMPP) | Encryption key | Gateway password | None | HA config entry |
| Easycontrol | Encryption key | Gateway password | None | HA config entry |
| **PoinTT (OAuth)** | ❌ None | OAuth token | 1 hour | 🔴 Needs HA config + refresh |

**Key Insight:** PoinTT is the only OAuth-based connector, requiring special token lifecycle management that other connectors don't need.

---

## Conclusion

### Is PoinTT Ready for HA Integration?

**Technical Readiness: ✅ YES**
- Core functionality complete and tested
- Architecture sound
- All BaseGateway methods work

**Interface Alignment: ⚠️ NEEDS WORK**
- Constructor signature mismatch (easy fix)
- Missing properties (easy fix)
- Token refresh pattern needs HA integration (moderate complexity)

**Estimated Work: 4-6 hours**
- Constructor + properties: 2 hours
- Token callback implementation: 2-3 hours
- Testing: 1-2 hours

### Recommended Approach

1. **Phase 1: Interface Alignment** (blocking)
   - Update constructor
   - Add properties
   - Override check_firmware_validity()

2. **Phase 2: Token Management** (blocking)
   - Implement token callback
   - Add token lifecycle tests
   - Document HA integration pattern

3. **Phase 3: HA Integration** (separate repo)
   - Create custom_components/bosch integration PR
   - Add PoinTT config flow with OAuth
   - Implement token refresh in coordinator
   - Add HA integration tests

**Bottom Line:** PoinTT is architecturally ready but needs interface changes before HA can use it. The changes are straightforward and won't affect standalone usage.

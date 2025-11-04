# PoinTT API Sensor Fixes for Home Assistant

## Issues Fixed

### Issue 1: Sensors with `id=None` causing duplicate unique_ids ✅ FIXED

**Problem:**
```python
# HA sensor/base.py line 64-66
self._attr_unique_id = f"{self._domain_name}{self._bosch_object.id}{self._uuid}"
# Result: "SensorsNone101638933" for multiple sensors
```

**Root Cause:**
Sensors in `050006.json` were missing the `name` field. The sensor object uses `name` as its `id` property.

**Fix:**
Added `name` field to all sensors in both `sensors` and `switches` sections:

```json
// BEFORE (missing name)
"operationMode": {
    "id": "/airConditioning/operationMode",
    "bosch_type": "stringValue",
    ...
}

// AFTER (with name)
"operationMode": {
    "id": "/airConditioning/operationMode",
    "name": "Operation Mode",  // ← Added
    "bosch_type": "stringValue",
    ...
}
```

**Result:**
- Unique IDs now: `SensorsOperation Mode101638933`, `SensorsFan Speed101638933`, etc.
- No more duplicate unique_id errors ✓

---

### Issue 2: Text sensors marked as numeric with `state_class='measurement'` ✅ FIXED

**Problem:**
```python
# Sensor with value 'heat' (string) but state_class='measurement' (numeric)
# HA raises: "Entity has state class measurement but its state is not numeric"
```

**Root Cause:**
String/enum sensors (operationMode, fanSpeed, etc.) had `state_class: "measurement"` set, which is only valid for numeric sensors.

**Fix:**
Removed `state_class` and non-standard `device_class` from all text/enum sensors:

```json
// BEFORE (incorrect - text sensor with state_class)
"operationMode": {
    "id": "/airConditioning/operationMode",
    "allowedValues": ["auto", "heat", "cool", "fanOnly"],
    "state_class": "measurement",  // ← WRONG for text
    "device_class": "mode"          // ← Not a standard HA device_class
}

// AFTER (correct - no state_class for text)
"operationMode": {
    "id": "/airConditioning/operationMode",
    "name": "Operation Mode",
    "allowedValues": ["auto", "heat", "cool", "fanOnly"]
    // No state_class - text sensors don't have one
    // No device_class - "mode" isn't a standard HA class
}
```

**Only numeric sensors keep `state_class`:**
```json
// Temperature sensors - CORRECT (numeric with state_class)
"temperatureSetpoint": {
    "name": "Temperature Setpoint",
    "bosch_type": "floatValue",
    "type": "number",
    "unitOfMeasure": "C",
    "state_class": "measurement",   // ✓ OK for numeric
    "device_class": "temperature"   // ✓ Standard HA class
}
```

---

## Summary of Changes

### File: `bosch_thermostat_client/db/pointtapi/050006.json`

**Sensors Section (lines 132-243):**
| Sensor | Change | Reason |
|--------|--------|--------|
| `operationMode` | + `name`, - `state_class`, - `device_class` | Text sensor, needs ID |
| `acControl` | + `name`, - `state_class`, - `device_class` | Binary sensor, needs ID |
| `fanSpeed` | + `name`, - `state_class`, - `device_class` | Text sensor, needs ID |
| `airFlowHorizontal` | + `name`, - `state_class`, - `device_class` | Text sensor, needs ID |
| `airFlowVertical` | + `name`, - `state_class`, - `device_class` | Text sensor, needs ID |
| `temperatureSetpoint` | + `name`, **KEEP** `state_class` | Numeric sensor ✓ |
| `roomTemperature` | (already had `name`), **KEEP** `state_class` | Numeric sensor ✓ |
| `quickAirFlows` | + `name`, - `state_class`, - `device_class` | Text sensor, needs ID |

**Switches Section (lines 4-119):**
| Switch | Change | Reason |
|--------|--------|--------|
| `operationMode` | (already had `name`), - `state_class`, - `device_class` | Select, not numeric |
| `acControl` | (already had `name`), - `state_class`, - `device_class` | Binary switch |
| `fanSpeed` | (already had `name`), - `state_class`, - `device_class` | Select, not numeric |
| `airFlowHorizontal` | (already had `name`), - `state_class`, - `device_class` | Select, not numeric |
| `airFlowVertical` | (already had `name`), - `state_class`, - `device_class` | Select, not numeric |
| `temperatureSetpoint` | (already had `name`), **KEEP** `state_class` | Numeric number ✓ |
| `roomTemperature` | (already had `name`), **KEEP** `state_class` | Numeric number ✓ |
| `quickAirFlows` | (already had `name`), - `state_class`, - `device_class` | Select, not numeric |

---

## Rules Applied

### Rule 1: All sensors/switches MUST have `name` field
```json
{
    "id": "/path/to/endpoint",
    "name": "Human Readable Name",  // ← REQUIRED (becomes sensor.id)
    ...
}
```

### Rule 2: Only numeric sensors have `state_class`
```json
// ✓ CORRECT - Numeric sensor
{
    "bosch_type": "floatValue",
    "type": "number",
    "unitOfMeasure": "C",
    "state_class": "measurement",     // ← OK for numeric
    "device_class": "temperature"     // ← Standard HA class
}

// ✓ CORRECT - Text/enum sensor
{
    "bosch_type": "stringValue",
    "type": "select",
    "allowedValues": ["heat", "cool"]
    // NO state_class - text sensors don't have one
}
```

### Rule 3: Only use standard Home Assistant device_classes

**Standard numeric device_classes:**
- `temperature`, `humidity`, `pressure`, `battery`, `power`, `energy`, etc.

**Do NOT use:**
- `mode`, `fan`, `airflow`, `switch` - These are not standard HA device_classes for sensors

---

## Testing

### Integration Tests ✅
```bash
python3 tests/test_pointtapi_integration.py
```
**Result:** All tests pass ✓

### HA Component Pattern Tests ✅
```bash
python3 test_ha_component_pattern.py
```
**Result:** All tests pass ✓

---

## Expected HA Behavior After Fix

### Unique IDs (Issue 1 Fixed)
```python
# Before (duplicate):
- Sensors: id=None → unique_id="SensorsNone101638933"
- All sensors had same unique_id → ERROR

# After (unique):
- Operation Mode: id="Operation Mode" → unique_id="SensorsOperation Mode101638933"
- Fan Speed: id="Fan Speed" → unique_id="SensorsFan Speed101638933"
- AC Control: id="AC Control" → unique_id="SensorsAC Control101638933"
- Each sensor has unique ID ✓
```

### State Classes (Issue 2 Fixed)
```python
# Before (error):
- operationMode: state="heat", state_class="measurement" → ERROR (text with numeric class)

# After (correct):
- operationMode: state="heat", state_class=None → ✓ (text sensor, no class)
- temperatureSetpoint: state=20.0, state_class="measurement" → ✓ (numeric sensor, has class)
```

---

## Verification Checklist

- [x] All sensors have `name` field
- [x] Text sensors do NOT have `state_class`
- [x] Numeric sensors KEEP `state_class="measurement"`
- [x] Only standard HA `device_class` values used
- [x] Integration tests pass
- [x] HA component pattern tests pass
- [x] No duplicate unique_id errors expected
- [x] No "state is not numeric" errors expected

---

## Files Changed

- `bosch_thermostat_client/db/pointtapi/050006.json` - Fixed sensor/switch definitions

---

## Impact

✅ **No breaking changes** - Only adds missing fields and removes invalid fields
✅ **Backward compatible** - Existing code continues to work
✅ **HA compatible** - Sensors now work correctly with HA component
✅ **All tests pass** - Verified with integration and component pattern tests

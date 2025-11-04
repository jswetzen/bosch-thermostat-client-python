# PoinTT API - Fix roomTemperature writeable Field

## Issue

The `roomTemperature` sensor was incorrectly marked as `writeable: 1` in the switches section, making it appear as an editable control in Home Assistant. However, according to the actual API response, room temperature is **read-only** (`writeable: 0`).

## API Response Analysis

From the actual PoinTT API `/airConditioning/standardFunctions` endpoint:

```json
{
    "id": "/airConditioning/roomTemperature",
    "type": "floatValue",
    "writeable": 0,  // ← READ-ONLY!
    "recordable": 0,
    "value": 19.0,
    "unitOfMeasure": "C"
}
```

**Writable Controls (writeable: 1):**
- operationMode ✓
- acControl ✓
- fanSpeed ✓
- airFlowHorizontal ✓
- airFlowVertical ✓
- temperatureSetpoint ✓
- quickAirFlows ✓

**Read-Only Sensor (writeable: 0):**
- **roomTemperature** ← Should NOT be editable

---

## Changes Made

### File: `bosch_thermostat_client/db/pointtapi/050006.json`

### 1. Removed roomTemperature from switches section

**Before:**
```json
{
    "switches": {
        "temperatureSetpoint": { ... },
        "roomTemperature": {           // ← WRONG! Should not be a switch
            "writeable": 1,            // ← WRONG! Should be 0
            "type": "number",
            ...
        },
        "quickAirFlows": { ... }
    }
}
```

**After:**
```json
{
    "switches": {
        "temperatureSetpoint": { ... },
        // roomTemperature REMOVED - not a writable control
        "quickAirFlows": { ... }
    }
}
```

**Rationale:**
- Switches section → Writable controls in HA (number, select, binary_sensor entities)
- roomTemperature is read-only → Should NOT be in switches

---

### 2. Updated roomTemperature in sensors section to writeable: 0

**Before:**
```json
{
    "sensors": {
        "roomTemperature": {
            "id": "/airConditioning/roomTemperature",
            "name": "Room Temperature",
            // Missing writeable field - defaults unclear
            "type": "regular",
            ...
        }
    }
}
```

**After:**
```json
{
    "sensors": {
        "roomTemperature": {
            "id": "/airConditioning/roomTemperature",
            "name": "Room Temperature",
            "bosch_type": "floatValue",
            "type": "regular",
            "writeable": 0,      // ← EXPLICIT: Read-only
            "recordable": 0,
            "state_class": "measurement",
            "device_class": "temperature",
            "unitOfMeasure": "C"
        }
    }
}
```

**Rationale:**
- Sensors section → Read-only sensors in HA (sensor entities)
- roomTemperature has `writeable: 0` in API → Correctly marked as read-only

---

## Impact on Home Assistant

### Before Fix ❌
- **roomTemperature appeared twice:**
  1. As an editable number control (from switches section)
  2. As a read-only sensor (from sensors section)
- **User could try to change room temperature** (but it wouldn't work - API rejects it)
- **Confusing UX:** Why can I edit room temperature?

### After Fix ✅
- **roomTemperature appears once:**
  - Only as a read-only sensor entity
- **User cannot edit room temperature** (correct - it's measured, not set)
- **Clear separation:**
  - **Setpoint** (target temperature) → Editable number control
  - **Room Temperature** (current temperature) → Read-only sensor

---

## Validation Rules

### For switches section (writable controls):
```json
{
    "switches": {
        "controlName": {
            "writeable": 1,  // ← REQUIRED: Must be editable
            "type": "select" | "number" | "binary"
        }
    }
}
```

### For sensors section (read-only sensors):
```json
{
    "sensors": {
        "sensorName": {
            "writeable": 0,     // ← SHOULD BE 0 for read-only
            "type": "regular"   // ← Read-only sensor type
        }
    }
}
```

---

## Testing

### Integration Tests ✅
```bash
python3 tests/test_pointtapi_integration.py
```
**Result:** All tests pass ✓

### API Response Validation ✅
Confirmed against actual API response:
```json
{
    "id": "/airConditioning/roomTemperature",
    "writeable": 0,  // ✓ Matches our configuration
    "value": 19.0
}
```

---

## Summary

| Field | Before | After | Correct? |
|-------|--------|-------|----------|
| **Switches section** | roomTemperature with writeable: 1 | Removed entirely | ✅ |
| **Sensors section** | roomTemperature (no writeable field) | roomTemperature with writeable: 0 | ✅ |

**Expected HA Behavior:**
- ✅ Room Temperature shows as read-only sensor (correct)
- ✅ Temperature Setpoint shows as editable number (correct)
- ✅ No duplicate entities
- ✅ No confusing controls for read-only values

---

## Files Changed

- `bosch_thermostat_client/db/pointtapi/050006.json`
  - Removed roomTemperature from switches section
  - Added explicit `writeable: 0` to roomTemperature in sensors section

---

## Related Fixes

This fix complements the previous sensor fixes:
1. **Sensor IDs** - All sensors have unique `name` field ✓
2. **State classes** - Only numeric sensors have `state_class` ✓
3. **Writeable field** - Only editable controls in switches section ✓

All three issues are now resolved for proper HA integration!

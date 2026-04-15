# ZeroStream Frontend Documentation

## Overview

Mobile-first web application for collecting and visualizing sensor data from smartphones. Built with Vue 3 and FastAPI, deployed as a Databricks App.

## Features

### Display Modes
- **Combined View** (Default): Graphical gauges with numerical readouts
- **Numerical View**: Full sensor data in grid layout
- **Graphical View**: Simplified pitch/roll indicators
- **Toggle**: Hidden by default, enable in settings

### Sensors Collected
- **Acceleration**: Linear motion without gravity (m/s²)
- **Rotation Rate**: Angular velocity from gyroscope (°/s)
- **Orientation**: Device angles - heading, pitch, roll (degrees)
- **Location**: GPS coordinates with accuracy metrics
- **Magnetometer**: Magnetic field strength (μT)

### User Interface
- **10 Hz display refresh**: Smooth visual updates
- **Configurable data frequency**: 0.1-10 Hz collection rate
- **Status indicators**: Green pulse (active), blue flash (data sent)
- **Dark theme**: Optimized for mobile viewing
- **Full-screen lock**: No scrolling, fixed viewport

## Technical Architecture

### Directory Structure
```
zero_frontend/
├── app.py                      # FastAPI server
├── app.yaml                    # Databricks Apps config
├── requirements.txt            # Python dependencies
└── static/
    ├── index.html              # Vue 3 SPA
    ├── css/style.css           # Dark theme styles
    └── js/
        ├── app.js              # Main Vue instance
        ├── services/
        │   ├── uidGenerator.js # Client ID generation
        │   ├── sensorService.js # Sensor data collection
        │   └── zerobus.js      # Data batching/sending
        └── components/
            ├── CombinedDisplay.js
            ├── SensorDisplay.js
            ├── GraphicalDisplay.js
            ├── ConfigPanel.js
            ├── PermissionRequest.js
            └── MiniMap.js
```

### Key Components

#### Unique Client IDs
- **Format**: 12 characters (e.g., "quantumray42")
- **Generation**: Technical word combinations + numbers
- **Storage**: localStorage, persistent per device
- **Examples**: "cybernode001", "tensorbeam23", "alphaflux456"

#### Compass Implementation
- **Design**: Rotating compass rose with fixed indicator
- **Smooth rotation**: Continuous angle tracking prevents jumps
- **Visual**: Cardinal directions (N/E/S/W), tick marks every 10°

#### Data Collection
- **Display updates**: Fixed 10 Hz for smooth UI
- **Data collection**: Configurable 0.1-10 Hz
- **Batching**: 10 readings per transmission
- **Format**: JSON array of sensor readings

### API Endpoints

#### POST /api/stream
Receives batched sensor data from clients.

**Request Body**:
```json
[
  {
    "clientId": "quantumray42",
    "timestamp": "2024-02-02T10:30:00.123Z",
    "acceleration": {"x": 0.12, "y": -0.34, "z": 0.05},
    "accelerationIncludingGravity": {"x": 0.12, "y": -0.34, "z": 9.85},
    "rotationRate": {"alpha": 2.5, "beta": -1.2, "gamma": 0.8},
    "orientation": {"alpha": 45.6, "beta": 12.3, "gamma": -5.7},
    "location": {
      "latitude": 37.7749,
      "longitude": -122.4194,
      "altitude": 15.2,
      "accuracy": 5.0,
      "speed": 2.5,
      "heading": 45.0
    },
    "magnetometer": {"x": 25.5, "y": -12.3, "z": 48.7}
  }
]
```

**Response**:
```json
{
  "status": "success",
  "count": 10
}
```

#### GET /api/health
Health check endpoint.

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2024-02-02T10:30:00Z"
}
```

## Configuration

### Client Settings (localStorage)
- `zerostream_uid`: Unique client identifier
- `zerostream_frequency`: Data collection frequency
- `zerostream_display_mode`: Current display mode
- `zerostream_alternate_displays`: Enable mode toggle

### Server Settings (config.env)
- `DEFAULT_FREQUENCY_HZ`: Initial collection frequency
- `DEFAULT_DISPLAY_MODE`: Starting display mode
- `ZEROBUS_BATCH_SIZE`: Records per transmission

## Deployment

```bash
# Using deploy script
./deploy-app.sh zerostream ./zero_frontend

# Manual deployment
databricks apps create zerostream
databricks sync ./zero_frontend /Users/frank.munz@databricks.com/apps/zerostream
databricks apps deploy zerostream --source-code-path /Workspace/Users/frank.munz@databricks.com/apps/zerostream
```

## Mobile Considerations

### iOS Permission Handling
- Motion sensors require explicit permission
- Location services prompt on first use
- Permission state saved in app

### Viewport Locking
- No horizontal scrolling
- Fixed position body
- Viewport-fit=cover for notched devices
- Overscroll behavior disabled

### Performance
- CSS transitions for smooth animations
- Minimal DOM updates via Vue reactivity
- Batch network requests to reduce overhead
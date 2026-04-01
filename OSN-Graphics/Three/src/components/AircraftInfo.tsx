import type { Aircraft } from '../types'
import { formatAltitude, formatVelocity, formatCoordinate } from '../lib/geo'

interface AircraftInfoProps {
  aircraft: Aircraft | null
  onClose: () => void
}

export function AircraftInfo({ aircraft, onClose }: AircraftInfoProps) {
  if (!aircraft) return null

  const altitude = formatAltitude(aircraft.altitude)
  const velocity = formatVelocity(aircraft.velocity)

  return (
    <div className="aircraft-info">
      <div className="aircraft-info-header">
        <h2>{aircraft.callsign || aircraft.icao24}</h2>
        <button onClick={onClose} className="close-btn">
          &times;
        </button>
      </div>

      <div className="info-grid">
        <div className="info-item">
          <span className="label">ICAO24</span>
          <span className="value">{aircraft.icao24}</span>
        </div>
        <div className="info-item">
          <span className="label">Callsign</span>
          <span className="value">{aircraft.callsign || '-'}</span>
        </div>
        <div className="info-item">
          <span className="label">Country</span>
          <span className="value">{aircraft.originCountry}</span>
        </div>
        <div className="info-item">
          <span className="label">Status</span>
          <span className={`value status ${aircraft.onGround ? 'ground' : 'airborne'}`}>
            {aircraft.onGround ? 'On Ground' : 'Airborne'}
          </span>
        </div>

        <div className="info-section">
          <h3>Position</h3>
        </div>

        <div className="info-item">
          <span className="label">Latitude</span>
          <span className="value">{formatCoordinate(aircraft.latitude, 'lat')}</span>
        </div>
        <div className="info-item">
          <span className="label">Longitude</span>
          <span className="value">{formatCoordinate(aircraft.longitude, 'lon')}</span>
        </div>
        <div className="info-item">
          <span className="label">Altitude</span>
          <span className="value">
            {altitude.meters}
            <br />
            <span className="secondary">{altitude.feet}</span>
          </span>
        </div>

        <div className="info-section">
          <h3>Movement</h3>
        </div>

        <div className="info-item">
          <span className="label">Velocity</span>
          <span className="value">
            {velocity.ms}
            <br />
            <span className="secondary">{velocity.knots}</span>
          </span>
        </div>
        <div className="info-item">
          <span className="label">Heading</span>
          <span className="value">{Math.round(aircraft.trueTrack)}°</span>
        </div>
        <div className="info-item">
          <span className="label">Vertical Rate</span>
          <span className="value">
            {aircraft.verticalRate > 0 ? '+' : ''}
            {Math.round(aircraft.verticalRate)} m/s
          </span>
        </div>
      </div>
    </div>
  )
}

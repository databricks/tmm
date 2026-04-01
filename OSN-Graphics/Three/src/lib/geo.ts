import * as THREE from 'three'

const DEG_TO_RAD = Math.PI / 180
const EARTH_RADIUS = 1 // Normalized globe radius

/**
 * Convert latitude/longitude/altitude to 3D Cartesian coordinates
 * @param lat Latitude in degrees
 * @param lon Longitude in degrees
 * @param altitude Altitude in meters
 * @param altitudeScale Scale factor for altitude visualization
 * @returns THREE.Vector3 position
 */
export function latLonAltToCartesian(
  lat: number,
  lon: number,
  altitude: number,
  altitudeScale: number = 1
): THREE.Vector3 {
  const phi = (90 - lat) * DEG_TO_RAD
  const theta = (lon + 180) * DEG_TO_RAD

  // Convert altitude from meters to globe units
  // Earth radius ~6371km, so 1m = 1/6371000 globe units
  // We exaggerate altitude for visibility
  const altitudeInGlobeUnits = (altitude / 6371000) * altitudeScale
  const r = EARTH_RADIUS + altitudeInGlobeUnits

  const x = -r * Math.sin(phi) * Math.cos(theta)
  const y = r * Math.cos(phi)
  const z = r * Math.sin(phi) * Math.sin(theta)

  return new THREE.Vector3(x, y, z)
}

/**
 * Get surface position (altitude = 0) for tether lines
 */
export function latLonToCartesian(lat: number, lon: number): THREE.Vector3 {
  return latLonAltToCartesian(lat, lon, 0, 1)
}

/**
 * Convert true track (heading) to rotation quaternion for aircraft orientation
 * @param lat Latitude in degrees
 * @param lon Longitude in degrees
 * @param trueTrack True track in degrees (0 = north, 90 = east)
 */
export function getAircraftOrientation(
  lat: number,
  lon: number,
  trueTrack: number
): THREE.Quaternion {
  const position = latLonToCartesian(lat, lon)
  const up = position.clone().normalize()

  // Calculate north direction at this point
  const northPole = new THREE.Vector3(0, 1, 0)
  const north = northPole.clone().sub(up.clone().multiplyScalar(up.dot(northPole))).normalize()

  // Calculate east direction
  const east = new THREE.Vector3().crossVectors(up, north).normalize()

  // Rotate by true track
  const trackRad = trueTrack * DEG_TO_RAD
  const heading = north.clone().multiplyScalar(Math.cos(trackRad))
    .add(east.clone().multiplyScalar(Math.sin(trackRad)))

  // Create rotation matrix
  const matrix = new THREE.Matrix4()
  const tangent = heading
  const binormal = new THREE.Vector3().crossVectors(up, tangent).normalize()

  matrix.makeBasis(binormal, up, tangent)

  const quaternion = new THREE.Quaternion()
  quaternion.setFromRotationMatrix(matrix)

  return quaternion
}

/**
 * Format altitude in meters and feet
 */
export function formatAltitude(meters: number): { meters: string; feet: string } {
  const feet = meters * 3.28084
  return {
    meters: `${Math.round(meters).toLocaleString()} m`,
    feet: `${Math.round(feet).toLocaleString()} ft`,
  }
}

/**
 * Format velocity in m/s and knots
 */
export function formatVelocity(ms: number): { ms: string; knots: string } {
  const knots = ms * 1.94384
  return {
    ms: `${Math.round(ms).toLocaleString()} m/s`,
    knots: `${Math.round(knots).toLocaleString()} kts`,
  }
}

/**
 * Format coordinates
 */
export function formatCoordinate(value: number, type: 'lat' | 'lon'): string {
  const abs = Math.abs(value)
  const deg = Math.floor(abs)
  const min = ((abs - deg) * 60).toFixed(2)
  const dir = type === 'lat' ? (value >= 0 ? 'N' : 'S') : value >= 0 ? 'E' : 'W'
  return `${deg}° ${min}' ${dir}`
}

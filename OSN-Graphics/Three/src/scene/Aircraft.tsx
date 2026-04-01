import { useRef, useMemo, useEffect } from 'react'
import * as THREE from 'three'
import { Line2 } from 'three/addons/lines/Line2.js'
import { LineMaterial } from 'three/addons/lines/LineMaterial.js'
import { LineGeometry } from 'three/addons/lines/LineGeometry.js'
import type { Aircraft as AircraftType } from '../types'
import { latLonAltToCartesian, latLonToCartesian } from '../lib/geo'
import { getCountryCentroid } from '../lib/countries'

// Create airplane-shaped texture for points
function createAirplaneTexture(): THREE.Texture {
  const size = 64
  const canvas = document.createElement('canvas')
  canvas.width = size
  canvas.height = size
  const ctx = canvas.getContext('2d')!

  const cx = size / 2
  const cy = size / 2

  ctx.fillStyle = 'white'

  // Fuselage (elongated body)
  ctx.beginPath()
  ctx.ellipse(cx, cy, 6, 20, 0, 0, Math.PI * 2)
  ctx.fill()

  // Main wings
  ctx.beginPath()
  ctx.moveTo(cx - 24, cy + 4)
  ctx.lineTo(cx + 24, cy + 4)
  ctx.lineTo(cx + 20, cy - 2)
  ctx.lineTo(cx - 20, cy - 2)
  ctx.closePath()
  ctx.fill()

  // Tail wings
  ctx.beginPath()
  ctx.moveTo(cx - 10, cy + 16)
  ctx.lineTo(cx + 10, cy + 16)
  ctx.lineTo(cx + 8, cy + 12)
  ctx.lineTo(cx - 8, cy + 12)
  ctx.closePath()
  ctx.fill()

  // Nose
  ctx.beginPath()
  ctx.moveTo(cx, cy - 24)
  ctx.lineTo(cx - 4, cy - 16)
  ctx.lineTo(cx + 4, cy - 16)
  ctx.closePath()
  ctx.fill()

  const texture = new THREE.CanvasTexture(canvas)
  texture.needsUpdate = true
  return texture
}

interface AircraftProps {
  aircraft: AircraftType[]
  altitudeScale: number
  selectedIcao: string | null
  arcMode: 'none' | 'trajectory' | 'origin'
  onSelect: (icao: string | null) => void
  onHover: (icao: string | null) => void
}

// Rainbow color based on altitude
function getAltitudeColor(altitude: number, onGround: boolean): THREE.Color {
  if (onGround) return new THREE.Color('#ffffff')

  const maxAlt = 13000
  const t = Math.min(Math.max(altitude, 0) / maxAlt, 1)

  const color = new THREE.Color()
  color.setHSL(t * 0.75, 1, 0.5)

  return color
}

// Create a curved great-circle arc between two points
function createGreatCircleArc(
  startLat: number,
  startLon: number,
  endLat: number,
  endLon: number,
  arcHeight: number,
  altitudeScale: number,
  segments: number = 50
): THREE.Vector3[] {
  const points: THREE.Vector3[] = []

  for (let i = 0; i <= segments; i++) {
    const t = i / segments

    // Spherical linear interpolation (slerp) for great circle
    const lat = startLat + (endLat - startLat) * t
    const lon = startLon + (endLon - startLon) * t

    // Arc height peaks in the middle (sine curve)
    const heightMultiplier = Math.sin(t * Math.PI)
    const altitude = arcHeight * heightMultiplier

    const pos = latLonAltToCartesian(lat, lon, altitude, altitudeScale)
    points.push(pos)
  }

  return points
}

// Create trajectory arc following current heading
function createTrajectoryArc(
  lat: number,
  lon: number,
  altitude: number,
  heading: number,
  velocity: number,
  verticalRate: number,
  altitudeScale: number,
  segments: number = 40
): THREE.Vector3[] {
  const points: THREE.Vector3[] = []

  // Project forward ~25 minutes of flight
  const flightMinutes = 25
  const headingRad = heading * Math.PI / 180

  for (let i = 0; i <= segments; i++) {
    const t = i / segments
    const timeSeconds = t * flightMinutes * 60

    // Calculate distance traveled
    const distanceKm = (velocity * timeSeconds) / 1000
    const distanceDeg = distanceKm / 111 // ~111km per degree at equator

    // Apply heading to get lat/lon deltas
    const deltaLat = Math.cos(headingRad) * distanceDeg
    const cosLat = Math.cos(lat * Math.PI / 180)
    const deltaLon = (Math.sin(headingRad) * distanceDeg) / Math.max(cosLat, 0.1)

    const newLat = Math.max(-85, Math.min(85, lat + deltaLat))
    const newLon = lon + deltaLon
    const newAlt = Math.max(0, altitude + verticalRate * timeSeconds)

    const pos = latLonAltToCartesian(newLat, newLon, newAlt, altitudeScale)
    points.push(pos)
  }

  return points
}

const airplaneTexture = createAirplaneTexture()

export function AircraftMarkers({
  aircraft,
  altitudeScale,
  selectedIcao,
  arcMode,
}: AircraftProps) {
  const pointsRef = useRef<THREE.Points>(null)
  const selectedRef = useRef<THREE.Mesh>(null)

  const selectedAircraft = useMemo(() => {
    return selectedIcao ? aircraft.find(ac => ac.icao24 === selectedIcao) ?? null : null
  }, [aircraft, selectedIcao])

  const geometry = useMemo(() => {
    const positions: number[] = []
    const colors: number[] = []

    aircraft.forEach((ac) => {
      const pos = latLonAltToCartesian(ac.latitude, ac.longitude, ac.altitude, altitudeScale)
      positions.push(pos.x, pos.y, pos.z)

      const color = ac.icao24 === selectedIcao
        ? new THREE.Color('#00ff00')
        : getAltitudeColor(ac.altitude, ac.onGround)
      colors.push(color.r, color.g, color.b)
    })

    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
    geo.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3))

    return geo
  }, [aircraft, altitudeScale, selectedIcao])

  useEffect(() => {
    if (selectedRef.current && selectedAircraft) {
      const pos = latLonAltToCartesian(
        selectedAircraft.latitude,
        selectedAircraft.longitude,
        selectedAircraft.altitude,
        altitudeScale
      )
      selectedRef.current.position.copy(pos)
    }
  }, [selectedAircraft, altitudeScale])

  if (aircraft.length === 0) return null

  return (
    <>
      <points ref={pointsRef} geometry={geometry}>
        <pointsMaterial
          size={0.04}
          vertexColors
          sizeAttenuation
          transparent
          opacity={1}
          map={airplaneTexture}
          alphaTest={0.3}
        />
      </points>

      {selectedAircraft && (
        <mesh ref={selectedRef}>
          <sphereGeometry args={[0.025, 16, 16]} />
          <meshBasicMaterial color="#00ff00" />
        </mesh>
      )}

      {arcMode === 'trajectory' && <TrajectoryArcs aircraft={aircraft} altitudeScale={altitudeScale} />}
      {arcMode === 'origin' && <OriginArcs aircraft={aircraft} altitudeScale={altitudeScale} />}
    </>
  )
}

interface ArcsProps {
  aircraft: AircraftType[]
  altitudeScale: number
}

function TrajectoryArcs({ aircraft, altitudeScale }: ArcsProps) {
  const group = useMemo(() => {
    const g = new THREE.Group()

    const airborne = aircraft.filter(ac => !ac.onGround && ac.velocity > 10)

    // Limit for performance
    const maxArcs = 1500
    const step = Math.max(1, Math.floor(airborne.length / maxArcs))

    const material = new THREE.LineBasicMaterial({
      color: '#00ffff',
      transparent: true,
      opacity: 0.7,
    })

    const coneMaterial = new THREE.MeshBasicMaterial({ color: '#00ffff' })
    const coneGeometry = new THREE.ConeGeometry(0.006, 0.018, 6)

    for (let i = 0; i < airborne.length; i += step) {
      const ac = airborne[i]

      const arcPoints = createTrajectoryArc(
        ac.latitude,
        ac.longitude,
        ac.altitude,
        ac.trueTrack,
        ac.velocity,
        ac.verticalRate,
        altitudeScale
      )

      if (arcPoints.length > 1) {
        const lineGeometry = new THREE.BufferGeometry().setFromPoints(arcPoints)
        const line = new THREE.Line(lineGeometry, material)
        g.add(line)

        // Arrow at end
        const endPos = arcPoints[arcPoints.length - 1]
        const prevPos = arcPoints[arcPoints.length - 2]
        const cone = new THREE.Mesh(coneGeometry, coneMaterial)
        cone.position.copy(endPos)

        const direction = endPos.clone().sub(prevPos).normalize()
        const quaternion = new THREE.Quaternion()
        quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction)
        cone.quaternion.copy(quaternion)

        g.add(cone)
      }
    }

    return g
  }, [aircraft, altitudeScale])

  return <primitive object={group} />
}

function OriginArcs({ aircraft, altitudeScale }: ArcsProps) {
  const group = useMemo(() => {
    const g = new THREE.Group()

    const airborne = aircraft.filter(ac => !ac.onGround && ac.originCountry)

    // Limit for performance
    const maxArcs = 800
    const step = Math.max(1, Math.floor(airborne.length / maxArcs))

    // Thick line material
    const material = new LineMaterial({
      color: 0xff8800,
      linewidth: 3, // pixels
      transparent: true,
      opacity: 0.6,
      resolution: new THREE.Vector2(window.innerWidth, window.innerHeight),
    })

    for (let i = 0; i < airborne.length; i += step) {
      const ac = airborne[i]
      const origin = getCountryCentroid(ac.originCountry)

      if (origin) {
        const [originLat, originLon] = origin

        // Arc height based on distance (longer = higher arc)
        const latDiff = Math.abs(ac.latitude - originLat)
        const lonDiff = Math.abs(ac.longitude - originLon)
        const distance = Math.sqrt(latDiff * latDiff + lonDiff * lonDiff)
        const arcHeight = Math.min(distance * 200, ac.altitude * 1.5)

        const arcPoints = createGreatCircleArc(
          originLat,
          originLon,
          ac.latitude,
          ac.longitude,
          arcHeight,
          altitudeScale,
          40
        )

        if (arcPoints.length > 1) {
          // Convert to flat array for LineGeometry
          const positions: number[] = []
          arcPoints.forEach(p => positions.push(p.x, p.y, p.z))

          const lineGeometry = new LineGeometry()
          lineGeometry.setPositions(positions)

          const line = new Line2(lineGeometry, material)
          line.computeLineDistances()
          g.add(line)
        }
      }
    }

    return g
  }, [aircraft, altitudeScale])

  return <primitive object={group} />
}

interface TetherLineProps {
  aircraft: AircraftType
  altitudeScale: number
}

export function TetherLine({ aircraft, altitudeScale }: TetherLineProps) {
  const line = useMemo(() => {
    const surfacePos = latLonToCartesian(aircraft.latitude, aircraft.longitude)
    const aircraftPos = latLonAltToCartesian(
      aircraft.latitude,
      aircraft.longitude,
      aircraft.altitude,
      altitudeScale
    )

    const points = [surfacePos, aircraftPos]
    const geometry = new THREE.BufferGeometry().setFromPoints(points)
    const material = new THREE.LineBasicMaterial({ color: '#00ff00', transparent: true, opacity: 0.8 })
    return new THREE.Line(geometry, material)
  }, [aircraft, altitudeScale])

  return <primitive object={line} />
}

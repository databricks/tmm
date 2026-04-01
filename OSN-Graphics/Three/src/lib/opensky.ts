import type { Aircraft, OpenSkyResponse } from '../types'

// OpenSky state vector indices
const INDEX = {
  ICAO24: 0,
  CALLSIGN: 1,
  ORIGIN_COUNTRY: 2,
  LONGITUDE: 5,
  LATITUDE: 6,
  BARO_ALTITUDE: 7,
  ON_GROUND: 8,
  VELOCITY: 9,
  TRUE_TRACK: 10,
  VERTICAL_RATE: 11,
  GEO_ALTITUDE: 13,
} as const

export async function fetchAircraftStates(): Promise<{
  aircraft: Aircraft[]
  totalRecords: number
}> {
  const response = await fetch('/api/opensky/states/all')

  if (!response.ok) {
    throw new Error(`OpenSky API error: ${response.status} ${response.statusText}`)
  }

  const data: OpenSkyResponse = await response.json()

  if (!data.states) {
    return { aircraft: [], totalRecords: 0 }
  }

  const totalRecords = data.states.length
  const aircraft = parseStates(data.states)

  return { aircraft, totalRecords }
}

function parseStates(states: (string | number | boolean | null)[][]): Aircraft[] {
  const aircraft: Aircraft[] = []

  for (const state of states) {
    const parsed = parseState(state)
    if (parsed) {
      aircraft.push(parsed)
    }
  }

  return aircraft
}

function parseState(state: (string | number | boolean | null)[]): Aircraft | null {
  const longitude = state[INDEX.LONGITUDE]
  const latitude = state[INDEX.LATITUDE]

  // Skip entries with invalid position
  if (
    longitude === null ||
    latitude === null ||
    typeof longitude !== 'number' ||
    typeof latitude !== 'number' ||
    !isFinite(longitude) ||
    !isFinite(latitude)
  ) {
    return null
  }

  const geoAltitude = parseNumber(state[INDEX.GEO_ALTITUDE])
  const baroAltitude = parseNumber(state[INDEX.BARO_ALTITUDE])
  const altitude = geoAltitude ?? baroAltitude ?? 0

  return {
    icao24: String(state[INDEX.ICAO24] ?? '').toLowerCase(),
    callsign: String(state[INDEX.CALLSIGN] ?? '').trim(),
    originCountry: String(state[INDEX.ORIGIN_COUNTRY] ?? ''),
    longitude,
    latitude,
    altitude,
    onGround: Boolean(state[INDEX.ON_GROUND]),
    velocity: parseNumber(state[INDEX.VELOCITY]) ?? 0,
    trueTrack: parseNumber(state[INDEX.TRUE_TRACK]) ?? 0,
    verticalRate: parseNumber(state[INDEX.VERTICAL_RATE]) ?? 0,
    geoAltitude,
    baroAltitude,
  }
}

function parseNumber(value: unknown): number | null {
  if (value === null || value === undefined) return null
  const num = Number(value)
  return isFinite(num) ? num : null
}

export interface Aircraft {
  icao24: string
  callsign: string
  originCountry: string
  longitude: number
  latitude: number
  altitude: number
  onGround: boolean
  velocity: number
  trueTrack: number
  verticalRate: number
  geoAltitude: number | null
  baroAltitude: number | null
}

export interface OpenSkyResponse {
  time: number
  states: (string | number | boolean | null)[][] | null
}

export interface AppState {
  aircraft: Aircraft[]
  loading: boolean
  error: string | null
  lastUpdated: Date | null
  totalRecords: number
}

import { useState, useEffect, useCallback } from 'react'
import { Scene } from './scene/Scene'
import { ControlPanel } from './components/ControlPanel'
import { AircraftInfo } from './components/AircraftInfo'
import { fetchAircraftStates } from './lib/opensky'
import type { Aircraft } from './types'
import './App.css'

function App() {
  const [aircraft, setAircraft] = useState<Aircraft[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [totalRecords, setTotalRecords] = useState(0)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  const [altitudeScale, setAltitudeScale] = useState(1000)
  const [autoRotate, setAutoRotate] = useState(true)
  const [arcMode, setArcMode] = useState<'none' | 'trajectory' | 'origin'>('trajectory')
  const [selectedIcao, setSelectedIcao] = useState<string | null>(null)
  const [hoveredIcao, setHoveredIcao] = useState<string | null>(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const { aircraft: data, totalRecords: total } = await fetchAircraftStates()
      setAircraft(data)
      setTotalRecords(total)
      setLastUpdated(new Date())
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch aircraft data'
      setError(message)
      console.error('Error fetching aircraft:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  // Initial load
  useEffect(() => {
    loadData()
  }, [loadData])

  const selectedAircraft = selectedIcao
    ? aircraft.find((ac) => ac.icao24 === selectedIcao) ?? null
    : null

  const hoveredAircraft = hoveredIcao
    ? aircraft.find((ac) => ac.icao24 === hoveredIcao) ?? null
    : null

  return (
    <div className="app">
      <Scene
        aircraft={aircraft}
        altitudeScale={altitudeScale}
        autoRotate={autoRotate}
        arcMode={arcMode}
        selectedIcao={selectedIcao}
        onSelect={setSelectedIcao}
        onHover={setHoveredIcao}
      />

      <ControlPanel
        loading={loading}
        error={error}
        totalRecords={totalRecords}
        renderedCount={aircraft.length}
        altitudeScale={altitudeScale}
        autoRotate={autoRotate}
        arcMode={arcMode}
        lastUpdated={lastUpdated}
        onRefresh={loadData}
        onAltitudeScaleChange={setAltitudeScale}
        onAutoRotateChange={setAutoRotate}
        onArcModeChange={setArcMode}
      />

      <AircraftInfo
        aircraft={selectedAircraft}
        onClose={() => setSelectedIcao(null)}
      />

      {hoveredAircraft && !selectedAircraft && (
        <div className="hover-tooltip">
          <strong>{hoveredAircraft.callsign || hoveredAircraft.icao24}</strong>
          <span>{hoveredAircraft.originCountry}</span>
          <span>{Math.round(hoveredAircraft.altitude).toLocaleString()} m</span>
        </div>
      )}
    </div>
  )
}

export default App

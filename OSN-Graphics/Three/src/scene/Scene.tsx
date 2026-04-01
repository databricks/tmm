import { Canvas } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import { Globe } from './Globe'
import { AircraftMarkers, TetherLine } from './Aircraft'
import type { Aircraft } from '../types'

interface SceneProps {
  aircraft: Aircraft[]
  altitudeScale: number
  autoRotate: boolean
  arcMode: 'none' | 'trajectory' | 'origin'
  selectedIcao: string | null
  onSelect: (icao: string | null) => void
  onHover: (icao: string | null) => void
}

export function Scene({
  aircraft,
  altitudeScale,
  autoRotate,
  arcMode,
  selectedIcao,
  onSelect,
  onHover,
}: SceneProps) {
  const selectedAircraft = selectedIcao
    ? aircraft.find((ac) => ac.icao24 === selectedIcao)
    : null

  return (
    <Canvas
      camera={{ position: [0, 0, 3], fov: 45 }}
      style={{ background: 'linear-gradient(to bottom, #1a3a5c, #0d2035)' }}
    >
      <ambientLight intensity={4} />
      <directionalLight position={[5, 3, 5]} intensity={4} />
      <directionalLight position={[-5, -3, -5]} intensity={3} />
      <directionalLight position={[0, 5, 0]} intensity={2} />
      <hemisphereLight args={['#87ceeb', '#1a3a5c', 2]} />

      <Globe autoRotate={autoRotate && !selectedIcao}>
        <AircraftMarkers
          aircraft={aircraft}
          altitudeScale={altitudeScale}
          selectedIcao={selectedIcao}
          arcMode={arcMode}
          onSelect={onSelect}
          onHover={onHover}
        />

        {selectedAircraft && (
          <TetherLine aircraft={selectedAircraft} altitudeScale={altitudeScale} />
        )}
      </Globe>

      <OrbitControls
        enablePan={true}
        minDistance={1.1}
        maxDistance={20}
        enableDamping
        dampingFactor={0.05}
      />
    </Canvas>
  )
}

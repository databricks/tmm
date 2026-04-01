import { useRef, useMemo, Suspense } from 'react'
import type { ReactNode } from 'react'
import { useFrame, useLoader } from '@react-three/fiber'
import * as THREE from 'three'

// NASA Blue Marble texture
const EARTH_TEXTURE_URL = 'https://unpkg.com/three-globe@2.31.1/example/img/earth-blue-marble.jpg'

interface GlobeProps {
  autoRotate: boolean
  children?: ReactNode
}

export function Globe({ autoRotate, children }: GlobeProps) {
  const globeRef = useRef<THREE.Group>(null)

  useFrame((_, delta) => {
    if (autoRotate && globeRef.current) {
      globeRef.current.rotation.y += delta * 0.05
    }
  })

  return (
    <group ref={globeRef}>
      <Suspense fallback={<FallbackEarth />}>
        <Earth />
      </Suspense>
      <Atmosphere />
      <Graticule />
      {children}
    </group>
  )
}

function Earth() {
  const texture = useLoader(THREE.TextureLoader, EARTH_TEXTURE_URL)
  const geometry = useMemo(() => new THREE.SphereGeometry(1, 64, 64), [])

  return (
    <mesh geometry={geometry}>
      <meshStandardMaterial
        map={texture}
        roughness={0.8}
        metalness={0.1}
      />
    </mesh>
  )
}

function FallbackEarth() {
  const geometry = useMemo(() => new THREE.SphereGeometry(1, 64, 64), [])

  return (
    <mesh geometry={geometry}>
      <meshStandardMaterial
        color="#1a4d7c"
        roughness={0.8}
        metalness={0.1}
      />
    </mesh>
  )
}

function Atmosphere() {
  const geometry = useMemo(() => new THREE.SphereGeometry(1.02, 64, 64), [])

  return (
    <mesh geometry={geometry}>
      <meshBasicMaterial
        color="#4fa8ff"
        transparent
        opacity={0.1}
        side={THREE.BackSide}
      />
    </mesh>
  )
}

function Graticule() {
  const lines = useMemo(() => {
    const lineObjects: THREE.Line[] = []
    const material = new THREE.LineBasicMaterial({
      color: '#ffffff',
      transparent: true,
      opacity: 0.15
    })

    // Latitude lines (every 30 degrees)
    for (let lat = -60; lat <= 60; lat += 30) {
      const points: THREE.Vector3[] = []
      const phi = (90 - lat) * (Math.PI / 180)

      for (let lon = 0; lon <= 360; lon += 5) {
        const theta = lon * (Math.PI / 180)
        const x = -1.003 * Math.sin(phi) * Math.cos(theta)
        const y = 1.003 * Math.cos(phi)
        const z = 1.003 * Math.sin(phi) * Math.sin(theta)
        points.push(new THREE.Vector3(x, y, z))
      }

      const geometry = new THREE.BufferGeometry().setFromPoints(points)
      lineObjects.push(new THREE.Line(geometry, material))
    }

    // Longitude lines (every 30 degrees)
    for (let lon = 0; lon < 360; lon += 30) {
      const points: THREE.Vector3[] = []
      const theta = lon * (Math.PI / 180)

      for (let lat = -90; lat <= 90; lat += 5) {
        const phi = (90 - lat) * (Math.PI / 180)
        const x = -1.003 * Math.sin(phi) * Math.cos(theta)
        const y = 1.003 * Math.cos(phi)
        const z = 1.003 * Math.sin(phi) * Math.sin(theta)
        points.push(new THREE.Vector3(x, y, z))
      }

      const geometry = new THREE.BufferGeometry().setFromPoints(points)
      lineObjects.push(new THREE.Line(geometry, material))
    }

    return lineObjects
  }, [])

  return (
    <group>
      {lines.map((line, i) => (
        <primitive key={i} object={line} />
      ))}
    </group>
  )
}

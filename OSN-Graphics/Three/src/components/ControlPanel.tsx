import { formatDistanceToNow } from '../lib/format'

interface ControlPanelProps {
  loading: boolean
  error: string | null
  totalRecords: number
  renderedCount: number
  altitudeScale: number
  autoRotate: boolean
  arcMode: 'none' | 'trajectory' | 'origin'
  lastUpdated: Date | null
  onRefresh: () => void
  onAltitudeScaleChange: (scale: number) => void
  onAutoRotateChange: (rotate: boolean) => void
  onArcModeChange: (mode: 'none' | 'trajectory' | 'origin') => void
}

export function ControlPanel({
  loading,
  error,
  totalRecords,
  renderedCount,
  altitudeScale,
  autoRotate,
  arcMode,
  lastUpdated,
  onRefresh,
  onAltitudeScaleChange,
  onAutoRotateChange,
  onArcModeChange,
}: ControlPanelProps) {
  return (
    <div className="control-panel">
      <h1>OpenSky Live</h1>

      {error && <div className="error">{error}</div>}

      <div className="stats">
        <div className="stat">
          <span className="label">Total records:</span>
          <span className="value">{totalRecords.toLocaleString()}</span>
        </div>
        <div className="stat">
          <span className="label">Rendered:</span>
          <span className="value">{renderedCount.toLocaleString()}</span>
        </div>
        {lastUpdated && (
          <div className="stat">
            <span className="label">Updated:</span>
            <span className="value">{formatDistanceToNow(lastUpdated)}</span>
          </div>
        )}
      </div>

      <div className="controls">
        <button onClick={onRefresh} disabled={loading} className="refresh-btn">
          {loading ? 'Loading...' : 'Refresh'}
        </button>

        <div className="slider-group">
          <label>
            Altitude Scale: {altitudeScale}x
            <input
              type="range"
              min="50"
              max="5000"
              step="100"
              value={altitudeScale}
              onChange={(e) => onAltitudeScaleChange(Number(e.target.value))}
            />
          </label>
        </div>

        <div className="checkbox-group">
          <label>
            <input
              type="checkbox"
              checked={autoRotate}
              onChange={(e) => onAutoRotateChange(e.target.checked)}
            />
            Auto-rotate
          </label>
        </div>

        <div className="radio-group">
          <span className="radio-label">Flight paths:</span>
          <label>
            <input
              type="radio"
              name="arcMode"
              checked={arcMode === 'none'}
              onChange={() => onArcModeChange('none')}
            />
            None
          </label>
          <label>
            <input
              type="radio"
              name="arcMode"
              checked={arcMode === 'trajectory'}
              onChange={() => onArcModeChange('trajectory')}
            />
            Trajectory (cyan)
          </label>
          <label>
            <input
              type="radio"
              name="arcMode"
              checked={arcMode === 'origin'}
              onChange={() => onArcModeChange('origin')}
            />
            From origin (orange)
          </label>
        </div>
      </div>

      <div className="legend">
        <h3>Altitude</h3>
        <div className="altitude-scale">
          <div className="scale-bar" />
          <div className="scale-labels">
            <span>0m</span>
            <span>7.5km</span>
            <span>13km+</span>
          </div>
        </div>
        <div className="legend-item">
          <span className="color-dot ground" />
          <span>On Ground</span>
        </div>
        <div className="legend-item">
          <span className="color-dot selected" />
          <span>Selected</span>
        </div>
      </div>

      <div className="instructions">
        <p>Click aircraft to select. Drag to rotate globe.</p>
      </div>
    </div>
  )
}

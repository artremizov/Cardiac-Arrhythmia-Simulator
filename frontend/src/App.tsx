import { useEffect, useState } from 'react'
import type { Presets, SimResponse, Tab } from './types'
import { getPresets, simulate } from './api'
import { Sidebar } from './components/Sidebar'
import { MetricsRow } from './components/MetricsRow'
import { MonitorChart } from './components/MonitorChart'
import { PVLoopChart } from './components/PVLoopChart'
import { AllVarsChart } from './components/AllVarsChart'
import { ExportPanel } from './components/ExportPanel'

const CAT_COLOR: Record<string, string> = {
  normal: '#059669', arrhythmia: '#d97706', structural: '#2563eb', critical: '#dc2626',
}

export default function App() {
  const [presets, setPresets]           = useState<Presets>({})
  const [preset,  setPreset]            = useState('Healthy Adult')
  const [comparePreset, setComparePreset] = useState('Heart Failure (Systolic)')
  const [compareMode,   setCompareMode]   = useState(false)
  const [hr,       setHr]       = useState(75)
  const [contract, setContract] = useState(100)
  const [resist,   setResist]   = useState(1.0)
  const [compl,    setCompl]    = useState(1.46)
  const [duration, setDuration] = useState(6.0)
  const [plotWindow, setPlotWindow] = useState(2.5)
  const [simData, setSimData]   = useState<SimResponse | null>(null)
  const [loading, setLoading]   = useState(false)
  const [error,   setError]     = useState<string | null>(null)
  const [tab, setTab]           = useState<Tab>('monitor')

  useEffect(() => {
    getPresets().then(setPresets).catch(console.error)
  }, [])

  useEffect(() => {
    const info = presets[preset]
    if (info) { setHr(info.hr); setContract(info.contract); setResist(info.resist); setCompl(info.compl) }
  }, [preset, presets])

  useEffect(() => {
    setPlotWindow(pw => Math.min(pw, duration))
  }, [duration])

  const runSimulation = async () => {
    setLoading(true); setError(null)
    try {
      const result = await simulate({ preset, hr, contract, resist, compl, duration,
        compare_preset: compareMode ? comparePreset : undefined })
      setSimData(result); setTab('monitor')
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  const r1 = simData?.primary ?? null
  const r2 = (compareMode && simData?.comparison) ? simData.comparison : null
  const presetInfo = presets[preset]
  const presetCat  = presetInfo?.category ?? 'normal'
  const presetCol  = CAT_COLOR[presetCat] ?? '#64748b'

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      <Sidebar
        presets={presets} preset={preset} onPresetChange={setPreset}
        compareMode={compareMode} onCompareModeChange={setCompareMode}
        comparePreset={comparePreset} onComparePresetChange={setComparePreset}
        hr={hr} onHrChange={setHr} contract={contract} onContractChange={setContract}
        resist={resist} onResistChange={setResist} compl={compl} onComplChange={setCompl}
        duration={duration} onDurationChange={setDuration}
        plotWindow={plotWindow} onPlotWindowChange={setPlotWindow}
        onRun={runSimulation} loading={loading} error={error} presetName={preset}
      />

      <main className="main-content">
        {!r1 ? (
          /* Welcome screen */
          <div>
            <div style={{ marginBottom: 32 }}>
              <h1 style={{ fontSize: '1.75rem', fontWeight: 800, letterSpacing: '-0.03em', color: '#111827', marginBottom: 6 }}>
                Cardio<span style={{ color: '#2563eb' }}>Sim</span>
              </h1>
              <p style={{ fontSize: '0.85rem', color: '#6b7280' }}>
                Interactive hemodynamic simulator · 12-ODE closed-loop cardiovascular model
              </p>
            </div>

            <p style={{ fontSize: '0.68rem', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: '#94a3b8', marginBottom: 16 }}>
              Select a preset and click Run Simulation
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              {Object.entries(presets).map(([name, info]) => {
                const col       = CAT_COLOR[info.category] ?? '#64748b'
                const isSelected = preset === name
                return (
                  <button
                    key={name}
                    onClick={() => setPreset(name)}
                    className="preset-gallery-card"
                    style={{
                      textAlign: 'left', padding: '14px 16px', borderRadius: 8,
                      background: isSelected ? col + '08' : '#ffffff',
                      border: `1px solid ${isSelected ? col + '40' : '#e5e7eb'}`,
                      borderLeft: `3px solid ${col}`,
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 5 }}>
                      <span style={{ fontSize: '0.82rem', fontWeight: 600, color: '#111827' }}>{name}</span>
                      <span style={{
                        fontSize: '0.62rem', fontWeight: 600, padding: '2px 7px',
                        borderRadius: 4, background: col + '14', color: col,
                        letterSpacing: '0.04em', textTransform: 'uppercase',
                      }}>{info.category}</span>
                    </div>
                    <p style={{ fontSize: '0.75rem', color: '#6b7280', lineHeight: 1.5,
                      display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                      {info.desc}
                    </p>
                  </button>
                )
              })}
            </div>
          </div>
        ) : (
          /* Results */
          <div>
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ width: 9, height: 9, borderRadius: '50%', background: presetCol, display: 'inline-block', flexShrink: 0 }} />
                <h2 style={{ fontSize: '1rem', fontWeight: 600, color: '#111827' }}>{r1.preset}</h2>
                <span style={{
                  fontSize: '0.62rem', fontWeight: 700, padding: '2px 8px', borderRadius: 4,
                  background: presetCol + '14', color: presetCol,
                  letterSpacing: '0.06em', textTransform: 'uppercase',
                }}>{presetCat}</span>
                {r2 && <span style={{ fontSize: '0.8rem', color: '#9ca3af' }}>vs {r2.preset}</span>}
              </div>
              <button
                onClick={runSimulation} disabled={loading}
                style={{
                  padding: '7px 16px', borderRadius: 6, fontSize: '0.8rem', fontWeight: 600,
                  background: '#eff6ff', color: '#2563eb', border: '1px solid #bfdbfe',
                  cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.6 : 1,
                  transition: 'all 0.12s',
                }}
              >
                {loading ? 'Running…' : `↺ Re-run ${r1.preset}`}
              </button>
            </div>

            <MetricsRow primary={r1} comparison={r2} />

            {/* Tabs */}
            <div className="tab-bar">
              {(['monitor', 'pvloop', 'allvars', 'export'] as Tab[]).map(t => (
                <button key={t} className={`tab-btn ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>
                  {{ monitor: 'Monitor', pvloop: 'PV Loop', allvars: 'All Variables', export: 'Export' }[t]}
                </button>
              ))}
            </div>

            <div className="card" style={{ padding: 20 }}>
              {tab === 'monitor' && <MonitorChart primary={r1} comparison={r2} plotWindow={plotWindow} />}
              {tab === 'pvloop'  && <PVLoopChart  primary={r1} comparison={r2} />}
              {tab === 'allvars' && <AllVarsChart  primary={r1} comparison={r2} plotWindow={plotWindow} />}
              {tab === 'export'  && <ExportPanel   primary={r1} comparison={r2} plotWindow={plotWindow} />}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

import { useEffect, useMemo, useState } from 'react'
import type { Presets, RunParams, SimResponse, Tab } from './types'
import { getPresets, simulate } from './api'
import { Sidebar } from './components/Sidebar'
import { MetricsRow } from './components/MetricsRow'
import { WaveformChart } from './components/WaveformChart'
import { PVLoopChart } from './components/PVLoopChart'
import { AllVarsChart } from './components/AllVarsChart'
import { ExportPanel } from './components/ExportPanel'
import { About } from './components/About'

const TABS: [Tab, string][] = [
  ['waveforms', 'Waveforms'], ['pvloop', 'PV loop'], ['allvars', 'State variables'],
  ['export', 'Export'], ['about', 'About'],
]

export default function App() {
  const [presets, setPresets]             = useState<Presets>({})
  const [preset,  setPreset]              = useState('Healthy Adult')
  const [comparePreset, setComparePreset] = useState('Ventricular Fibrillation')
  const [compareMode,   setCompareMode]   = useState(false)
  const [hr,       setHr]       = useState(75)
  const [contract, setContract] = useState(100)
  const [resist,   setResist]   = useState(1.0)
  const [compl,    setCompl]    = useState(1.46)
  const [duration, setDuration] = useState(6.0)
  const [plotWindow, setPlotWindow] = useState(2.5)
  const [simData, setSimData]   = useState<SimResponse | null>(null)
  const [lastRun, setLastRun]   = useState<RunParams | null>(null)
  const [loading, setLoading]   = useState(false)
  const [error,   setError]     = useState<string | null>(null)
  const [tab, setTab]           = useState<Tab>('waveforms')
  const [elapsed, setElapsed]   = useState<number | null>(null)

  useEffect(() => {
    getPresets().then(setPresets).catch(() => setError('Could not load presets from the server.'))
  }, [])

  const loadPreset = (name: string) => {
    const info = presets[name]
    if (info) { setHr(info.hr); setContract(info.contract); setResist(info.resist); setCompl(info.compl) }
  }
  useEffect(() => { loadPreset(preset) }, [preset, presets])  // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (comparePreset === preset) {
      const other = Object.keys(presets).find(n => n !== preset)
      if (other) setComparePreset(other)
    }
  }, [preset, comparePreset, presets])

  useEffect(() => { setPlotWindow(pw => Math.min(pw, duration)) }, [duration])

  const current: RunParams = useMemo(() => ({
    preset, hr, contract, resist, compl, duration,
    compare_preset: compareMode ? comparePreset : undefined,
  }), [preset, hr, contract, resist, compl, duration, compareMode, comparePreset])

  const info = presets[preset]
  const modified = !!info && (info.hr !== hr || info.contract !== contract || info.resist !== resist || info.compl !== compl)
  const stale = !!lastRun && JSON.stringify(lastRun) !== JSON.stringify(current)

  const runSimulation = async () => {
    setLoading(true); setError(null)
    const t0 = performance.now()
    try {
      const result = await simulate(current)
      setSimData(result); setLastRun(current)
      setElapsed((performance.now() - t0) / 1000)
      if (tab === 'about') setTab('waveforms')
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  const r1 = simData?.primary ?? null
  const r2 = simData?.comparison ?? null

  return (
    <div className="app">
      <Sidebar
        presets={presets} preset={preset} onPresetChange={setPreset}
        modified={modified} onReset={() => loadPreset(preset)}
        compareMode={compareMode} onCompareModeChange={setCompareMode}
        comparePreset={comparePreset} onComparePresetChange={setComparePreset}
        hr={hr} onHrChange={setHr} contract={contract} onContractChange={setContract}
        resist={resist} onResistChange={setResist} compl={compl} onComplChange={setCompl}
        duration={duration} onDurationChange={setDuration}
        plotWindow={plotWindow} onPlotWindowChange={setPlotWindow}
        onRun={runSimulation} loading={loading} error={error}
      />

      <main className="main">
        {r1 && lastRun && (
          <div className="run-info">
            <div className="run-title">
              {r2 ? <>A: {r1.preset}<span className="vs">B: {r2.preset}</span></> : r1.preset}
            </div>
            <div className="run-params">
              {lastRun.preset !== 'Ventricular Fibrillation' && <>HR {lastRun.hr} bpm · </>}
              contractility {lastRun.contract}% · resistance {lastRun.resist.toFixed(2)} mmHg·s/mL ·
              compliance {lastRun.compl.toFixed(2)} mL/mmHg · {lastRun.duration.toFixed(1)} s simulated
              {elapsed != null && <> · computed in {elapsed.toFixed(1)} s</>}
            </div>
            {stale && !loading && <div className="stale">Settings changed since this run. Press Run simulation to update.</div>}
            {loading && <div className="stale">Running…</div>}
          </div>
        )}

        {r1 && <MetricsRow primary={r1} comparison={r2} />}

        <nav className="tabs" role="tablist" aria-label="Views">
          {TABS.map(([id, label]) => (
            <button key={id} type="button" role="tab" aria-selected={tab === id}
                    className={`tab${tab === id ? ' is-active' : ''}`} onClick={() => setTab(id)}>
              {label}
            </button>
          ))}
        </nav>

        <div className="panel" role="tabpanel">
          {tab === 'about' ? <About /> : !r1 ? (
            <div className="empty">
              <p className="empty-title">No results yet</p>
              <p>Choose a preset or set the parameters in the sidebar, then press Run simulation.</p>
            </div>
          ) : (
            <>
              {tab === 'waveforms' && <WaveformChart primary={r1} comparison={r2} plotWindow={plotWindow} />}
              {tab === 'pvloop'    && <PVLoopChart   primary={r1} comparison={r2} />}
              {tab === 'allvars'   && <AllVarsChart  primary={r1} comparison={r2} plotWindow={plotWindow} />}
              {tab === 'export'    && <ExportPanel   primary={r1} comparison={r2} plotWindow={plotWindow} />}
            </>
          )}
        </div>
      </main>
    </div>
  )
}

import type { SimResponse, Presets } from './types'

export async function simulate(params: {
  preset: string
  hr: number
  contract: number
  resist: number
  compl: number
  duration: number
  compare_preset?: string
}): Promise<SimResponse> {
  const res = await fetch('/api/simulate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(err.detail ?? 'Simulation failed')
  }
  return res.json()
}

export async function getPresets(): Promise<Presets> {
  const res = await fetch('/api/presets')
  return res.json()
}

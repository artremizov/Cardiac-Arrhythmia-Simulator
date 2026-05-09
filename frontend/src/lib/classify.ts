export type Status = 'normal' | 'warning' | 'danger'

export function classify(name: string, value: number): Status {
  switch (name) {
    case 'co':
      if (value < 2.5) return 'danger'
      if (value < 4.0) return 'warning'
      return 'normal'
    case 'sys':
      if (value > 160 || value < 80) return 'danger'
      if (value > 140 || value < 90) return 'warning'
      return 'normal'
    case 'dia':
      if (value > 100 || value < 50) return 'danger'
      if (value > 90  || value < 60) return 'warning'
      return 'normal'
    case 'sv':
      if (value < 30) return 'danger'
      if (value < 50) return 'warning'
      return 'normal'
    case 'map':
      if (value < 60 || value > 120) return 'danger'
      if (value < 70 || value > 105) return 'warning'
      return 'normal'
    case 'pp':
      if (value > 80 || value < 20) return 'danger'
      if (value > 60 || value < 25) return 'warning'
      return 'normal'
    default:
      return 'normal'
  }
}

export const STATUS_COLOR: Record<Status, string> = {
  normal:  '#059669',
  warning: '#d97706',
  danger:  '#dc2626',
}

export const STATUS_BG: Record<Status, string> = {
  normal:  '#f0fdf4',
  warning: '#fffbeb',
  danger:  '#fff1f2',
}

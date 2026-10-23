import { SERIES } from './theme'

// The 12 state variables of the Avanzolini (1988) model, in solver order.
// Volumes are reported in mL (1 mL = 1 cm³).
export interface StateVar { id: string; name: string; unit: string; color: string }

export const STATE_VARS: StateVar[] = [
  { id: 'X1',  name: 'Aortic pressure',                unit: 'mmHg', color: SERIES.aorta },
  { id: 'X2',  name: 'Aortic flow',                    unit: 'mL/s', color: SERIES.aorta },
  { id: 'X3',  name: 'Systemic arterial pressure',     unit: 'mmHg', color: SERIES.other },
  { id: 'X4',  name: 'Systemic peripheral flow',       unit: 'mL/s', color: SERIES.other },
  { id: 'X5',  name: 'Systemic venous pressure',       unit: 'mmHg', color: SERIES.venous },
  { id: 'X6',  name: 'Right ventricular volume',       unit: 'mL',   color: SERIES.other },
  { id: 'X7',  name: 'Pulmonary artery pressure',      unit: 'mmHg', color: SERIES.pulm },
  { id: 'X8',  name: 'Pulmonary arterial flow',        unit: 'mL/s', color: SERIES.pulm },
  { id: 'X9',  name: 'Pulmonary arteriolar pressure',  unit: 'mmHg', color: SERIES.other },
  { id: 'X10', name: 'Pulmonary venous flow',          unit: 'mL/s', color: SERIES.other },
  { id: 'X11', name: 'Pulmonary venous / LA pressure', unit: 'mmHg', color: SERIES.other },
  { id: 'X12', name: 'Left ventricular volume',        unit: 'mL',   color: SERIES.lv },
]

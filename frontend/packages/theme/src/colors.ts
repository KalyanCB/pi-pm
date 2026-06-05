/** Bloomberg Terminal Lite — dark-first professional palette */
export const colors = {
  background: '#0a0e14',
  backgroundElevated: '#111820',
  backgroundPanel: '#151d28',
  border: '#1e2a3a',
  borderSubtle: '#162030',

  textPrimary: '#e8edf4',
  textSecondary: '#8b9cb3',
  textMuted: '#5c6d82',
  textMono: '#c5d4e8',

  accent: '#3d8fd1',
  accentMuted: '#2a6aa3',

  positive: '#3dba7a',
  negative: '#e05252',
  warning: '#d4a017',
  danger: '#c0392b',
  info: '#5b9bd5',

  actionBuy: '#3dba7a',
  actionWatch: '#d4a017',
  actionExit: '#e07b39',
  actionReject: '#e05252',

  convictionBlocked: '#5c6d82',
  convictionLow: '#8b9cb3',
  convictionMedium: '#5b9bd5',
  convictionHigh: '#3dba7a',
  convictionExceptional: '#2dd4a8',

  riskLow: '#3dba7a',
  riskMedium: '#d4a017',
  riskHigh: '#e07b39',
  riskCritical: '#c0392b',

  highConcern: '#c0392b',
  highConcernBg: '#2a1515',

  sidebar: '#0d1219',
  sidebarActive: '#1a2838',
} as const;

export type Colors = typeof colors;

export type Action = 'BUY' | 'WATCH' | 'HOLD' | 'EXIT_APPROVED' | 'REJECT';

export type ConvictionBand =
  | 'BLOCKED'
  | 'LOW'
  | 'MEDIUM'
  | 'HIGH'
  | 'EXCEPTIONAL';

export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | 'UNKNOWN';

export type ExitUrgency = 'LOW' | 'NORMAL' | 'HIGH' | 'CRITICAL';

export type ReconciliationStatus = 'PASS' | 'WARNING' | 'FAIL';

export type Breakpoint = 'mobile' | 'tablet' | 'desktop' | 'wide';

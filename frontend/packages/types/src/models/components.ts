import type { Action, ConvictionBand, RiskLevel } from '../enums';
import type { CommitteeAdvisoryOverlay } from '../api/committee';
import type { Citation } from '../api/copilot';
import type { RiskAlert } from '../api/common';

export interface RecommendationCardProps {
  symbol: string;
  action: Action;
  rank: number | null;
  convictionScore: number;
  convictionBand: ConvictionBand;
  reasonCodes: string[];
  committeeAdvisory?: CommitteeAdvisoryOverlay | null;
  layout?: 'card' | 'row';
  onPress?: () => void;
}

export interface PortfolioPositionCardProps {
  symbol: string | null;
  quantity: number;
  avgCost: number;
  marketValue: number | null;
  unrealizedPnl: number | null;
  weightPct: number | null;
  convictionBand: string | null;
  sector: string | null;
  onPress?: () => void;
}

export interface TrustScoreCardProps {
  score: number | null;
  showBreakdown?: boolean;
}

export interface RiskIndicatorProps {
  riskLevel: RiskLevel;
  alerts: RiskAlert[];
  maxAlerts?: number;
  onPress?: () => void;
}

export interface CopilotMessageProps {
  role: 'user' | 'assistant';
  content: string;
  intent?: string | null;
  refused?: boolean;
  citations?: Citation[];
  uncitedClaims?: string[];
}

export interface CitationPanelProps {
  citations: Citation[];
  onPress?: (citation: Citation) => void;
}

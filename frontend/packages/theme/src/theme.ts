import { colors, type Colors } from './colors';
import { typography, type Typography } from './typography';
import { spacing, type Spacing } from './spacing';
import { elevation, type Elevation } from './elevation';

export interface Theme {
  colors: Colors;
  typography: Typography;
  spacing: Spacing;
  elevation: Elevation;
  borderRadius: {
    sm: number;
    md: number;
    lg: number;
  };
  layout: {
    sidebarWidth: number;
    copilotPanelWidth: number;
    maxContentWidth: number;
  };
}

export const darkTheme: Theme = {
  colors,
  typography,
  spacing,
  elevation,
  borderRadius: {
    sm: 4,
    md: 6,
    lg: 8,
  },
  layout: {
    sidebarWidth: 240,
    copilotPanelWidth: 400,
    maxContentWidth: 1440,
  },
};

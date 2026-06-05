import { colors, type Colors } from './colors';
import { typography, type Typography } from './typography';
import { spacing, type Spacing } from './spacing';

export interface Theme {
  colors: Colors;
  typography: Typography;
  spacing: Spacing;
  borderRadius: {
    sm: number;
    md: number;
    lg: number;
  };
}

export const darkTheme: Theme = {
  colors,
  typography,
  spacing,
  borderRadius: {
    sm: 4,
    md: 6,
    lg: 8,
  },
};

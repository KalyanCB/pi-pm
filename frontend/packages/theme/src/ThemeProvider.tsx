import React, { createContext, useContext, useMemo } from 'react';
import { darkTheme, type Theme } from './theme';

const ThemeContext = createContext<Theme>(darkTheme);

export interface ThemeProviderProps {
  children: React.ReactNode;
  theme?: Theme;
}

export function ThemeProvider({ children, theme = darkTheme }: ThemeProviderProps) {
  const value = useMemo(() => theme, [theme]);
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): Theme {
  return useContext(ThemeContext);
}

import type { Breakpoint } from '@pipm/types';

export const breakpoints = {
  mobile: 0,
  tablet: 768,
  desktop: 1024,
  wide: 1440,
} as const;

export function resolveBreakpoint(width: number): Breakpoint {
  if (width >= breakpoints.wide) return 'wide';
  if (width >= breakpoints.desktop) return 'desktop';
  if (width >= breakpoints.tablet) return 'tablet';
  return 'mobile';
}

export function useIsDesktopLayout(width: number): boolean {
  return width >= breakpoints.desktop;
}

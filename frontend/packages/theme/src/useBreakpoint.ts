import { useEffect, useState } from 'react';
import { Dimensions, type ScaledSize } from 'react-native';
import type { Breakpoint } from '@pipm/types';
import { resolveBreakpoint } from './breakpoints';

export interface BreakpointState {
  breakpoint: Breakpoint;
  width: number;
  isDesktop: boolean;
  isMobile: boolean;
}

function getBreakpointFromDimensions(dimensions: ScaledSize): BreakpointState {
  const width = dimensions.width;
  const breakpoint = resolveBreakpoint(width);
  return {
    breakpoint,
    width,
    isDesktop: breakpoint === 'desktop' || breakpoint === 'wide',
    isMobile: breakpoint === 'mobile',
  };
}

export function useBreakpoint(): BreakpointState {
  const [state, setState] = useState(() =>
    getBreakpointFromDimensions(Dimensions.get('window')),
  );

  useEffect(() => {
    const handler = ({ window }: { window: ScaledSize }) => {
      setState(getBreakpointFromDimensions(window));
    };
    const subscription = Dimensions.addEventListener('change', handler);
    return () => subscription.remove();
  }, []);

  return state;
}

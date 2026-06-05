import React from 'react';
import { render, screen } from '@testing-library/react-native';
import { ThemeProvider } from '@pipm/theme';
import { ConvictionBadge } from '../molecules/ConvictionBadge';

function wrap(ui: React.ReactElement) {
  return <ThemeProvider>{ui}</ThemeProvider>;
}

describe('ConvictionBadge', () => {
  it('renders band and score', () => {
    render(wrap(<ConvictionBadge score={82} band="HIGH" />));
    expect(screen.getByText('HIGH')).toBeTruthy();
    expect(screen.getByText('82')).toBeTruthy();
  });

  it('hides score when showScore is false', () => {
    render(wrap(<ConvictionBadge score={82} band="HIGH" showScore={false} />));
    expect(screen.getByText('HIGH')).toBeTruthy();
    expect(screen.queryByText('82')).toBeNull();
  });
});

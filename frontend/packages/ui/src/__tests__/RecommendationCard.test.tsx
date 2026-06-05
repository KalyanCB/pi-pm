import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react-native';
import { ThemeProvider } from '@pipm/theme';
import { RecommendationCard } from '../molecules/RecommendationCard';

function wrap(ui: React.ReactElement) {
  return <ThemeProvider>{ui}</ThemeProvider>;
}

describe('RecommendationCard', () => {
  it('renders symbol and action', () => {
    render(
      wrap(
        <RecommendationCard
          symbol="RELIANCE"
          action="BUY"
          rank={3}
          convictionScore={82}
          convictionBand="HIGH"
          reasonCodes={['RANK_TOP_20']}
        />,
      ),
    );
    expect(screen.getByText('RELIANCE')).toBeTruthy();
    expect(screen.getByText('BUY')).toBeTruthy();
  });

  it('calls onPress when tapped', () => {
    const onPress = jest.fn();
    render(
      wrap(
        <RecommendationCard
          symbol="INFY"
          action="WATCH"
          rank={5}
          convictionScore={65}
          convictionBand="MEDIUM"
          reasonCodes={[]}
          onPress={onPress}
        />,
      ),
    );
    fireEvent.press(screen.getByLabelText('INFY WATCH'));
    expect(onPress).toHaveBeenCalledTimes(1);
  });
});

import { type AppConfig } from '../types';

export const DEFAULT_CONFIG: AppConfig = {
  campaign: {
    id: 'community-center-fund',
    title: 'Community Center Fund',
    raised: 27430,
    goal: 50000,
    description: "We're 55% of the way to building our new center.",
    trustBadge: 'Trusted by 2,000+ donors'
  },
  options: [
    {
      id: 'tier-1',
      amount: 25,
      description: 'Feed a child for a week'
    },
    {
      id: 'tier-2',
      amount: 50,
      description: 'Provide school supplies',
      recommended: true
    },
    {
      id: 'tier-3',
      amount: 100,
      description: 'Support a local teacher'
    }
  ]
};

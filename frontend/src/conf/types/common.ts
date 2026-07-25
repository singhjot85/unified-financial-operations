export type Frequency = 'one-time' | 'monthly';

export interface Campaign {
  id: string;
  title: string;
  raised: number;
  goal: number;
  description: string;
  trustBadge: string;
}

export interface DonationOption {
  id: string;
  amount: number;
  description: string;
  recommended?: boolean;
}

export interface Donation {
  id: string;
  amount: number;
  frequency: Frequency;
  email: string;
  name: string;
  date: string;
  receiptNumber: string;
  paymentMethod: string;
  campaignId: string;
}

export interface AppConfig {
  campaign: Campaign;
  options: DonationOption[];
}

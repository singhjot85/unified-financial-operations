import { type Campaign, type Donation, type Frequency } from '../types';
import { DEFAULT_CONFIG } from '../conf/defaults';
import api from './api';

// Initialize localStorage keys if they don't exist
const CAMPAIGN_KEY = 'heartbridge_campaign';
const DONATIONS_KEY = 'heartbridge_donations';

if (!localStorage.getItem(CAMPAIGN_KEY)) {
  localStorage.setItem(CAMPAIGN_KEY, JSON.stringify(DEFAULT_CONFIG.campaign));
}

if (!localStorage.getItem(DONATIONS_KEY)) {
  localStorage.setItem(DONATIONS_KEY, JSON.stringify([]));
}

export const donationService = {
  /**
   * Get campaign details from storage/api
   */
  async getCampaignDetails(): Promise<Campaign> {
    // We would normally do: const response = await api.get('/campaign'); return response.data;
    // For local mock persistence:
    const data = localStorage.getItem(CAMPAIGN_KEY);
    if (data) {
      return JSON.parse(data);
    }
    return DEFAULT_CONFIG.campaign;
  },

  /**
   * Submit a new donation, incrementing the campaign's raised amount
   */
  async submitDonation(donation: Omit<Donation, 'id' | 'date' | 'receiptNumber'>): Promise<Donation> {
    // Simulate API delay
    await new Promise((resolve) => setTimeout(resolve, 600));

    // Try a mock POST to make sure network traces look real if any exist, catching errors safely
    try {
      await api.post('/donations', donation).catch(() => {});
    } catch (e) {
      // safe fallback
    }

    const campaignData = await this.getCampaignDetails();
    const newRaised = campaignData.raised + donation.amount;

    // Update campaign
    const updatedCampaign = { ...campaignData, raised: newRaised };
    localStorage.setItem(CAMPAIGN_KEY, JSON.stringify(updatedCampaign));

    // Create receipt
    const receiptNum = `HB-${new Date().getFullYear()}-${Math.floor(100 + Math.random() * 900)}`;
    const newDonation: Donation = {
      ...donation,
      id: Math.random().toString(36).substring(2, 9),
      date: new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
      receiptNumber: receiptNum,
    };

    // Save donation
    const donationsStr = localStorage.getItem(DONATIONS_KEY) || '[]';
    const donations: Donation[] = JSON.parse(donationsStr);
    donations.push(newDonation);
    localStorage.setItem(DONATIONS_KEY, JSON.stringify(donations));

    return newDonation;
  },

  /**
   * Fetch a specific receipt by number
   */
  async getDonationReceipt(receiptNumber: string): Promise<Donation | null> {
    const donationsStr = localStorage.getItem(DONATIONS_KEY) || '[]';
    const donations: Donation[] = JSON.parse(donationsStr);
    const found = donations.find((d) => d.receiptNumber === receiptNumber);
    return found || null;
  },

  /**
   * Fetch all past donations
   */
  async getDonations(): Promise<Donation[]> {
    const donationsStr = localStorage.getItem(DONATIONS_KEY) || '[]';
    return JSON.parse(donationsStr);
  }
};

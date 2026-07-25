import { defineStore } from 'pinia';
import type { Campaign, Donation, DonationOption } from '../types';
import { donationService } from '../services/donationService';
import { DEFAULT_CONFIG } from '../conf/defaults';

export const useDonationStore = defineStore('donation', {
  state: () => ({
    campaign: null as Campaign | null,
    options: DEFAULT_CONFIG.options as DonationOption[],
    currentDonation: null as Donation | null,
    loading: false,
    error: null as string | null,
  }),

  getters: {
    campaignProgress(): number {
      if (!this.campaign || this.campaign.goal === 0) return 0;
      const progress = (this.campaign.raised / this.campaign.goal) * 100;
      return Math.min(Math.round(progress), 100);
    },
    formattedRaised(): string {
      if (!this.campaign) return '$0';
      return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(this.campaign.raised);
    },
    formattedGoal(): string {
      if (!this.campaign) return '$0';
      return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(this.campaign.goal);
    }
  },

  actions: {
    async fetchCampaignDetails() {
      this.loading = true;
      this.error = null;
      try {
        this.campaign = await donationService.getCampaignDetails();
      } catch (err: any) {
        this.error = err.message || 'Failed to fetch campaign details';
      } finally {
        this.loading = false;
      }
    },

    async makeDonation(donationData: Omit<Donation, 'id' | 'date' | 'receiptNumber'>) {
      this.loading = true;
      this.error = null;
      try {
        const result = await donationService.submitDonation(donationData);
        this.currentDonation = result;
        // Refresh campaign state
        await this.fetchCampaignDetails();
        return result;
      } catch (err: any) {
        this.error = err.message || 'Failed to submit donation';
        throw err;
      } finally {
        this.loading = false;
      }
    },

    async fetchReceipt(receiptNumber: string) {
      this.loading = true;
      this.error = null;
      try {
        const result = await donationService.getDonationReceipt(receiptNumber);
        if (result) {
          this.currentDonation = result;
        }
        return result;
      } catch (err: any) {
        this.error = err.message || 'Failed to fetch receipt';
        return null;
      } finally {
        this.loading = false;
      }
    }
  }
});

<script setup lang="ts">
import { onMounted } from 'vue';
import { useDonationStore } from '../stores/donation';
import AppBar from '../components/AppBar.vue';
import HeroSection from '../components/HeroSection.vue';
import TieredItems from '../components/TieredItems.vue';
import AppFooter from '../components/AppFooter.vue';

const donationStore = useDonationStore();

onMounted(async () => {
  await donationStore.fetchCampaignDetails();
});
</script>

<template>
  <div class="min-h-screen flex flex-col bg-background">
    <!-- Top Nav Bar -->
    <AppBar />

    <!-- Main Content -->
    <main class="flex-grow flex flex-col items-center">
      <!-- Hero Section banner -->
      <HeroSection />

      <!-- Campaign details and snapshot selection -->
      <section class="w-full max-w-container-max mx-auto px-sm md:px-xl py-xl flex flex-col gap-xl -mt-xl relative z-20">
        <!-- Campaign Snapshot Card -->
        <div class="bg-surface rounded-2xl border border-outline-variant/60 shadow-sm p-8 md:p-10 flex flex-col items-center text-center gap-4">
          <h2 class="text-2xl md:text-3xl font-sans font-bold text-on-surface">
            {{ donationStore.campaign?.title || 'Community Center Fund' }}
          </h2>

          <div class="w-full max-w-[600px] mt-2">
            <!-- Progress numbers -->
            <div class="flex justify-between items-center mb-2.5">
              <span class="text-xs font-bold text-[#00685F]">
                {{ donationStore.formattedRaised }} Raised
              </span>
              <span class="text-xs font-semibold text-on-surface-variant">
                Goal: {{ donationStore.formattedGoal }}
              </span>
            </div>

            <!-- Custom Progress Bar (Pill style) -->
            <div class="w-full h-3 bg-[#EEF2F1] rounded-full overflow-hidden">
              <div
                class="h-full bg-[#00685F] rounded-full transition-all duration-500 ease-out"
                :style="{ width: `${donationStore.campaignProgress}%` }"
              ></div>
            </div>

            <p class="mt-4 text-sm font-sans font-semibold text-on-surface-variant">
              We're {{ donationStore.campaignProgress }}% of the way to building our new center.
            </p>
          </div>

          <!-- Trust badge indicator (Pill badge matching screenshot) -->
          <div class="mt-2 flex items-center gap-2 text-[#00685F] bg-[#E6F7F5] border border-[#00685F]/10 px-4 py-1.5 rounded-full text-xs font-semibold select-none">
            <span class="material-symbols-outlined text-[15px]" style="font-variation-settings: 'FILL' 0; font-weight: 600;">shield_with_heart</span>
            <span>
              {{ donationStore.campaign?.trustBadge || 'Trusted by 2,000+ donors' }}
            </span>
          </div>
        </div>

        <!-- Bento Tiers -->
        <TieredItems />

        <!-- Why Give / Transparent Trust Icons -->
        <div class="border-t border-outline-variant/50 pt-8 mt-4">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-6 items-center">
            <div class="flex flex-col md:flex-row items-center justify-center gap-3 text-center md:text-left">
              <span class="material-symbols-outlined text-[#00685F] text-[32px]">visibility</span>
              <span class="text-sm font-sans font-semibold text-on-surface">100% Transparent Tracking</span>
            </div>

            <div class="flex flex-col md:flex-row items-center justify-center gap-3 text-center md:text-left border-y md:border-y-0 md:border-x border-outline-variant/50 py-4 md:py-0 md:px-4">
              <span class="material-symbols-outlined text-[#00685F] text-[32px]">receipt_long</span>
              <span class="text-sm font-sans font-semibold text-on-surface">Instant Tax Receipts</span>
            </div>

            <div class="flex flex-col md:flex-row items-center justify-center gap-3 text-center md:text-left">
              <span class="material-symbols-outlined text-[#00685F] text-[32px]">lock</span>
              <span class="text-sm font-sans font-semibold text-on-surface">Secure Encrypted Payments</span>
            </div>
          </div>
        </div>
      </section>
    </main>

    <!-- Footer -->
    <AppFooter />
  </div>
</template>

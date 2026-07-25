<script setup lang="ts">
import { useRouter } from 'vue-router';
import { useDonationStore } from '../stores/donation';
import { type DonationOption } from '../conf/types/common';

const router = useRouter();
const donationStore = useDonationStore();

const handleSelectTier = (tier: DonationOption) => {
  // Save pre-fill in store or route with query params
  router.push({ path: '/donate', query: { amount: tier.amount.toString() } });
};

const handleCustomAmount = () => {
  router.push({ path: '/donate', query: { amount: 'custom' } });
};
</script>

<template>
  <div class="flex flex-col gap-8 w-full mt-2">
    <!-- Donation Quick-Select Grid -->
    <div class="flex flex-col md:flex-row gap-6 justify-center items-stretch w-full">
      <div
        v-for="option in donationStore.options"
        :key="option.id"
        @click="handleSelectTier(option)"
        class="flex-1 bg-surface border rounded-xl p-8 flex flex-col items-center justify-center text-center gap-4 hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 cursor-pointer group select-none relative min-h-[180px]"
        :class="[
          option.recommended
            ? 'border-2 border-[#00685F]'
            : 'border-outline-variant/60 hover:border-[#00685F]'
        ]"
      >
        <!-- Recommended Badge -->
        <div
          v-if="option.recommended"
          class="absolute -top-3.5 bg-[#00685F] text-white text-[11px] font-bold px-4 py-1 rounded-full shadow-sm"
        >
          Recommended
        </div>

        <div
          class="text-4xl md:text-5xl font-sans font-bold text-[#00685F]"
          :class="{ 'mt-2': option.recommended }"
        >
          ${{ option.amount }}
        </div>
        <p class="text-sm font-sans text-on-surface-variant max-w-[220px]">
          {{ option.description }}
        </p>
      </div>
    </div>

    <!-- Custom Amount Navigation -->
    <div class="text-center w-full mt-4">
      <a
        @click.prevent="handleCustomAmount"
        class="text-sm font-sans font-semibold text-[#00685F] hover:text-[#004f48] transition-colors cursor-pointer border-b border-[#00685F] hover:border-[#004f48] pb-0.5 inline-block"
        href="#"
      >
        Custom Amount
      </a>
    </div>
  </div>
</template>

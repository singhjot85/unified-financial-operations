<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useDonationStore } from '../stores/donation';
import AppButton from '../components/AppButton.vue';

const router = useRouter();
const donationStore = useDonationStore();

// Dynamic user details with mock fallbacks for testing
const donorName = computed(() => donationStore.currentDonation?.name || 'Alex');
const displayAmount = computed(() => {
  const amt = donationStore.currentDonation?.amount || 100;
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amt);
});
const donationDate = computed(() => donationStore.currentDonation?.date || 'Oct 26, 2024');
const paymentMethod = computed(() => donationStore.currentDonation?.paymentMethod || 'Visa ending in 4242');

// Calculate meals provided (approx $5.00 per meal or 2.5 meals per dollar)
const mealsProvided = computed(() => {
  const amt = donationStore.currentDonation?.amount || 100;
  return Math.round(amt * 0.4) || 20;
});

// Interactive state
const isDownloaded = ref(false);
const showConfetti = ref(true);

const handleDownload = () => {
  isDownloaded.value = true;
  setTimeout(() => {
    isDownloaded.value = false;
  }, 2000);
};

const handleViewDetails = () => {
  router.push('/receipt');
};

// Simple Vue-based Confetti Pieces
interface ConfettiPiece {
  id: number;
  left: string;
  duration: string;
  delay: string;
  color: string;
}

const confettiPieces = ref<ConfettiPiece[]>([]);
const colors = ['#00685F', '#00201D', '#E6F7F5', '#B84A39'];

onMounted(() => {
  const pieces: ConfettiPiece[] = [];
  for (let i = 0; i < 60; i++) {
    pieces.push({
      id: i,
      left: Math.random() * 100 + 'vw',
      duration: (Math.random() * 3 + 2) + 's',
      delay: Math.random() * 2 + 's',
      color: colors[Math.floor(Math.random() * colors.length)]
    });
  }
  confettiPieces.value = pieces;
});
</script>

<template>
  <div class="bg-background text-on-background font-sans antialiased min-h-screen flex flex-col items-center justify-center relative overflow-hidden">
    <!-- Confetti Container -->
    <div v-if="showConfetti" class="absolute inset-0 pointer-events-none z-0 overflow-hidden">
      <div
        v-for="piece in confettiPieces"
        :key="piece.id"
        class="confetti-piece"
        :style="{
          left: piece.left,
          animationDuration: piece.duration,
          animationDelay: piece.delay,
          backgroundColor: piece.color
         }"
      ></div>
    </div>

    <!-- Main Content Card -->
    <main class="w-full max-w-container-max mx-auto px-6 py-12 relative z-10 flex flex-col items-center justify-center text-center">
      <!-- Minimal Brand Logo Header -->
      <div @click="router.push('/')" class="mb-8 flex items-center gap-2 cursor-pointer hover:opacity-95 select-none justify-center">
        <img
          alt="HeartBridge Logo"
          class="h-9 w-9 object-contain"
          src="https://lh3.googleusercontent.com/aida-public/AB6AXuBuwCe8q0lYxUQUnfWb95tcuhSYimeb8ulBvDxxYMoUmjKlab1Op0cW3tR2plTyzhb-o8OaeXuGUIULxRKBPbH2jvjLIuEog0HpG9NwNvkhfcgfAx3XYgN9iDY3lRtCq87a5PvjYDWXE27bP3cF5DiRvq1waLd4ljmkJ7ldSv40rGOMJrwiRKzjLCTzulE9J4KzoFEyZNLxm0l6s-417RsIftRmkJGkxE4ZiBgn08dinbOaaZAwC3vvWqHOHlwilocU4WtgeQqMTek"
        />
        <span class="text-xl md:text-2xl font-sans tracking-tight font-bold text-[#00685F]">HeartBridge</span>
      </div>

      <!-- Receipt Visual Card -->
      <div class="bg-surface border border-outline-variant/60 rounded-2xl shadow-sm p-8 md:p-12 w-full max-w-2xl mx-auto flex flex-col items-center relative overflow-hidden">
        <!-- Brand accent color bar -->
        <div class="absolute top-0 left-0 w-full h-1.5 bg-[#00685F]"></div>

        <!-- Success indicator box (rounded-full matching brand) -->
        <div class="success-circle w-20 h-20 rounded-full border-2 border-[#00685F] text-[#00685F] flex items-center justify-center mb-8 bg-[#E6F7F5]">
          <span class="material-symbols-outlined" style="font-size: 40px; font-variation-settings: 'FILL' 1;">check_circle</span>
        </div>

        <h1 class="font-sans text-3xl md:text-4xl text-on-background mb-2 font-bold tracking-tight">
          Thank You, {{ donorName }}!
        </h1>
        <p class="text-sm md:text-base text-on-surface-variant font-sans mb-8">Your gift is changing lives today.</p>

        <!-- Dynamic Impact box -->
        <div class="bg-[#E6F7F5] border border-[#00685F]/10 rounded-xl p-6 mb-8 w-full max-w-md">
          <div class="flex items-center justify-center gap-2 mb-2 text-[#00685F] font-bold text-xs uppercase tracking-wider">
            <span class="material-symbols-outlined text-[16px]" style="font-variation-settings: 'FILL' 1;">restaurant</span>
            <span>Your Impact</span>
          </div>
          <p class="text-base text-[#00201D] font-sans font-semibold">
            You've just provided <strong class="text-[#00685F] font-bold font-sans">{{ mealsProvided }} meals</strong> for children in need.
          </p>
        </div>

        <!-- Receipt summary box -->
        <div class="w-full max-w-md mb-8">
          <h3 class="text-xs font-bold text-on-surface-variant mb-3 text-left">Receipt Preview</h3>
          <div class="bg-[#F5F7F6] border border-outline-variant/40 rounded-xl p-6 text-left">
            <div class="flex justify-between items-center mb-3">
              <span class="text-xs text-on-surface-variant font-medium">Donation Date</span>
              <span class="text-xs text-on-surface font-bold">{{ donationDate }}</span>
            </div>

            <div class="flex justify-between items-center mb-3">
              <span class="text-xs text-on-surface-variant font-medium">Amount</span>
              <span class="text-xl font-sans font-bold text-[#00685F]">{{ displayAmount }}</span>
            </div>

            <div class="flex justify-between items-center border-t border-outline-variant/30 mt-4 pt-4">
              <span class="text-xs text-on-surface-variant font-medium">Payment Method</span>
              <span class="text-xs text-on-surface font-bold">{{ paymentMethod }}</span>
            </div>
          </div>
        </div>

        <!-- Buttons -->
        <div class="flex flex-col sm:flex-row gap-4 w-full max-w-md mb-8">
          <button
            class="flex-1 bg-[#00201D] text-white hover:bg-black rounded-full px-6 py-3.5 font-semibold text-sm cursor-pointer shadow-sm flex items-center justify-center gap-2"
            @click="handleDownload"
          >
            <span class="material-symbols-outlined text-[18px]">download</span>
            {{ isDownloaded ? 'Downloading...' : 'Download Receipt' }}
          </button>

          <button
            class="flex-1 border border-outline-variant/80 hover:bg-[#F5F7F6] text-[#00685F] font-semibold text-sm rounded-full px-6 py-3.5 cursor-pointer flex items-center justify-center gap-2"
            @click="handleViewDetails"
          >
            <span class="material-symbols-outlined text-[18px]">receipt_long</span>
            View Details
          </button>
        </div>

        <!-- Share Section -->
        <div class="border-t border-outline-variant/40 w-full pt-6 flex flex-col items-center">
          <p class="text-xs font-bold text-on-surface-variant mb-4">Share your impact</p>
          <div class="flex gap-4">
            <button
              aria-label="Share on Facebook"
              class="w-11 h-11 border border-outline-variant/60 rounded-full flex items-center justify-center text-on-surface-variant hover:text-[#00685F] hover:bg-[#E6F7F5] transition-colors cursor-pointer focus-visible:outline-none"
            >
              <span class="material-symbols-outlined text-[18px]">share</span>
            </button>
            <button
              aria-label="Share on Twitter"
              class="w-11 h-11 border border-outline-variant/60 rounded-full flex items-center justify-center text-on-surface-variant hover:text-[#00685F] hover:bg-[#E6F7F5] transition-colors cursor-pointer focus-visible:outline-none"
            >
              <span class="material-symbols-outlined text-[18px]">share</span>
            </button>
            <button
              aria-label="Copy Link"
              class="w-11 h-11 border border-outline-variant/60 rounded-full flex items-center justify-center text-on-surface-variant hover:text-[#00685F] hover:bg-[#E6F7F5] transition-colors cursor-pointer focus-visible:outline-none"
            >
              <span class="material-symbols-outlined text-[18px]">link</span>
            </button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.confetti-piece {
  position: absolute;
  width: 10px;
  height: 20px;
  top: 0;
  opacity: 0;
  animation: fall linear infinite;
  border-radius: 2px;
}

@keyframes fall {
  0% {
    opacity: 1;
    top: -10%;
    transform: rotateZ(0deg) rotateX(0deg);
  }
  100% {
    opacity: 0;
    top: 100%;
    transform: rotateZ(360deg) rotateX(360deg);
  }
}

.success-circle {
  animation: scaleIn 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
}

@keyframes scaleIn {
  0% {
    transform: scale(0);
    opacity: 0;
  }
  50% {
    transform: scale(1.15);
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
}
</style>

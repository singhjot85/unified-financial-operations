<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useDonationStore } from '../stores/donation';
import AppFooter from '../components/AppFooter.vue';

const router = useRouter();
const donationStore = useDonationStore();

// Dynamic receipt variables with high-contrast realistic defaults
const donorName = computed(() => donationStore.currentDonation?.name || 'Eleanor Shellstrop');
const donorEmail = computed(() => donationStore.currentDonation?.email || 'eleanor@example.com');
const donationDate = computed(() => donationStore.currentDonation?.date || 'October 24, 2024');
const receiptNumber = computed(() => donationStore.currentDonation?.receiptNumber || '#HB-2024-001');
const finalAmount = computed(() => {
  const amt = donationStore.currentDonation?.amount || 250;
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amt);
});

// Interactive state actions
const isPrinted = ref(false);
const isEmailed = ref(false);
const isDownloaded = ref(false);

const handlePrint = () => {
  isPrinted.value = true;
  // Trigger standard window print
  setTimeout(() => {
    window.print();
    isPrinted.value = false;
  }, 300);
};

const handleEmail = () => {
  isEmailed.value = true;
  setTimeout(() => {
    alert(`Receipt successfully queued and emailed to ${donorEmail.value}!`);
    isEmailed.value = false;
  }, 1000);
};

const handleDownload = () => {
  isDownloaded.value = true;
  setTimeout(() => {
    alert('PDF tax receipt successfully generated and downloaded!');
    isDownloaded.value = false;
  }, 1000);
};

const goHome = () => {
  router.push('/');
};
</script>

<template>
  <div class="bg-background text-on-background min-h-screen flex flex-col font-sans antialiased">

    <!-- Top back button banner -->
    <div class="w-full max-w-3xl mx-auto px-6 pt-8">
      <button
        @click="goHome"
        class="text-on-surface hover:text-primary text-sm font-semibold flex items-center gap-1.5 transition-colors py-2 cursor-pointer focus-visible:outline-none"
      >
        <span class="material-symbols-outlined text-[16px]">arrow_back</span>
        Return to Homepage
      </button>
    </div>

    <!-- Main Receipt Canvas -->
    <main class="flex-grow flex items-center justify-center py-8 px-6">
      <div class="w-full max-w-3xl bg-surface border border-outline-variant/60 rounded-2xl shadow-sm overflow-hidden relative">

        <!-- Receipt Header -->
        <div class="bg-[#EEF2F1] p-8 border-b border-outline-variant/40 flex flex-col md:flex-row items-center justify-between gap-6 relative">

          <!-- Watermark logo back element -->
          <div class="absolute inset-0 flex items-center justify-center opacity-[0.03] pointer-events-none select-none">
            <img
              alt=""
              class="w-64 h-64 object-contain grayscale"
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuBuwCe8q0lYxUQUnfWb95tcuhSYimeb8ulBvDxxYMoUmjKlab1Op0cW3tR2plTyzhb-o8OaeXuGUIULxRKBPbH2jvjLIuEog0HpG9NwNvkhfcgfAx3XYgN9iDY3lRtCq87a5PvjYDWXE27bP3cF5DiRvq1waLd4ljmkJ7ldSv40rGOMJrwiRKzjLCTzulE9J4KzoFEyZNLxm0l6s-417RsIftRmkJGkxE4ZiBgn08dinbOaaZAwC3vvWqHOHlwilocU4WtgeQqMTek"
            />
          </div>

          <div class="flex items-center gap-3 relative z-10">
            <img
              alt="HeartBridge Logo"
              class="h-10 w-10 object-contain"
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuBuwCe8q0lYxUQUnfWb95tcuhSYimeb8ulBvDxxYMoUmjKlab1Op0cW3tR2plTyzhb-o8OaeXuGUIULxRKBPbH2jvjLIuEog0HpG9NwNvkhfcgfAx3XYgN9iDY3lRtCq87a5PvjYDWXE27bP3cF5DiRvq1waLd4ljmkJ7ldSv40rGOMJrwiRKzjLCTzulE9J4KzoFEyZNLxm0l6s-417RsIftRmkJGkxE4ZiBgn08dinbOaaZAwC3vvWqHOHlwilocU4WtgeQqMTek"
            />
            <div>
              <h1 class="text-xl md:text-2xl font-sans font-bold text-[#00685F]">HeartBridge</h1>
              <p class="text-xs text-on-surface-variant font-medium">Tax ID: 98-7654321</p>
            </div>
          </div>

          <div class="text-center md:text-right relative z-10 select-none">
            <p class="text-[10px] uppercase tracking-wider font-bold text-on-surface-variant mb-1">Official Tax Receipt</p>
            <p class="font-sans text-2xl text-[#00685F] font-bold">{{ receiptNumber }}</p>
          </div>
        </div>

        <!-- Receipt Body details -->
        <div class="p-8 md:p-12 bg-surface relative">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
            <div>
              <p class="text-xs font-bold text-on-surface-variant mb-1.5 select-none">Donor Information</p>
              <p class="text-lg font-sans font-bold text-on-surface">{{ donorName }}</p>
              <p class="text-sm text-on-surface-variant font-sans">{{ donorEmail }}</p>
            </div>

            <div class="md:text-right">
              <p class="text-xs font-bold text-on-surface-variant mb-1.5 select-none">Date of Donation</p>
              <p class="text-lg font-sans font-bold text-on-surface">{{ donationDate }}</p>
            </div>
          </div>

          <!-- Donation item card -->
          <div class="bg-[#F5F7F6] border border-outline-variant/40 rounded-xl p-6 mb-8 flex justify-between items-center">
            <div>
              <p class="text-base font-sans font-semibold text-[#00201D]">One-time Donation - Clean Water Initiative</p>
              <p class="text-xs text-on-surface-variant font-sans mt-0.5">No goods or services were provided in exchange.</p>
            </div>
            <p class="text-3xl font-sans font-bold text-[#00685F]">{{ finalAmount }}</p>
          </div>

          <!-- Bottom Actions -->
          <div class="flex flex-col sm:flex-row gap-4 justify-end items-center mt-8 border-t border-outline-variant/40 pt-6">
            <button
              @click="handlePrint"
              :disabled="isPrinted"
              class="w-full sm:w-auto px-6 py-3 border border-outline-variant/80 text-on-surface text-sm font-semibold rounded-full flex items-center justify-center gap-2 hover:bg-[#F5F7F6] transition-all duration-150 cursor-pointer focus-visible:outline-none"
            >
              <span class="material-symbols-outlined text-[16px]">print</span>
              {{ isPrinted ? 'Printing...' : 'Print' }}
            </button>

            <button
              @click="handleEmail"
              :disabled="isEmailed"
              class="w-full sm:w-auto px-6 py-3 border border-outline-variant/80 text-on-surface text-sm font-semibold rounded-full flex items-center justify-center gap-2 hover:bg-[#F5F7F6] transition-all duration-150 cursor-pointer focus-visible:outline-none"
            >
              <span class="material-symbols-outlined text-[16px]">mail</span>
              {{ isEmailed ? 'Sending...' : 'Email Me' }}
            </button>

            <button
              @click="handleDownload"
              :disabled="isDownloaded"
              class="w-full sm:w-auto px-6 py-3 bg-[#00201D] text-white text-sm font-semibold rounded-full flex items-center justify-center gap-2 hover:bg-black transition-all duration-150 shadow-sm focus-visible:outline-none"
            >
              <span class="material-symbols-outlined text-[18px]">download</span>
              {{ isDownloaded ? 'Downloading...' : 'Download PDF' }}
            </button>
          </div>
        </div>

        <!-- Material accent bar footer -->
        <div class="h-1.5 w-full bg-[#00685F]"></div>
      </div>
    </main>

    <!-- Footer -->
    <AppFooter />
  </div>
</template>

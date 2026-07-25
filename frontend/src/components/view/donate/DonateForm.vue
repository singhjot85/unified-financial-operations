<script setup lang="ts">
import { ref, watch, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useDonationStore } from '../../../stores/donation';
import { type Frequency } from '../../../conf/types/common';
import AppButton from '../../AppButton.vue';


const route = useRoute();
const router = useRouter();
const donationStore = useDonationStore();

// Form states
const selectedFrequency = ref<Frequency>('one-time');
const selectedAmount = ref<string>('50'); // Default to 50
const customAmountValue = ref<number | null>(null);

const email = ref('');
const cardName = ref('');
const cardNumber = ref(''); // For display simulation
const isSubmitting = ref(false);

// Default dynamic impact texts
const impactData: Record<string, string> = {
  '25': 'Provides emergency nutrition packs for <strong>one child</strong> for a month.',
  '50': 'Provides clean water filters for <strong>two families</strong> for an entire year, ensuring health and sanitation.',
  '100': 'Funds comprehensive medical checkups and vaccinations for <strong>a small village</strong>.'
};

// Calculate current impact description
const currentImpactText = ref(impactData['50']);
const displayAmount = ref('$50');

const updateImpact = () => {
  if (selectedAmount.value === 'custom') {
    const amt = customAmountValue.value || 0;
    displayAmount.value = `$${amt}`;
    currentImpactText.value = amt > 0
      ? `Every contribution helps us bridge the gap. Your <strong>$${amt}</strong> gift delivers essential aid where it is needed most.`
      : 'Every contribution helps us bridge the gap and deliver essential aid where it is needed most.';
  } else {
    displayAmount.value = `$${selectedAmount.value}`;
    currentImpactText.value = impactData[selectedAmount.value] || 'Thank you for your generous support.';
  }
};

// Listen to amount changes
watch([selectedAmount, customAmountValue], () => {
  updateImpact();
});

// Check query params for pre-filled data on mount
onMounted(() => {
  const queryAmount = route.query.amount;
  if (queryAmount) {
    if (queryAmount === 'custom') {
      selectedAmount.value = 'custom';
    } else if (['25', '50', '100'].includes(queryAmount as string)) {
      selectedAmount.value = queryAmount as string;
    } else {
      selectedAmount.value = 'custom';
      customAmountValue.value = parseFloat(queryAmount as string) || null;
    }
  }
  updateImpact();
});

// Handle form submit
const handleSubmit = async (e: Event) => {
  e.preventDefault();

  const finalAmount = selectedAmount.value === 'custom'
    ? (customAmountValue.value || 0)
    : parseFloat(selectedAmount.value);

  if (finalAmount <= 0) {
    alert('Please select or enter a valid donation amount.');
    return;
  }

  isSubmitting.value = true;

  try {
    // Dispatch Pinia store action to submit
    await donationStore.makeDonation({
      amount: finalAmount,
      frequency: selectedFrequency.value,
      email: email.value || 'donor@heartbridge.ngo',
      name: cardName.value || 'Generous Donor',
      campaignId: 'community-center-fund',
      paymentMethod: 'Visa ending in 4242'
    });

    // Navigate to Thank You view
    router.push('/thank-you');
  } catch (err) {
    console.error('Error completing gift:', err);
  } finally {
    isSubmitting.value = false;
  }
};
</script>

<template>
  <div class="flex-grow w-full max-w-container-max mx-auto px-6 md:px-12 py-12 flex flex-col lg:flex-row gap-12 items-start justify-center">
    <!-- Form Section -->
    <div class="w-full lg:w-3/5 bg-surface border border-outline-variant/60 rounded-2xl shadow-sm p-8 md:p-10 relative overflow-hidden">
      <!-- Subtle Tonal Layer Background -->
      <div class="absolute inset-0 bg-surface-container-lowest opacity-40 z-0"></div>

      <form class="relative z-10 flex flex-col gap-8" @submit="handleSubmit">
        <!-- Step 1: Amount selection -->
        <section class="flex flex-col gap-6">
          <header>
            <h2 class="text-2xl md:text-3xl font-sans font-bold text-on-surface">Choose Amount</h2>
            <p class="text-sm text-on-surface-variant mt-2 font-sans">Select a predefined amount or enter your own custom value.</p>
          </header>

          <!-- Frequency toggle buttons (Pill styled) -->
          <div class="flex p-1 bg-[#EEF2F1] border border-outline-variant/40 rounded-full w-fit mb-2">
            <button
              type="button"
              :aria-pressed="selectedFrequency === 'one-time'"
              @click="selectedFrequency = 'one-time'"
              class="px-6 py-2.5 text-xs font-bold transition-all duration-150 rounded-full focus-visible:outline-none cursor-pointer"
              :class="[
                selectedFrequency === 'one-time'
                  ? 'bg-[#00201D] text-white font-bold shadow-sm'
                  : 'text-on-surface-variant hover:text-on-surface'
              ]"
            >
              One-time
            </button>
            <button
              type="button"
              :aria-pressed="selectedFrequency === 'monthly'"
              @click="selectedFrequency = 'monthly'"
              class="px-6 py-2.5 text-xs font-bold transition-all duration-150 rounded-full focus-visible:outline-none flex items-center gap-2 cursor-pointer"
              :class="[
                selectedFrequency === 'monthly'
                  ? 'bg-[#00685F] text-on-primary font-bold shadow-sm'
                  : 'text-on-surface-variant hover:text-on-surface'
              ]"
            >
              <span class="material-symbols-outlined text-[14px]" style="font-variation-settings: 'FILL' 1;">favorite</span>
              Monthly
            </button>
          </div>

          <!-- Amount grid options -->
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <!-- Option 1: $25 -->
            <div class="relative">
              <input
                class="sr-only"
                id="amt-25"
                name="amount"
                type="radio"
                value="25"
                v-model="selectedAmount"
              />
              <label
                for="amt-25"
                class="flex items-center justify-center py-6 border rounded-xl cursor-pointer transition-all duration-200 text-center font-sans text-2xl font-bold text-on-surface select-none bg-surface"
                :class="[
                  selectedAmount === '25'
                    ? 'border-[#00685F] bg-[#E6F7F5] ring-2 ring-[#00685F] text-[#00685F]'
                    : 'border-outline-variant hover:bg-surface-container-low'
                ]"
              >
                $25
              </label>
            </div>

            <!-- Option 2: $50 (Recommended) -->
            <div class="relative">
              <input
                class="sr-only"
                id="amt-50"
                name="amount"
                type="radio"
                value="50"
                v-model="selectedAmount"
              />
              <label
                for="amt-50"
                class="flex flex-col items-center justify-center py-5 border rounded-xl cursor-pointer transition-all duration-200 text-center select-none relative bg-surface"
                :class="[
                  selectedAmount === '50'
                    ? 'border-[#00685F] bg-[#E6F7F5] ring-2 ring-[#00685F] text-[#00685F] font-bold'
                    : 'border-outline-variant hover:bg-surface-container-low'
                ]"
              >
                <span class="absolute -top-3 bg-[#00685F] text-white text-[9px] font-bold px-2.5 py-0.5 rounded-full tracking-wider shadow-sm">
                  Recommended
                </span>
                <span class="font-sans text-2xl font-bold text-on-surface mt-1">$50</span>
              </label>
            </div>

            <!-- Option 3: $100 -->
            <div class="relative">
              <input
                class="sr-only"
                id="amt-100"
                name="amount"
                type="radio"
                value="100"
                v-model="selectedAmount"
              />
              <label
                for="amt-100"
                class="flex items-center justify-center py-6 border rounded-xl cursor-pointer transition-all duration-200 text-center font-sans text-2xl font-bold text-on-surface select-none bg-surface"
                :class="[
                  selectedAmount === '100'
                    ? 'border-[#00685F] bg-[#E6F7F5] ring-2 ring-[#00685F] text-[#00685F]'
                    : 'border-outline-variant hover:bg-surface-container-low'
                ]"
              >
                $100
              </label>
            </div>

            <!-- Custom Option -->
            <div class="relative">
              <input
                class="sr-only"
                id="amt-custom"
                name="amount"
                type="radio"
                value="custom"
                v-model="selectedAmount"
              />
              <label
                for="amt-custom"
                class="flex flex-col items-center justify-center py-6 border rounded-xl cursor-pointer transition-all duration-200 text-center select-none bg-surface"
                :class="[
                  selectedAmount === 'custom'
                    ? 'border-[#00685F] bg-[#E6F7F5] ring-2 ring-[#00685F] text-[#00685F] font-bold'
                    : 'border-outline-variant hover:bg-surface-container-low'
                ]"
              >
                <span class="text-sm font-sans font-bold text-on-surface-variant">Custom</span>
              </label>
            </div>
          </div>

          <!-- Hidden custom input field -->
          <div v-if="selectedAmount === 'custom'" class="mt-1 transition-all duration-200">
            <label class="sr-only" for="custom-amount">Custom Amount</label>
            <div class="relative">
              <span class="absolute left-4 top-1/2 -translate-y-1/2 font-sans text-2xl font-bold text-on-surface-variant">$</span>
              <input
                id="custom-amount"
                class="w-full pl-10 pr-4 py-4 border border-outline-variant rounded-xl bg-surface focus:border-[#00685F] font-sans text-2xl font-bold text-on-surface transition-all outline-none"
                placeholder="0.00"
                type="number"
                min="1"
                v-model="customAmountValue"
                required
              />
            </div>
          </div>
        </section>

        <hr class="border-outline-variant/40 border-t" />

        <!-- Step 2: Payment -->
        <section class="flex flex-col gap-6">
          <header class="flex justify-between items-end">
            <div>
              <h2 class="text-2xl font-sans font-bold text-on-surface">Payment</h2>
            </div>
            <div class="flex gap-2 opacity-60">
              <span class="material-symbols-outlined text-on-surface" title="Secure Payment">lock</span>
            </div>
          </header>

          <!-- Express Checkout -->
          <div class="flex flex-col sm:flex-row gap-4 mb-1">
            <button
              type="button"
              class="flex-1 py-4 border border-outline-variant rounded-full bg-[#1D1D1F] text-white flex items-center justify-center gap-2 hover:opacity-95 transition-opacity focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[#00685F] cursor-pointer text-sm font-bold shadow-sm"
            >
              <span>Pay with Apple Pay</span>
            </button>
          </div>

          <!-- Or Pay with Card Divider -->
          <div class="flex items-center gap-4 mb-1">
            <div class="h-px bg-outline-variant/40 flex-1"></div>
            <span class="text-xs font-semibold text-on-surface-variant">Or pay with card</span>
            <div class="h-px bg-outline-variant/40 flex-1"></div>
          </div>

          <!-- Fields -->
          <div class="flex flex-col gap-4">
            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-semibold text-on-surface-variant" for="email">Email Address</label>
              <input
                id="email"
                v-model="email"
                class="w-full px-4 py-3.5 border border-outline-variant rounded-xl bg-surface focus:border-[#00685F] font-sans text-sm text-on-surface transition-all outline-none"
                placeholder="you@example.com"
                required
                type="email"
              />
            </div>

            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-semibold text-on-surface-variant" for="card-element">Card Details</label>
              <div
                id="card-element"
                class="w-full px-4 py-3.5 border border-outline-variant rounded-xl bg-surface flex items-center justify-between text-on-surface-variant focus-within:border-[#00685F] transition-all cursor-text"
              >
                <input
                  v-model="cardNumber"
                  class="bg-transparent border-none w-full font-sans text-sm text-on-surface transition-all outline-none"
                  placeholder="Card number, expiration, CVC"
                  required
                />
                <span class="material-symbols-outlined text-[18px] opacity-60">credit_card</span>
              </div>
            </div>

            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-semibold text-on-surface-variant" for="name">Name on Card</label>
              <input
                id="name"
                v-model="cardName"
                class="w-full px-4 py-3.5 border border-outline-variant rounded-xl bg-surface focus:border-[#00685F] font-sans text-sm text-on-surface transition-all outline-none"
                placeholder="Eleanor Shellstrop"
                required
                type="text"
              />
            </div>
          </div>
        </section>

        <!-- submit action -->
        <div class="mt-4 flex flex-col gap-4">
          <button
            type="submit"
            class="w-full py-4 text-sm font-bold bg-[#00685F] text-white rounded-full hover:bg-[#00524a] active:scale-[0.99] transition-all shadow-md flex items-center justify-center gap-2 cursor-pointer"
            :disabled="isSubmitting"
          >
            <span v-if="isSubmitting" class="animate-spin h-5 w-5 border-2 border-white border-t-transparent rounded-full mr-2"></span>
            <span v-else>Complete My Gift</span>
            <span class="material-symbols-outlined text-[18px]">favorite</span>
          </button>

          <p class="text-center text-xs text-on-surface-variant flex items-center justify-center gap-2 font-medium">
            <span class="material-symbols-outlined text-[15px] text-[#00685F]">verified_user</span>
            Your donation is secure and tax-deductible.
          </p>
        </div>
      </form>
    </div>

    <!-- Sidebar / Impact Summary -->
    <aside class="w-full lg:w-2/5 flex flex-col gap-6 lg:sticky lg:top-24">
      <!-- Dynamic Impact Card -->
      <div class="bg-surface border border-outline-variant/60 rounded-2xl shadow-sm p-8 flex flex-col gap-6 relative overflow-hidden">
        <div class="absolute top-0 right-0 p-4 opacity-[0.03] pointer-events-none">
          <span class="material-symbols-outlined text-[120px] text-[#00685F]" style="font-variation-settings: 'FILL' 1;">water_drop</span>
        </div>

        <div class="relative z-10">
          <h3 class="text-xs uppercase tracking-wider font-bold text-[#00685F] mb-1">Your Impact</h3>
          <div class="text-5xl font-sans font-bold text-on-background flex items-baseline gap-1">
            <span>{{ displayAmount }}</span>
          </div>

          <div class="mt-6 bg-[#F5F7F6] rounded-xl border border-outline-variant/30 p-6 font-sans text-sm leading-relaxed text-on-surface">
            <p v-html="currentImpactText"></p>
          </div>
        </div>
      </div>

      <!-- Trust Card -->
      <div class="bg-surface p-6 border border-outline-variant/60 rounded-2xl shadow-sm flex items-start gap-4">
        <div class="bg-[#E6F7F5] text-[#00685F] p-3 rounded-xl shrink-0 flex items-center justify-center">
          <span class="material-symbols-outlined text-[20px]" style="font-variation-settings: 'FILL' 1;">receipt_long</span>
        </div>
        <div>
          <h4 class="text-sm font-bold text-on-surface mb-1">Tax Receipt Included</h4>
          <p class="text-xs leading-relaxed text-on-surface-variant font-sans">
            An official tax receipt will be emailed immediately after your donation is processed.
          </p>
        </div>
      </div>
    </aside>
  </div>
</template>

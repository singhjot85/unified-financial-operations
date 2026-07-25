<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import AppBar from '../components/AppBar.vue';
import AppFooter from '../components/AppFooter.vue';
import AppButton from '../components/AppButton.vue';

const router = useRouter();

const digits = ref<string[]>(['', '', '', '', '', '']);
const digitInputs = ref<HTMLInputElement[]>([]);
const useBackupCode = ref(false);
const backupCode = ref('');
const isLoading = ref(false);
const errorMessage = ref('');

const resendTimer = ref(45);
let timerInterval: any = null;

onMounted(() => {
  startTimer();
});

onUnmounted(() => {
  if (timerInterval) clearInterval(timerInterval);
});

const startTimer = () => {
  resendTimer.value = 45;
  if (timerInterval) clearInterval(timerInterval);
  timerInterval = setInterval(() => {
    if (resendTimer.value > 0) {
      resendTimer.value--;
    } else {
      clearInterval(timerInterval);
    }
  }, 1000);
};

const handleInput = (index: number, event: Event) => {
  const input = event.target as HTMLInputElement;
  const val = input.value;

  if (val.length > 0) {
    digits.value[index] = val[val.length - 1];
    if (index < 5 && digitInputs.value[index + 1]) {
      digitInputs.value[index + 1].focus();
    }
  }
};

const handleKeyDown = (index: number, event: KeyboardEvent) => {
  if (event.key === 'Backspace' && !digits.value[index] && index > 0) {
    digitInputs.value[index - 1].focus();
  }
};

const handlePaste = (event: ClipboardEvent) => {
  event.preventDefault();
  const pastedData = event.clipboardData?.getData('text').trim() || '';
  if (/^\d{6}$/.test(pastedData)) {
    for (let i = 0; i < 6; i++) {
      digits.value[i] = pastedData[i];
    }
    if (digitInputs.value[5]) {
      digitInputs.value[5].focus();
    }
  }
};

const handleResend = () => {
  if (resendTimer.value > 0) return;
  startTimer();
  digits.value = ['', '', '', '', '', ''];
  if (digitInputs.value[0]) digitInputs.value[0].focus();
};

const handleVerify = () => {
  errorMessage.value = '';

  if (useBackupCode.value) {
    if (!backupCode.value) {
      errorMessage.value = 'Please enter a valid backup security code.';
      return;
    }
  } else {
    const code = digits.value.join('');
    if (code.length < 6) {
      errorMessage.value = 'Please enter all 6 digits of your authentication code.';
      return;
    }
  }

  isLoading.value = true;
  setTimeout(() => {
    isLoading.value = false;
    // Successful verification routes to campaign home
    router.push('/');
  }, 600);
};
</script>

<template>
  <div class="min-h-screen bg-background flex flex-col font-sans text-on-surface">
    <!-- Minimal Header -->
    <AppBar minimal />

    <!-- Main Content Container -->
    <main class="flex-1 flex items-center justify-center px-4 sm:px-6 py-12 md:py-16">
      <div class="w-full max-w-md">
        <!-- Card Container -->
        <div class="bg-surface rounded-2xl border border-outline-variant/60 shadow-lg p-6 sm:p-10 transition-all duration-300">

          <!-- Header & Logo -->
          <div class="text-center mb-8">
            <div class="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-primary-container/80 text-primary mb-4 shadow-sm">
              <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <h1 class="text-2xl sm:text-3xl font-bold tracking-tight text-on-surface">Two-Factor Authentication</h1>
            <p class="text-sm text-on-surface-variant mt-2">
              Enter the 6-digit passcode from your authenticator app or email
            </p>
          </div>

          <!-- Error Alert -->
          <div v-if="errorMessage" class="mb-6 p-4 rounded-xl bg-error-container text-on-error-container text-xs font-medium flex items-center gap-3 border border-error/20">
            <svg class="w-5 h-5 text-error shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{{ errorMessage }}</span>
          </div>

          <!-- Form -->
          <form @submit.prevent="handleVerify" class="space-y-6">
            <!-- 6-Digit Passcode Mode -->
            <div v-if="!useBackupCode" class="space-y-4">
              <label class="block text-xs font-semibold uppercase tracking-wider text-on-surface-variant text-center">
                Security Verification Code
              </label>

              <!-- 6 Digit Inputs -->
              <div class="flex justify-between items-center gap-2" @paste="handlePaste">
                <input
                  v-for="(digit, idx) in digits"
                  :key="idx"
                  ref="digitInputs"
                  v-model="digits[idx]"
                  type="text"
                  inputmode="numeric"
                  maxlength="1"
                  class="w-11 h-13 sm:w-12 sm:h-14 text-center text-xl font-bold bg-surface-container-low border border-outline-variant rounded-xl text-on-surface focus:bg-surface focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition-all duration-200"
                  @input="handleInput(idx, $event)"
                  @keydown="handleKeyDown(idx, $event)"
                />
              </div>

              <!-- Resend Timer -->
              <div class="flex items-center justify-between text-xs pt-1">
                <span class="text-on-surface-variant">Didn't receive a code?</span>
                <button
                  type="button"
                  @click="handleResend"
                  :disabled="resendTimer > 0"
                  class="font-semibold transition-colors cursor-pointer"
                  :class="resendTimer > 0 ? 'text-on-surface-variant/50 cursor-not-allowed' : 'text-primary hover:underline'"
                >
                  <span v-if="resendTimer > 0">Resend in {{ resendTimer }}s</span>
                  <span v-else>Resend Code</span>
                </button>
              </div>
            </div>

            <!-- Backup Code Mode -->
            <div v-else class="space-y-2">
              <label for="backup-code" class="block text-xs font-semibold uppercase tracking-wider text-on-surface-variant">
                Emergency Backup Code
              </label>
              <input
                id="backup-code"
                v-model="backupCode"
                type="text"
                placeholder="XXXX-XXXX-XXXX"
                class="w-full px-4 py-3 bg-surface-container-low border border-outline-variant rounded-xl text-sm font-mono text-on-surface placeholder:text-on-surface-variant/50 focus:bg-surface focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition-all duration-200"
              />
              <p class="text-[11px] text-on-surface-variant">Enter one of your 8-digit emergency recovery codes.</p>
            </div>

            <!-- Submit Button -->
            <AppButton
              id="mfa-verify-btn"
              type="submit"
              variant="primary"
              :disabled="isLoading"
              class="w-full rounded-xl py-3.5 text-sm font-semibold tracking-normal uppercase-none transition-all duration-200 shadow-md hover:shadow-lg"
            >
              <span v-if="!isLoading">Verify & Continue</span>
              <span v-else class="flex items-center gap-2">
                <svg class="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Verifying Code...
              </span>
            </AppButton>
          </form>

          <!-- Toggle Backup Code Mode & Back to Login -->
          <div class="mt-8 pt-6 border-t border-outline-variant/60 flex flex-col items-center gap-3 text-xs">
            <button
              type="button"
              @click="useBackupCode = !useBackupCode; errorMessage = ''"
              class="font-medium text-primary hover:underline transition-colors cursor-pointer"
            >
              <span v-if="!useBackupCode">Lost your device? Use an emergency backup code</span>
              <span v-else">Back to 6-digit authenticator code</span>
            </button>

            <router-link to="/login" class="text-on-surface-variant hover:text-on-surface flex items-center gap-1 font-medium transition-colors">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              Return to Sign In
            </router-link>
          </div>

        </div>
      </div>
    </main>

    <!-- Footer -->
    <AppFooter />
  </div>
</template>

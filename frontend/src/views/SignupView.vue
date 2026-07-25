<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import AppBar from '../components/AppBar.vue';
import AppFooter from '../components/AppFooter.vue';
import AppButton from '../components/AppButton.vue';

const router = useRouter();

const firstName = ref('');
const lastName = ref('');
const email = ref('');
const organization = ref('');
const password = ref('');
const confirmPassword = ref('');
const agreeTerms = ref(false);
const showPassword = ref(false);
const isLoading = ref(false);
const errorMessage = ref('');

const togglePasswordVisibility = () => {
  showPassword.value = !showPassword.value;
};

const handleSignup = () => {
  errorMessage.value = '';

  if (!firstName.value || !lastName.value || !email.value || !password.value) {
    errorMessage.value = 'Please fill out all required fields.';
    return;
  }

  if (password.value !== confirmPassword.value) {
    errorMessage.value = 'Passwords do not match.';
    return;
  }

  if (!agreeTerms.value) {
    errorMessage.value = 'You must agree to the Terms of Service and Privacy Policy.';
    return;
  }

  isLoading.value = true;
  // Simulate registration and route to MFA verification
  setTimeout(() => {
    isLoading.value = false;
    router.push('/mfa');
  }, 600);
};
</script>

<template>
  <div class="min-h-screen bg-background flex flex-col font-sans text-on-surface">
    <!-- Minimal Header -->
    <AppBar minimal />

    <!-- Main Content Container -->
    <main class="flex-1 flex items-center justify-center px-4 sm:px-6 py-12 md:py-16">
      <div class="w-full max-w-lg">
        <!-- Card Container -->
        <div class="bg-surface rounded-2xl border border-outline-variant/60 shadow-lg p-6 sm:p-10 transition-all duration-300">

          <!-- Header & Logo -->
          <div class="text-center mb-8">
            <div class="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-primary-container/80 text-primary mb-4 shadow-sm">
              <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
              </svg>
            </div>
            <h1 class="text-2xl sm:text-3xl font-bold tracking-tight text-on-surface">Create an Account</h1>
            <p class="text-sm text-on-surface-variant mt-2">Join HeartBridge to power high-impact NGO fundraising</p>
          </div>

          <!-- Error Alert -->
          <div v-if="errorMessage" class="mb-6 p-4 rounded-xl bg-error-container text-on-error-container text-xs font-medium flex items-center gap-3 border border-error/20">
            <svg class="w-5 h-5 text-error shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{{ errorMessage }}</span>
          </div>

          <!-- Form -->
          <form @submit.prevent="handleSignup" class="space-y-4 sm:space-y-5">
            <!-- Full Name Row -->
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div class="space-y-1.5">
                <label for="first-name" class="block text-xs font-semibold uppercase tracking-wider text-on-surface-variant">First Name *</label>
                <input
                  id="first-name"
                  v-model="firstName"
                  type="text"
                  required
                  placeholder="Jane"
                  class="w-full px-4 py-3 bg-surface-container-low border border-outline-variant rounded-xl text-sm text-on-surface placeholder:text-on-surface-variant/50 focus:bg-surface focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition-all duration-200"
                />
              </div>
              <div class="space-y-1.5">
                <label for="last-name" class="block text-xs font-semibold uppercase tracking-wider text-on-surface-variant">Last Name *</label>
                <input
                  id="last-name"
                  v-model="lastName"
                  type="text"
                  required
                  placeholder="Doe"
                  class="w-full px-4 py-3 bg-surface-container-low border border-outline-variant rounded-xl text-sm text-on-surface placeholder:text-on-surface-variant/50 focus:bg-surface focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition-all duration-200"
                />
              </div>
            </div>

            <!-- Email Input -->
            <div class="space-y-1.5">
              <label for="signup-email" class="block text-xs font-semibold uppercase tracking-wider text-on-surface-variant">Work / Personal Email *</label>
              <input
                id="signup-email"
                v-model="email"
                type="email"
                required
                placeholder="jane.doe@organization.org"
                class="w-full px-4 py-3 bg-surface-container-low border border-outline-variant rounded-xl text-sm text-on-surface placeholder:text-on-surface-variant/50 focus:bg-surface focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition-all duration-200"
              />
            </div>

            <!-- Organization / NGO (Optional) -->
            <div class="space-y-1.5">
              <label for="organization" class="block text-xs font-semibold uppercase tracking-wider text-on-surface-variant">NGO / Organization Name (Optional)</label>
              <input
                id="organization"
                v-model="organization"
                type="text"
                placeholder="e.g. Global Health Initiative"
                class="w-full px-4 py-3 bg-surface-container-low border border-outline-variant rounded-xl text-sm text-on-surface placeholder:text-on-surface-variant/50 focus:bg-surface focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition-all duration-200"
              />
            </div>

            <!-- Passwords Row -->
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div class="space-y-1.5">
                <label for="signup-password" class="block text-xs font-semibold uppercase tracking-wider text-on-surface-variant">Password *</label>
                <div class="relative">
                  <input
                    id="signup-password"
                    v-model="password"
                    :type="showPassword ? 'text' : 'password'"
                    required
                    placeholder="Min 8 chars"
                    class="w-full px-4 py-3 bg-surface-container-low border border-outline-variant rounded-xl text-sm text-on-surface placeholder:text-on-surface-variant/50 focus:bg-surface focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition-all duration-200 pr-10"
                  />
                  <button
                    type="button"
                    @click="togglePasswordVisibility"
                    class="absolute inset-y-0 right-0 pr-3 flex items-center text-on-surface-variant hover:text-primary transition-colors cursor-pointer"
                    tabindex="-1"
                  >
                    <svg v-if="!showPassword" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                    <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858-5.908a10.049 10.049 0 013.122-.463c4.478 0 8.268 2.943 9.542 7a9.97 9.97 0 01-2.49 4.15m-4.006 2.006a3 3 0 01-4.243-4.243m4.243 4.243L3 3l18 18" />
                    </svg>
                  </button>
                </div>
              </div>

              <div class="space-y-1.5">
                <label for="confirm-password" class="block text-xs font-semibold uppercase tracking-wider text-on-surface-variant">Confirm *</label>
                <input
                  id="confirm-password"
                  v-model="confirmPassword"
                  :type="showPassword ? 'text' : 'password'"
                  required
                  placeholder="Repeat password"
                  class="w-full px-4 py-3 bg-surface-container-low border border-outline-variant rounded-xl text-sm text-on-surface placeholder:text-on-surface-variant/50 focus:bg-surface focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition-all duration-200"
                />
              </div>
            </div>

            <!-- Terms Agreement -->
            <div class="flex items-start pt-1">
              <input
                id="agree-terms"
                v-model="agreeTerms"
                type="checkbox"
                required
                class="mt-0.5 w-4 h-4 text-primary bg-surface border-outline-variant rounded focus:ring-primary focus:ring-offset-0 cursor-pointer"
              />
              <label for="agree-terms" class="ml-2.5 text-xs text-on-surface-variant leading-relaxed select-none cursor-pointer">
                I agree to the <a href="#/terms" class="text-primary font-medium hover:underline">Terms of Service</a> and <a href="#/privacy" class="text-primary font-medium hover:underline">Privacy Policy</a>.
              </label>
            </div>

            <!-- Submit Button -->
            <AppButton
              id="signup-submit-btn"
              type="submit"
              variant="primary"
              :disabled="isLoading"
              class="w-full rounded-xl py-3.5 text-sm font-semibold tracking-normal uppercase-none transition-all duration-200 shadow-md hover:shadow-lg mt-2"
            >
              <span v-if="!isLoading">Register Account</span>
              <span v-else class="flex items-center gap-2">
                <svg class="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Creating Account...
              </span>
            </AppButton>
          </form>

          <!-- Bottom Redirect -->
          <div class="mt-8 text-center text-xs text-on-surface-variant">
            Already registered with HeartBridge?
            <router-link to="/login" class="font-bold text-primary hover:underline ml-1 transition-colors">Sign in here</router-link>
          </div>
        </div>
      </div>
    </main>

    <!-- Footer -->
    <AppFooter />
  </div>
</template>

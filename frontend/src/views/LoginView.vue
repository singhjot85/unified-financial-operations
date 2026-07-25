<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import AppBar from '../components/AppBar.vue';
import AppFooter from '../components/AppFooter.vue';
import AppButton from '../components/AppButton.vue';

const router = useRouter();

const email = ref('');
const password = ref('');
const rememberMe = ref(false);
const showPassword = ref(false);
const isLoading = ref(false);
const errorMessage = ref('');

const togglePasswordVisibility = () => {
  showPassword.value = !showPassword.value;
};

const handleLogin = () => {
  errorMessage.value = '';
  if (!email.value || !password.value) {
    errorMessage.value = 'Please enter both your email address and password.';
    return;
  }

  isLoading.value = True;
  // Simulate login request and route to MFA verification step
  setTimeout(() => {
    isLoading.value = False;
    router.push('/mfa');
  }, 600);
};

const handleSsoLogin = (provider: string) => {
  isLoading.value = True;
  setTimeout(() => {
    isLoading.value = False;
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
      <div class="w-full max-w-md">
        <!-- Card Container -->
        <div class="bg-surface rounded-2xl border border-outline-variant/60 shadow-lg p-6 sm:p-10 transition-all duration-300">

          <!-- Header & Logo -->
          <div class="text-center mb-8">
            <div class="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-primary-container/80 text-primary mb-4 shadow-sm">
              <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
            </div>
            <h1 class="text-2xl sm:text-3xl font-bold tracking-tight text-on-surface">Welcome Back</h1>
            <p class="text-sm text-on-surface-variant mt-2">Sign in to your HeartBridge donor & admin portal</p>
          </div>

          <!-- Error Alert -->
          <div v-if="errorMessage" class="mb-6 p-4 rounded-xl bg-error-container text-on-error-container text-xs font-medium flex items-center gap-3 border border-error/20">
            <svg class="w-5 h-5 text-error shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{{ errorMessage }}</span>
          </div>

          <!-- Form -->
          <form @submit.prevent="handleLogin" class="space-y-5">
            <!-- Email Input -->
            <div class="space-y-1.5">
              <label for="email" class="block text-xs font-semibold uppercase tracking-wider text-on-surface-variant">Email Address</label>
              <div class="relative">
                <input
                  id="email"
                  v-model="email"
                  type="email"
                  required
                  placeholder="name@organization.org"
                  class="w-full px-4 py-3 bg-surface-container-low border border-outline-variant rounded-xl text-sm text-on-surface placeholder:text-on-surface-variant/50 focus:bg-surface focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition-all duration-200"
                />
                <div class="absolute inset-y-0 right-0 pr-3.5 flex items-center pointer-events-none text-on-surface-variant/60">
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                </div>
              </div>
            </div>

            <!-- Password Input -->
            <div class="space-y-1.5">
              <div class="flex justify-between items-center">
                <label for="password" class="block text-xs font-semibold uppercase tracking-wider text-on-surface-variant">Password</label>
                <a href="#/forgot-password" class="text-xs font-semibold text-primary hover:underline transition-colors">Forgot password?</a>
              </div>
              <div class="relative">
                <input
                  id="password"
                  v-model="password"
                  :type="showPassword ? 'text' : 'password'"
                  required
                  placeholder="••••••••••••"
                  class="w-full px-4 py-3 bg-surface-container-low border border-outline-variant rounded-xl text-sm text-on-surface placeholder:text-on-surface-variant/50 focus:bg-surface focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition-all duration-200 pr-10"
                />
                <button
                  type="button"
                  @click="togglePasswordVisibility"
                  class="absolute inset-y-0 right-0 pr-3.5 flex items-center text-on-surface-variant hover:text-primary transition-colors cursor-pointer"
                  tabindex="-1"
                >
                  <svg v-if="!showPassword" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                  <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858-5.908a10.049 10.049 0 013.122-.463c4.478 0 8.268 2.943 9.542 7a9.97 9.97 0 01-2.49 4.15m-4.006 2.006a3 3 0 01-4.243-4.243m4.243 4.243L3 3l18 18" />
                  </svg>
                </button>
              </div>
            </div>

            <!-- Remember Me -->
            <div class="flex items-center">
              <input
                id="remember-me"
                v-model="rememberMe"
                type="checkbox"
                class="w-4 h-4 text-primary bg-surface border-outline-variant rounded focus:ring-primary focus:ring-offset-0 cursor-pointer"
              />
              <label for="remember-me" class="ml-2.5 text-xs font-medium text-on-surface-variant select-none cursor-pointer">
                Remember this device for 30 days
              </label>
            </div>

            <!-- Submit Button -->
            <AppButton
              id="login-submit-btn"
              type="submit"
              variant="primary"
              :disabled="isLoading"
              class="w-full rounded-xl py-3.5 text-sm font-semibold tracking-normal uppercase-none transition-all duration-200 shadow-md hover:shadow-lg"
            >
              <span v-if="!isLoading">Sign In</span>
              <span v-else class="flex items-center gap-2">
                <svg class="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Authenticating...
              </span>
            </AppButton>
          </form>

          <!-- Divider -->
          <div class="relative my-6">
            <div class="absolute inset-0 flex items-center">
              <div class="w-full border-t border-outline-variant/60"></div>
            </div>
            <div class="relative flex justify-center text-xs uppercase tracking-wider">
              <span class="bg-surface px-3 text-on-surface-variant/70 font-medium">Or continue with</span>
            </div>
          </div>

          <!-- Social / SSO Login Options -->
          <div class="grid grid-cols-2 gap-3">
            <button
              type="button"
              @click="handleSsoLogin('google')"
              class="flex items-center justify-center gap-2.5 px-4 py-2.5 bg-surface-container-low border border-outline-variant/80 rounded-xl text-xs font-semibold text-on-surface hover:bg-surface-container hover:border-outline transition-all cursor-pointer"
            >
              <svg class="w-4 h-4" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" />
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" />
              </svg>
              Google SSO
            </button>

            <button
              type="button"
              @click="handleSsoLogin('saml')"
              class="flex items-center justify-center gap-2.5 px-4 py-2.5 bg-surface-container-low border border-outline-variant/80 rounded-xl text-xs font-semibold text-on-surface hover:bg-surface-container hover:border-outline transition-all cursor-pointer"
            >
              <svg class="w-4 h-4 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5m3 0h4M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
              </svg>
              NGO SAML
            </button>
          </div>

          <!-- Bottom Redirect -->
          <div class="mt-8 text-center text-xs text-on-surface-variant">
            Don't have a HeartBridge account?
            <router-link to="/signup" class="font-bold text-primary hover:underline ml-1 transition-colors">Create an account</router-link>
          </div>
        </div>

        <!-- Security Footer Badge -->
        <div class="mt-6 text-center flex items-center justify-center gap-2 text-xs text-on-surface-variant/80">
          <svg class="w-4 h-4 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
          <span>256-Bit SSL Encrypted & SOC2 Compliant NGO Platform</span>
        </div>
      </div>
    </main>

    <!-- Footer -->
    <AppFooter />
  </div>
</template>

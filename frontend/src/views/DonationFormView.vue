<script setup lang="ts">
import { useRouter } from 'vue-router';
import AppBar from '../components/AppBar.vue';
import DonateForm from '../components/view/donate/DonateForm.vue';

const router = useRouter();

const handleBack = (e: Event) => {
  e.preventDefault();
  router.push('/');
};
</script>

<template>
  <div class="min-h-screen flex flex-col bg-background">
    <!-- Minimal Header with Back Navigation -->
    <AppBar minimal>
      <template #action>
        <a
          @click="handleBack"
          class="text-on-surface hover:text-primary text-sm font-semibold flex items-center gap-1.5 transition-colors cursor-pointer select-none font-sans"
          href="#"
        >
          <span class="material-symbols-outlined text-[16px]">arrow_back</span>
          Back to Campaign
        </a>
      </template>
    </AppBar>

    <!-- Main Transactional Canvas -->
    <main class="flex-grow flex flex-col justify-center">
      <DonateForm />
    </main>
  </div>
</template>

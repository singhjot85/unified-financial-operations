<script setup lang="ts">
import { onMounted } from 'vue';
import { useDonationStore } from './stores/donation';

const donationStore = useDonationStore();

onMounted(async () => {
  await donationStore.fetchCampaignDetails();
});
</script>

<template>
  <v-app class="bg-background min-h-screen">
    <router-view v-slot="{ Component, route }">
      <transition :name="(route.meta.transition as string) || 'fade'" mode="out-in">
        <component :is="Component" :key="route.path" />
      </transition>
    </router-view>
  </v-app>
</template>

<style>
/* Global resets or custom typography if necessary */
body {
  font-family: var(--font-sans);
  background-color: var(--background);
  color: var(--on-background);
  letter-spacing: -0.01em;
}
h1, h2, h3, h4, .font-serif {
  font-family: var(--font-headline);
}
/* Premium Editorial feel scrollbar */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
::-webkit-scrollbar-track {
  background: var(--background);
}
::-webkit-scrollbar-thumb {
  background: var(--outline-variant);
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
  background: var(--outline);
}
</style>

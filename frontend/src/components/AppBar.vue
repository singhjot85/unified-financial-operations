<script setup lang="ts">
import { useRouter } from 'vue-router';
import AppButton from './AppButton.vue';

interface Props {
  minimal?: boolean;
}

defineProps<Props>();

const router = useRouter();

const navigateToCampaign = () => {
  router.push('/');
};

const handleDonate = () => {
  router.push('/donate');
};
</script>

<template>
  <header class="bg-surface border-b border-outline-variant sticky top-0 z-50 w-full flex justify-between items-center px-6 md:px-12 py-4 max-w-container-max mx-auto h-20">
    <!-- Logo and Brand Name -->
    <div @click="navigateToCampaign" class="flex items-center gap-2 cursor-pointer hover:opacity-95 select-none">
      <img
        alt="HeartBridge Logo"
        class="h-10 w-10 object-contain"
        src="https://lh3.googleusercontent.com/aida-public/AB6AXuBuwCe8q0lYxUQUnfWb95tcuhSYimeb8ulBvDxxYMoUmjKlab1Op0cW3tR2plTyzhb-o8OaeXuGUIULxRKBPbH2jvjLIuEog0HpG9NwNvkhfcgfAx3XYgN9iDY3lRtCq87a5PvjYDWXE27bP3cF5DiRvq1waLd4ljmkJ7ldSv40rGOMJrwiRKzjLCTzulE9J4KzoFEyZNLxm0l6s-417RsIftRmkJGkxE4ZiBgn08dinbOaaZAwC3vvWqHOHlwilocU4WtgeQqMTek"
      />
      <span class="text-xl md:text-2xl font-sans tracking-tight font-bold text-[#00685F]">HeartBridge</span>
    </div>

    <!-- Navigation Menu (Hidden on minimal or mobile viewports) -->
    <nav v-if="!minimal" class="hidden md:flex items-center gap-8 text-sm font-medium">
      <a class="text-on-surface hover:text-primary transition-all duration-200" href="#/campaigns">Campaigns</a>
      <a class="text-on-surface hover:text-primary transition-all duration-200" href="#/about">About Us</a>
      <a class="text-on-surface hover:text-primary transition-all duration-200" href="#/impact">Impact</a>
      <a class="text-on-surface hover:text-primary transition-all duration-200" href="#/login">Login</a>
    </nav>

    <!-- Call to Action -->
    <div class="flex items-center gap-4">
      <!-- Back Link for transaction flow -->
      <slot name="action">
        <button
          v-if="!minimal"
          class="bg-[#00685F] text-white text-sm font-medium px-6 py-2.5 rounded-full hover:bg-[#004f48] active:scale-95 transition-all cursor-pointer shadow-sm"
          @click="handleDonate"
        >
          Donate Now
        </button>
      </slot>
    </div>
  </header>
</template>

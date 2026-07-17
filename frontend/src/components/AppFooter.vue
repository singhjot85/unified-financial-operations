<script setup lang="ts">
import { useRoute } from 'vue-router';

const route = useRoute();
</script>

<template>
  <footer class="bg-surface border-t border-outline-variant w-full py-10 px-6 md:px-12 flex flex-col md:flex-row justify-between items-start gap-6 max-w-container-max mx-auto mt-auto text-xs font-sans text-on-surface-variant">
    <!-- Brand / Contact -->
    <div class="flex flex-col gap-1 w-full md:w-auto text-center md:text-left">
      <span class="text-base font-bold text-on-surface">HeartBridge</span>
      <span class="text-on-surface-variant hover:text-primary transition-colors cursor-pointer text-xs">contact@heartbridge.ngo</span>
    </div>

    <!-- Links -->
    <div class="flex justify-center gap-8 w-full md:w-auto text-center font-medium text-on-surface-variant py-2 md:py-0">
      <a class="hover:text-primary transition-colors" href="#/privacy">Privacy Policy</a>
      <a class="hover:text-primary transition-colors" href="#/terms">Terms of Service</a>
    </div>

    <!-- Copyright & Powered -->
    <div class="flex flex-col items-center md:items-end gap-1 w-full md:w-auto text-center md:text-right">
      <span>© 2024 HeartBridge. All rights reserved.</span>
      <span class="text-on-surface-variant/75 text-[11px]">Powered by <span class="font-semibold text-primary">ImpactFlow.</span></span>
    </div>
  </footer>
</template>

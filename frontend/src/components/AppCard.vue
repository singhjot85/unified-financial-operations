<script setup lang="ts">
interface Props {
  variant?: 'flat' | 'outlined' | 'elevated' | 'glass';
  id?: string;
}

withDefaults(defineProps<Props>(), {
  variant: 'flat',
});
</script>

<template>
  <div
    :id="id"
    class="overflow-hidden transition-all duration-200"
    :class="{
      'bg-surface border border-outline-variant': variant === 'outlined',
      'bg-surface border border-outline-variant/60 p-6': variant === 'flat',
      'bg-surface-container border border-outline-variant/50 p-6': variant === 'elevated',
      'bg-surface-container/90 backdrop-blur-md border border-outline-variant/40': variant === 'glass'
    }"
  >
    <slot />
  </div>
</template>

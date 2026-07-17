<script setup lang="ts">
interface Props {
  variant?: 'primary' | 'secondary' | 'tonal' | 'text' | 'black';
  disabled?: boolean;
  type?: 'button' | 'submit' | 'reset';
  id?: string;
}

withDefaults(defineProps<Props>(), {
  variant: 'primary',
  disabled: false,
  type: 'button',
});

defineEmits<{
  (e: 'click', event: MouseEvent): void;
}>();
</script>

<template>
  <button
    :id="id"
    :type="type"
    :disabled="disabled"
    @click="$emit('click', $event)"
    class="text-xs uppercase tracking-widest font-bold px-8 py-4 transition-all duration-200 cursor-pointer focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none flex items-center justify-center gap-2"
    :class="{
      'bg-primary text-on-primary hover:bg-[#c92f3b] shadow-sm hover:shadow-md': variant === 'primary',
      'border border-on-background text-on-background bg-transparent hover:bg-on-background/5': variant === 'secondary',
      'bg-surface-container text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high': variant === 'tonal',
      'text-on-surface-variant hover:text-primary bg-transparent border-b border-transparent hover:border-primary pb-1': variant === 'text',
      'bg-[#1D1D1F] text-white hover:bg-[#333] shadow-md hover:shadow-lg': variant === 'black'
    }"
  >
    <slot />
  </button>
</template>

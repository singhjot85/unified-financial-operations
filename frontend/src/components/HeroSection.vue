<script setup lang="ts">
import { useRouter } from 'vue-router';

const router = useRouter();

const handleStartImpact = () => {
  router.push('/donate');
};
</script>

<template>
  <section class="relative w-full min-h-[500px] flex items-center justify-center py-20 px-6 md:px-12 bg-[#00201D] overflow-hidden">
    <!-- Background Image with Blend & Opacity Overlay -->
    <div class="absolute inset-0 z-0">
      <img
        class="w-full h-full object-cover opacity-55"
        alt="Diverse volunteers and community members working in sunlit garden"
        src="https://lh3.googleusercontent.com/aida-public/AB6AXuAQoe85UnmbAe8SR4DKBxK5dy2tu0E76ueNQ7LrRzOJiu9IyK-mOGUiX1J5LxE6YzMXPqBDJ3kq7_Bexqy61MbYsIfZWB7TSIc1S2bSvgNt8X9l4ssOR8wBMT0DTCG79kVNQ7lhhkt5AYwmFB4Zm5GzAZq1sABjo-5ptj08rn16az3ZccF08I-5bhNgUzxYo3Ea4Kph0GwNuDjqHTVLybkgNIYcQNfJG7wr0nz4onM8g3Lo2n8flfsAyPrUn_IPHLVklKWe5Ah6e4o"
      />
      <!-- Dark teal gradient overlay to ensure perfect text contrast -->
      <div class="absolute inset-0 bg-gradient-to-b from-[#00201D]/70 via-[#00201D]/60 to-[#00201D]/80"></div>
    </div>

    <!-- Hero Content -->
    <div class="relative z-10 max-w-[800px] text-center flex flex-col items-center gap-6">
      <h1 class="text-4xl md:text-[64px] font-sans font-bold tracking-tight text-white leading-[1.1] drop-shadow-sm">
        Build a Brighter Future Together
      </h1>

      <p class="text-lg md:text-xl text-white/90 max-w-[600px] leading-relaxed font-sans">
        Your contribution directly empowers local communities.
      </p>

      <div class="flex items-center justify-center mt-4">
        <button
          class="bg-[#00685F] text-white text-sm font-medium px-8 py-3.5 rounded-full hover:bg-[#00524a] active:scale-95 transition-all cursor-pointer shadow-lg tracking-wide"
          @click="handleStartImpact"
        >
          Start Your Impact
        </button>
      </div>
    </div>
  </section>
</template>

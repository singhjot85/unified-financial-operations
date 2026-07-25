import { defineStore } from "pinia";

export const useBrandingStore = defineStore('branding', {
    state: () => ({
        media: null as Object | null,
        prContent: null as Object | null
    }),

    getters: {
        // App wise getters
    },

    actions: {
        // API calls
    },

})

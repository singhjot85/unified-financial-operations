import { type RouteRecordRaw } from 'vue-router';

export const publicRoutes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Landing',
    component: () => import('../views/LandingView.vue'),
    meta: { transition: 'fade' }
  },
  {
    path: '/donate',
    name: 'DonationForm',
    component: () => import('../views/DonationFormView.vue'),
    meta: { transition: 'push' }
  },
  {
    path: '/thank-you',
    name: 'ThankYou',
    component: () => import('../views/ThankYouView.vue'),
    meta: { transition: 'push' }
  },
  {
    path: '/receipt',
    name: 'Receipt',
    component: () => import('../views/ReceiptView.vue'),
    meta: { transition: 'slide_up' }
  }
];

import { type RouteRecordRaw } from 'vue-router';

export const publicRoutes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Landing',
    component: () => import('../views/LandingView.vue'),
    meta: { transition: 'fade' }
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue'),
    meta: { transition: 'fade' }
  },
  {
    path: '/signup',
    name: 'Signup',
    component: () => import('../views/SignupView.vue'),
    meta: { transition: 'push' }
  },
  {
    path: '/mfa',
    name: 'MFA',
    component: () => import('../views/MfaView.vue'),
    meta: { transition: 'slide_up' }
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

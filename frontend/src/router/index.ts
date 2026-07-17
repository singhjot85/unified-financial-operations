import { createRouter, createWebHashHistory } from 'vue-router';
import { publicRoutes } from './public';

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    ...publicRoutes,
    // Redirect unknown paths to landing
    {
      path: '/:pathMatch(.*)*',
      redirect: '/'
    }
  ],
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition;
    } else {
      return { top: 0 };
    }
  }
});

// Custom transition hook or logging can go here
router.afterEach((to, from) => {
  // Can be used to set document title dynamically
  const title = (to.name as string) || 'HeartBridge';
  document.title = `HeartBridge - ${title}`;
});

export default router;

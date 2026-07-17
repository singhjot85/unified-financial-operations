import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import router from './router';
import './index.css';

// Vuetify
import { createVuetify } from 'vuetify';
import 'vuetify/styles';
import * as components from 'vuetify/components';
import * as directives from 'vuetify/directives';

const heartBridgeTheme = {
  dark: false,
  colors: {
    primary: '#00685f',
    secondary: '#006a63',
    background: '#f5faf8',
    surface: '#ffffff',
    'surface-variant': '#dee4e1',
    error: '#ba1a1a',
    'on-primary': '#ffffff',
    'on-secondary': '#ffffff',
  },
};

const vuetify = createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'heartBridgeTheme',
    themes: {
      heartBridgeTheme,
    },
  },
});

const app = createApp(App);
const pinia = createPinia();

app.use(pinia);
app.use(router);
app.use(vuetify);

app.mount('#app');

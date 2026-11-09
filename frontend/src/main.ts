import { createApp } from "vue";
import PrimeVue from "primevue/config";
import Aura from "@primeuix/themes/aura";
import { definePreset } from "@primeuix/themes";
import App from "./App.vue";
import { router } from "./router";
import "./style.css";
import "./tokens.css";
import "./portal.css";
import "./friendly.css";
const PortalTheme = definePreset(Aura, {
  semantic: {
    primary: {
      50: "#eff6ff",
      100: "#dbeafe",
      200: "#bfdbfe",
      300: "#93c5fd",
      400: "#60a5fa",
      500: "#1351b4",
      600: "#10459a",
      700: "#0c326f",
      800: "#092759",
      900: "#071d43",
      950: "#03112b",
    },
  },
});
createApp(App)
  .use(router)
  .use(PrimeVue, {
    theme: { preset: PortalTheme, options: { darkModeSelector: ".dark-mode" } },
  })
  .mount("#app");

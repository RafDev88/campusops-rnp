import { createRouter, createWebHistory } from "vue-router";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/account",
      name: "account",
      component: () => import("./views/Account.vue"),
    },
    {
      path: "/my-research",
      name: "my-research",
      component: () => import("./views/MyResearch.vue"),
    },
    {
      path: "/monitoring",
      name: "monitoring",
      component: () => import("./views/Monitoring.vue"),
    },
    {
      path: "/help",
      name: "help",
      component: () => import("./views/Help.vue"),
    },
    {
      path: "/flows",
      name: "flows",
      component: () => import("./views/Flows.vue"),
    },
    {
      path: "/reports",
      name: "reports",
      component: () => import("./views/Reports.vue"),
    },
    {
      path: "/reviews",
      name: "reviews",
      component: () => import("./views/Review.vue"),
    },
    {
      path: "/changes",
      name: "changes",
      component: () => import("./views/Review.vue"),
    },
    {
      path: "/policies",
      name: "policies",
      component: () => import("./views/Policies.vue"),
    },
    {
      path: "/",
      name: "overview",
      component: () => import("./views/Overview.vue"),
    },
    {
      path: "/search",
      name: "search",
      component: () => import("./views/Search.vue"),
    },
    {
      path: "/institutions",
      name: "institutions",
      component: () => import("./views/Institutions.vue"),
    },
    {
      path: "/publications",
      name: "publications",
      component: () => import("./views/Publications.vue"),
    },
    {
      path: "/researchers",
      name: "researchers",
      component: () => import("./views/Researcher.vue"),
    },
    {
      path: "/sources",
      name: "sources",
      component: () => import("./views/Sources.vue"),
    },
    {
      path: "/runs",
      name: "runs",
      component: () => import("./views/Runs.vue"),
    },
    {
      path: "/automation",
      name: "automation",
      component: () => import("./views/Automation.vue"),
    },
    {
      path: "/incidents",
      name: "incidents",
      component: () => import("./views/Incidents.vue"),
    },
    {
      path: "/radar",
      name: "radar",
      component: () => import("./views/Radar.vue"),
    },
    {
      path: "/quality",
      name: "quality",
      component: () => import("./views/Catalogs.vue"),
    },
    {
      path: "/datasets",
      name: "datasets",
      component: () => import("./views/Catalogs.vue"),
    },
    {
      path: "/settings",
      name: "settings",
      component: () => import("./views/Settings.vue"),
    },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition;
    if (
      (to.query.publication &&
        to.query.publication !== from.query.publication) ||
      (to.query.id && to.query.id !== from.query.id)
    )
      return { top: 0 };
    if (to.path !== from.path) return { top: 0 };
    return undefined;
  },
});

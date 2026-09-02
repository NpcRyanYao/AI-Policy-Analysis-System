import { createRouter, createWebHistory } from "vue-router";
import MainLayout from "./layouts/MainLayout.vue";
import Dashboard from "./views/Dashboard.vue";
import PolicyList from "./views/PolicyList.vue";
import PolicyDetail from "./views/PolicyDetail.vue";
import Subscriptions from "./views/Subscriptions.vue";
import Compare from "./views/Compare.vue";
import Ingest from "./views/Ingest.vue";

export default createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      component: MainLayout,
      children: [
        { path: "", name: "dashboard", component: Dashboard },
        { path: "policies", name: "policies", component: PolicyList },
        { path: "policies/:id", name: "policy-detail", component: PolicyDetail },
        { path: "subscriptions", name: "subscriptions", component: Subscriptions },
        { path: "compare", name: "compare", component: Compare },
        { path: "ingest", name: "ingest", component: Ingest },
      ],
    },
  ],
});

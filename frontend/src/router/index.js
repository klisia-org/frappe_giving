import { createRouter, createWebHistory } from "vue-router";
import CampaignForm from "../views/CampaignForm.vue";
import NotFound from "../views/NotFound.vue";

const routes = [
  {
    path: "/:formName",
    name: "CampaignForm",
    component: CampaignForm,
    props: true,
  },
  {
    path: "/:pathMatch(.*)*",
    name: "NotFound",
    component: NotFound,
  },
];

const router = createRouter({
  history: createWebHistory("/donate"),
  routes,
});

export default router;

import { createRouter, createWebHistory } from "vue-router";
import CampaignForm from "../views/CampaignForm.vue";
import NotFound from "../views/NotFound.vue";
import DonorPortal from "../views/DonorPortal.vue";
import ActiveDonations from "../views/portal/ActiveDonations.vue";
import DonationHistory from "../views/portal/DonationHistory.vue";
import YearlyReport from "../views/portal/YearlyReport.vue";
import PortalDonate from "../views/portal/PortalDonate.vue";

// Guests don't belong in the portal — send them to Frappe's login with a
// redirect-back so they land here after signing in. Uses a hard redirect
// because Frappe's /login is a server-rendered page outside this SPA.
function requireLogin(to, from, next) {
  const user = window.frappe_user;
  if (!user || user === "Guest") {
    const back = encodeURIComponent(
      (window.location.pathname || "/donate/donorportal") + (window.location.search || "")
    );
    window.location.replace(`/login?redirect-to=${back}`);
    return; // stop Vue router; navigation is taken over by window.location
  }
  next();
}

const routes = [
  {
    path: "/donorportal",
    component: DonorPortal,
    beforeEnter: requireLogin,
    children: [
      { path: "", name: "ActiveDonations", component: ActiveDonations },
      { path: "donate", name: "PortalDonate", component: PortalDonate },
      { path: "history", name: "DonationHistory", component: DonationHistory },
      { path: "receipts", name: "YearlyReport", component: YearlyReport },
    ],
  },
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

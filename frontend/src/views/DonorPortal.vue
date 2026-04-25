<template>
  <div class="min-h-screen bg-gray-50">
    <div v-if="loading" class="text-center py-24 text-gray-500">Loading…</div>

    <div
      v-else-if="error"
      class="mx-auto max-w-2xl mt-12 rounded-lg bg-red-50 border border-red-200 p-6 text-red-700"
    >
      <p class="font-medium">We couldn't load your donor portal.</p>
      <p class="text-sm mt-1">{{ error }}</p>
    </div>

    <div v-else>
      <header class="bg-white border-b border-gray-200">
        <div class="mx-auto max-w-4xl px-4 sm:px-6 py-6 flex items-center justify-between">
          <div>
            <p class="text-xs uppercase tracking-wide text-gray-500">Donor Portal</p>
            <h1 class="text-xl font-semibold text-gray-900">{{ donor.donor_name }}</h1>
            <p class="text-sm text-gray-500">{{ donor.email }}</p>
          </div>
          <a
            href="/api/method/logout"
            class="text-sm font-medium text-gray-500 hover:text-gray-700"
          >
            Sign out
          </a>
        </div>
        <nav class="mx-auto max-w-4xl px-4 sm:px-6">
          <div class="flex gap-1 -mb-px">
            <router-link
              v-for="tab in tabs"
              :key="tab.name"
              :to="{ name: tab.name }"
              class="px-4 py-3 text-sm font-medium border-b-2 transition-colors"
              :class="[
                $route.name === tab.name
                  ? 'border-sky-500 text-sky-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900',
              ]"
            >
              {{ tab.label }}
            </router-link>
          </div>
        </nav>
      </header>

      <main class="mx-auto max-w-4xl px-4 sm:px-6 py-8">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script>
export default {
  name: "DonorPortal",
  inject: ["$call"],
  provide() {
    return {
      donor: () => this.donor,
    };
  },
  data() {
    return {
      donor: null,
      loading: true,
      error: null,
      tabs: [
        { label: "Active Giving", name: "ActiveDonations" },
        { label: "Donate", name: "PortalDonate" },
        { label: "History", name: "DonationHistory" },
        { label: "Tax Receipts", name: "YearlyReport" },
      ],
    };
  },
  async mounted() {
    try {
      const profile = await this.$call(
        "frappe_giving.api.portal.get_donor_profile"
      );
      if (!profile) {
        this.error =
          "Your account is not linked to a donor record yet. Please contact us so we can associate your giving history.";
        return;
      }
      this.donor = profile;
    } catch (e) {
      // beforeEnter already redirects Guests, so anything we see here is a
      // genuine server error rather than an auth problem.
      this.error = e?.message || "Unable to load donor profile.";
    } finally {
      this.loading = false;
    }
  },
};
</script>

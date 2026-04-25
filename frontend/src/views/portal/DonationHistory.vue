<template>
  <section>
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-lg font-semibold text-gray-900">Donation History</h2>
      <select
        v-model="selectedYear"
        class="rounded-md border-gray-300 text-sm focus:border-sky-500 focus:ring-sky-500"
        @change="reload"
      >
        <option :value="null">All years</option>
        <option v-for="y in years" :key="y" :value="y">{{ y }}</option>
      </select>
    </div>

    <div v-if="loading && rows.length === 0" class="text-center py-16 text-gray-500">
      Loading…
    </div>

    <div
      v-else-if="error"
      class="rounded-md bg-red-50 border border-red-200 p-4 text-sm text-red-700"
    >
      {{ error }}
    </div>

    <div
      v-else-if="rows.length === 0"
      class="rounded-lg bg-white border border-gray-200 p-10 text-center text-gray-600"
    >
      No donations found{{ selectedYear ? ` for ${selectedYear}` : "" }}.
    </div>

    <div v-else class="rounded-lg bg-white shadow-sm border border-gray-200 px-5">
      <DonationRow v-for="row in rows" :key="row.name" :row="row" />
    </div>

    <div v-if="hasMore" class="mt-4 text-center">
      <button
        :disabled="loading"
        class="px-4 py-2 rounded-md border border-gray-300 text-sm font-medium text-gray-700 hover:border-gray-400 disabled:opacity-50"
        @click="loadMore"
      >
        {{ loading ? "Loading…" : "Load more" }}
      </button>
    </div>
  </section>
</template>

<script>
import DonationRow from "../../components/portal/DonationRow.vue";

const PAGE_SIZE = 50;

export default {
  name: "DonationHistory",
  components: { DonationRow },
  inject: ["$call"],
  data() {
    return {
      rows: [],
      years: [],
      selectedYear: null,
      hasMore: false,
      loading: false,
      error: null,
    };
  },
  async mounted() {
    try {
      this.years = await this.$call("frappe_giving.api.portal.get_available_years");
    } catch (e) {
      // Non-fatal — filter just won't populate.
      console.warn("Could not load years:", e);
    }
    await this.reload();
  },
  methods: {
    async reload() {
      this.rows = [];
      this.hasMore = false;
      await this.fetchPage(0);
    },
    async loadMore() {
      await this.fetchPage(this.rows.length);
    },
    async fetchPage(offset) {
      this.loading = true;
      this.error = null;
      try {
        const res = await this.$call(
          "frappe_giving.api.portal.get_donation_history",
          { year: this.selectedYear, limit: PAGE_SIZE, offset }
        );
        this.rows = offset === 0 ? res.rows : [...this.rows, ...res.rows];
        this.hasMore = res.has_more;
      } catch (e) {
        this.error = e?.message || "Unable to load history.";
      } finally {
        this.loading = false;
      }
    },
  },
};
</script>

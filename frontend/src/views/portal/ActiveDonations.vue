<template>
  <section>
    <div v-if="loading" class="text-center py-16 text-gray-500">Loading…</div>

    <div
      v-else-if="error"
      class="rounded-md bg-red-50 border border-red-200 p-4 text-sm text-red-700"
    >
      {{ error }}
    </div>

    <div
      v-else-if="donations.length === 0"
      class="rounded-lg bg-white border border-gray-200 p-10 text-center"
    >
      <p class="text-gray-700 font-medium">No active recurring gifts.</p>
      <p class="text-sm text-gray-500 mt-1">
        Want to start one?
        <router-link
          :to="{ name: 'PortalDonate' }"
          class="text-sky-600 font-medium hover:text-sky-700"
        >
          Give now →
        </router-link>
      </p>
    </div>

    <div v-else class="space-y-4">
      <article
        v-for="d in donations"
        :key="d.name"
        class="rounded-lg bg-white shadow-sm border border-gray-200 p-5"
      >
        <div class="flex items-start justify-between gap-4">
          <div>
            <p class="text-xs uppercase tracking-wide text-gray-500">
              {{ d.frequency }} gift
            </p>
            <p class="text-2xl font-semibold text-gray-900 mt-1">
              {{ formatAmount(d) }}
              <span class="text-sm font-normal text-gray-500">
                / {{ d.frequency.toLowerCase() }}
              </span>
            </p>
            <p class="mt-2 text-sm text-gray-700">
              {{ d.campaign_label || d.campaign }}
            </p>
          </div>
          <span
            class="inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700"
          >
            Active
          </span>
        </div>
        <dl class="mt-4 grid grid-cols-2 gap-3 text-sm">
          <div>
            <dt class="text-gray-500">Started</dt>
            <dd class="text-gray-800">{{ formatDate(d.donation_date) }}</dd>
          </div>
          <div>
            <dt class="text-gray-500">Last charged</dt>
            <dd class="text-gray-800">
              {{ d.last_payment_date ? formatDate(d.last_payment_date) : "—" }}
            </dd>
          </div>
        </dl>
        <p class="mt-3 text-xs text-gray-400 font-mono">{{ d.name }}</p>
      </article>
    </div>
  </section>
</template>

<script>
const CURRENCY_SYMBOLS = {
  USD: "$",
  EUR: "€",
  GBP: "£",
  BRL: "R$",
  CAD: "C$",
  AUD: "A$",
};

export default {
  name: "ActiveDonations",
  inject: ["$call"],
  data() {
    return {
      donations: [],
      loading: true,
      error: null,
    };
  },
  async mounted() {
    try {
      this.donations = await this.$call(
        "frappe_giving.api.portal.get_active_recurring_donations"
      );
    } catch (e) {
      this.error = e?.message || "Unable to load active donations.";
    } finally {
      this.loading = false;
    }
  },
  methods: {
    formatAmount(d) {
      const sym = CURRENCY_SYMBOLS[d.currency] || d.currency + " ";
      const num = Number(d.amount || 0).toLocaleString(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      });
      return `${sym}${num}`;
    },
    formatDate(raw) {
      if (!raw) return "";
      const d = new Date(raw);
      if (Number.isNaN(d.getTime())) return raw;
      return d.toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
      });
    },
  },
};
</script>

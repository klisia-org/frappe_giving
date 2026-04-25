<template>
  <section>
    <div class="flex items-center justify-between mb-4">
      <div>
        <h2 class="text-lg font-semibold text-gray-900">Consolidated Tax Receipt</h2>
        <p class="text-sm text-gray-500">
          Summary of all confirmed donations received during the selected year.
        </p>
      </div>
      <select
        v-if="years.length"
        v-model="selectedYear"
        class="rounded-md border-gray-300 text-sm focus:border-sky-500 focus:ring-sky-500"
        @change="reload"
      >
        <option v-for="y in years" :key="y" :value="y">{{ y }}</option>
      </select>
    </div>

    <div v-if="loading" class="text-center py-16 text-gray-500">Loading…</div>

    <div
      v-else-if="error"
      class="rounded-md bg-red-50 border border-red-200 p-4 text-sm text-red-700"
    >
      {{ error }}
    </div>

    <div
      v-else-if="!summary || summary.donation_count === 0"
      class="rounded-lg bg-white border border-gray-200 p-10 text-center text-gray-600"
    >
      No confirmed donations on record{{ selectedYear ? ` for ${selectedYear}` : "" }}.
    </div>

    <div v-else class="space-y-6">
      <div class="rounded-lg bg-white shadow-sm border border-gray-200 p-6">
        <div class="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <p class="text-xs uppercase tracking-wide text-gray-500">
              Tax year {{ summary.year }}
            </p>
            <p class="text-3xl font-semibold text-gray-900 mt-1">
              {{ summary.donation_count }}
              <span class="text-base font-normal text-gray-500">
                donation{{ summary.donation_count === 1 ? "" : "s" }}
              </span>
            </p>
            <div class="mt-3 space-y-1">
              <p
                v-for="row in summary.currency_breakdown"
                :key="row.currency"
                class="text-xl font-semibold text-gray-800"
              >
                {{ formatMoney(row.total, row.currency) }}
              </p>
              <p
                v-if="summary.currency_breakdown.length > 1 && summary.total_usd"
                class="text-sm text-gray-500"
              >
                ≈ {{ formatMoney(summary.total_usd, "USD") }} USD equivalent
              </p>
            </div>
          </div>
          <div class="flex flex-col items-end gap-2">
            <a
              :href="pdfUrl"
              target="_blank"
              rel="noopener"
              class="inline-flex items-center rounded-md bg-sky-500 px-4 py-2 text-sm font-medium text-white hover:bg-sky-600"
            >
              Download PDF
            </a>
            <button
              type="button"
              :disabled="emailing"
              class="inline-flex items-center rounded-md border border-sky-500 px-4 py-2 text-sm font-medium text-sky-600 hover:bg-sky-50 disabled:opacity-60"
              @click="emailToSelf"
            >
              {{ emailing ? "Sending…" : "Email me this" }}
            </button>
            <p
              v-if="emailNotice"
              class="text-xs text-emerald-700 max-w-xs text-right"
            >
              {{ emailNotice }}
            </p>
            <p
              v-else-if="emailError"
              class="text-xs text-red-600 max-w-xs text-right"
            >
              {{ emailError }}
            </p>
          </div>
        </div>
      </div>

      <div class="rounded-lg bg-white shadow-sm border border-gray-200 px-5">
        <DonationRow
          v-for="item in summary.line_items"
          :key="item.name"
          :row="item"
        />
      </div>

      <p class="text-xs text-gray-500 leading-relaxed">
        No goods or services were provided in exchange for these contributions.
        This statement is provided for your records; donations are tax-deductible
        to the extent allowed by law.
      </p>
    </div>
  </section>
</template>

<script>
import DonationRow from "../../components/portal/DonationRow.vue";

const CURRENCY_SYMBOLS = {
  USD: "$",
  EUR: "€",
  GBP: "£",
  BRL: "R$",
  CAD: "C$",
  AUD: "A$",
};

export default {
  name: "YearlyReport",
  components: { DonationRow },
  inject: ["$call"],
  data() {
    return {
      years: [],
      selectedYear: null,
      summary: null,
      loading: true,
      error: null,
      emailing: false,
      emailNotice: null,
      emailError: null,
    };
  },
  watch: {
    selectedYear() {
      // Stale notice for the prior year confuses the donor — reset.
      this.emailNotice = null;
      this.emailError = null;
    },
  },
  computed: {
    pdfUrl() {
      if (!this.selectedYear) return "#";
      return `/api/method/frappe_giving.api.receipts.download_yearly_statement?year=${this.selectedYear}`;
    },
  },
  async mounted() {
    try {
      this.years = await this.$call("frappe_giving.api.portal.get_available_years");
      this.selectedYear = this.years[0] || null;
    } catch (e) {
      this.error = e?.message || "Unable to load available years.";
      this.loading = false;
      return;
    }
    if (this.selectedYear) {
      await this.reload();
    } else {
      this.loading = false;
    }
  },
  methods: {
    async reload() {
      if (!this.selectedYear) return;
      this.loading = true;
      this.error = null;
      try {
        this.summary = await this.$call(
          "frappe_giving.api.portal.get_yearly_summary",
          { year: this.selectedYear }
        );
      } catch (e) {
        this.summary = null;
        this.error = e?.message || "Unable to load summary.";
      } finally {
        this.loading = false;
      }
    },
    async emailToSelf() {
      if (!this.selectedYear || this.emailing) return;
      this.emailing = true;
      this.emailNotice = null;
      this.emailError = null;
      try {
        const res = await this.$call(
          "frappe_giving.api.portal.email_yearly_statement_to_self",
          { year: this.selectedYear }
        );
        this.emailNotice = `Sent to ${res?.sent_to || "your email"}.`;
      } catch (e) {
        this.emailError = e?.message || "Couldn't send the email. Try again.";
      } finally {
        this.emailing = false;
      }
    },
    formatMoney(amount, currency) {
      const sym = CURRENCY_SYMBOLS[currency] || currency + " ";
      const num = Number(amount || 0).toLocaleString(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      });
      return `${sym}${num}`;
    },
  },
};
</script>

<template>
  <div class="flex items-center justify-between gap-4 py-3 border-b border-gray-100 last:border-0">
    <div class="min-w-0">
      <div class="flex items-center gap-2 flex-wrap">
        <span class="font-semibold text-gray-900">
          {{ formattedAmount }}
        </span>
        <span
          class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium"
          :class="frequencyClass"
        >
          {{ row.frequency }}
        </span>
        <span
          v-if="row.status"
          class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium"
          :class="statusClass"
        >
          {{ row.status }}
        </span>
      </div>
      <p class="text-sm text-gray-600 truncate">
        {{ row.campaign_label || row.campaign }}
      </p>
      <p class="text-xs text-gray-400 font-mono">{{ row.name }}</p>
    </div>
    <div class="text-right shrink-0">
      <p class="text-sm text-gray-700">{{ formattedDate }}</p>
      <a
        v-if="row.receipt_pdf_url"
        :href="row.receipt_pdf_url"
        target="_blank"
        rel="noopener"
        class="text-xs font-medium text-sky-600 hover:text-sky-700"
      >
        Receipt PDF →
      </a>
    </div>
  </div>
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

const STATUS_COLORS = {
  Paid: "bg-emerald-50 text-emerald-700",
  Invoiced: "bg-sky-50 text-sky-700",
  Draft: "bg-gray-100 text-gray-600",
  Failed: "bg-red-50 text-red-700",
  Refunded: "bg-amber-50 text-amber-700",
  Cancelled: "bg-gray-100 text-gray-600",
};

export default {
  name: "DonationRow",
  props: {
    row: { type: Object, required: true },
  },
  computed: {
    formattedAmount() {
      const sym = CURRENCY_SYMBOLS[this.row.currency] || this.row.currency + " ";
      const num = Number(this.row.amount || 0).toLocaleString(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      });
      return `${sym}${num}`;
    },
    formattedDate() {
      if (!this.row.donation_date && !this.row.date) return "";
      const raw = this.row.donation_date || this.row.date;
      const d = new Date(raw);
      if (Number.isNaN(d.getTime())) return raw;
      return d.toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
      });
    },
    frequencyClass() {
      return this.row.frequency === "One-Time"
        ? "bg-gray-100 text-gray-600"
        : "bg-sky-50 text-sky-700";
    },
    statusClass() {
      return STATUS_COLORS[this.row.status] || "bg-gray-100 text-gray-600";
    },
  },
};
</script>

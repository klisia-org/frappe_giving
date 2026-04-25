<template>
  <div>
    <label class="block text-sm font-medium mb-2">Donation Amount</label>
    <div class="grid grid-cols-3 gap-2">
      <button
        v-for="level in levels"
        :key="level.amount"
        type="button"
        :class="[
          'py-3 px-2 rounded-md border text-center transition-colors',
          isSelected(level.amount)
            ? 'fg-level-selected'
            : 'border-gray-300 hover:border-gray-400',
        ]"
        :style="isSelected(level.amount) ? null : { background: 'var(--fg-bg)' }"
        @click="select(level.amount)"
      >
        <div class="font-semibold">{{ formatAmount(level.amount) }}</div>
        <div
          v-if="level.label"
          :class="[
            'text-xs mt-0.5 leading-tight',
            isSelected(level.amount) ? 'fg-level-sub' : '',
          ]"
          :style="isSelected(level.amount) ? null : { color: 'var(--fg-muted)' }"
        >
          {{ level.label }}
        </div>
      </button>
    </div>

    <div v-if="allowCustom" class="mt-3">
      <label class="block text-xs font-medium mb-1" :style="{ color: 'var(--fg-muted)' }">
        Or enter a custom amount
      </label>
      <div class="relative">
        <span class="absolute left-3 top-1/2 -translate-y-1/2" :style="{ color: 'var(--fg-muted)' }">
          {{ currencySymbol }}
        </span>
        <input
          :value="customAmount"
          type="number"
          min="1"
          step="0.01"
          class="fg-input w-full pl-8 pr-3 py-2 border rounded-md"
          @input="onCustomInput($event.target.value)"
        />
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "GivingLevels",
  props: {
    amount: { type: [Number, String], default: null },
    levels: { type: Array, default: () => [] },
    currency: { type: String, default: "USD" },
    allowCustom: { type: Boolean, default: true },
  },
  emits: ["update:amount"],
  data() {
    return {
      customAmount: null,
    };
  },
  computed: {
    levelAmounts() {
      return (this.levels || []).map((l) => Number(l.amount));
    },
    currencySymbol() {
      return this.currency === "USD" ? "$" : this.currency;
    },
  },
  methods: {
    isSelected(value) {
      return Number(this.amount) === Number(value);
    },
    select(value) {
      this.customAmount = null;
      this.$emit("update:amount", Number(value));
    },
    onCustomInput(value) {
      const n = Number(value);
      this.customAmount = value;
      this.$emit("update:amount", isNaN(n) ? null : n);
    },
    formatAmount(value) {
      return `${this.currencySymbol}${Number(value).toLocaleString()}`;
    },
  },
};
</script>

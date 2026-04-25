<template>
  <div>
    <div v-if="loading" class="text-center py-8 text-gray-500 text-sm">
      Preparing secure payment…
    </div>

    <div v-show="!loading">
      <div ref="paymentElement" class="mb-4" />

      <div
        v-if="errorMessage"
        class="rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-700 mb-4"
      >
        {{ errorMessage }}
      </div>

      <button
        type="button"
        :disabled="confirming || !stripeReady"
        class="fg-btn w-full py-3 px-4 rounded-md font-medium"
        @click="handleConfirm"
      >
        {{ confirming ? "Processing…" : ctaLabel }}
      </button>

      <button
        type="button"
        :disabled="confirming"
        class="w-full mt-2 py-2 px-4 rounded-md text-sm text-gray-600 hover:text-gray-800"
        @click="$emit('back')"
      >
        Back
      </button>
    </div>
  </div>
</template>

<script>
import { loadStripe } from "@stripe/stripe-js";

export default {
  name: "PaymentSection",
  props: {
    clientSecret: { type: String, required: true },
    publishableKey: { type: String, required: true },
    ctaLabel: { type: String, default: "Confirm Donation" },
  },
  emits: ["paid", "failed", "back"],
  data() {
    return {
      stripe: null,
      elements: null,
      paymentElement: null,
      stripeReady: false,
      loading: true,
      confirming: false,
      errorMessage: null,
    };
  },
  async mounted() {
    try {
      this.stripe = await loadStripe(this.publishableKey);
      if (!this.stripe) throw new Error("Stripe.js failed to load.");

      this.elements = this.stripe.elements({
        clientSecret: this.clientSecret,
        appearance: { theme: "stripe" },
      });
      this.paymentElement = this.elements.create("payment");
      this.paymentElement.mount(this.$refs.paymentElement);
      this.paymentElement.on("ready", () => {
        this.stripeReady = true;
        this.loading = false;
      });
    } catch (e) {
      this.errorMessage = e?.message || "Failed to load payment form.";
      this.loading = false;
    }
  },
  beforeUnmount() {
    if (this.paymentElement) {
      this.paymentElement.unmount();
    }
  },
  methods: {
    async handleConfirm() {
      this.errorMessage = null;
      this.confirming = true;
      try {
        const { error, paymentIntent } = await this.stripe.confirmPayment({
          elements: this.elements,
          redirect: "if_required",
        });
        if (error) {
          this.errorMessage = error.message || "Payment could not be completed.";
          this.$emit("failed", error);
        } else {
          this.$emit("paid", paymentIntent);
        }
      } catch (e) {
        this.errorMessage = e?.message || "Unexpected error during payment.";
        this.$emit("failed", e);
      } finally {
        this.confirming = false;
      }
    },
  },
};
</script>

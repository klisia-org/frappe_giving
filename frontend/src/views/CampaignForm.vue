<template>
  <div class="fg-form py-8 px-4" :style="themeVars">
    <div class="mx-auto max-w-2xl">
      <div v-if="loading" class="text-center py-12 text-gray-500">Loading…</div>

      <div
        v-else-if="error"
        class="rounded-lg bg-red-50 border border-red-200 p-6 text-red-700"
      >
        <p class="font-medium">Couldn't load this donation form.</p>
        <p class="text-sm mt-1">{{ error }}</p>
      </div>

      <div
        v-else-if="step === 'thanks'"
        class="fg-card rounded-lg shadow-sm p-8"
      >
        <h1 class="text-2xl font-semibold mb-4">Thank you!</h1>
        <div
          class="prose prose-sm max-w-none"
          v-html="form.thank_you_message || defaultThanks"
        />
        <div
          v-if="finalizationError"
          class="mt-6 rounded-md bg-amber-50 border border-amber-200 p-3 text-sm text-amber-800"
        >
          <p class="font-medium">Note</p>
          <p class="mt-1">{{ finalizationError }}</p>
        </div>
        <p class="mt-6 text-sm" :style="{ color: 'var(--fg-muted)' }">
          Reference: <span class="font-mono">{{ donationName }}</span>
        </p>
        <a
          v-if="receiptUrl"
          :href="receiptUrl"
          target="_blank"
          rel="noopener"
          class="fg-link inline-flex items-center mt-3 text-sm font-medium"
        >
          Print your receipt →
        </a>
      </div>

      <div
        v-else-if="form"
        class="fg-card rounded-lg shadow-sm overflow-hidden"
      >
        <div
          v-if="portalMode && headlineOverride"
          class="px-6 sm:px-8 pt-6 pb-4 border-b border-sky-100 bg-sky-50"
        >
          <p class="text-sm font-medium text-sky-800">{{ headlineOverride }}</p>
        </div>

        <img
          v-if="form.image"
          :src="form.image"
          :alt="form.hero_title || form.form_title"
          class="w-full h-56 object-cover"
        />

        <div class="p-6 sm:p-8">
          <h1 class="text-2xl font-semibold">
            {{ form.hero_title || form.form_title }}
          </h1>
          <p v-if="form.subtitle" class="mt-1" :style="{ color: 'var(--fg-muted)' }">
            {{ form.subtitle }}
          </p>

          <div
            v-if="form.description"
            class="mt-4 prose prose-sm max-w-none"
            v-html="form.description"
          />

          <!-- STEP: details -->
          <form
            v-if="step === 'details'"
            class="mt-6 space-y-6"
            @submit.prevent="handleContinue"
          >
            <GivingLevels
              v-model:amount="selectedAmount"
              :levels="form.giving_levels"
              :currency="form.currency"
              :allow-custom="form.allow_custom_amount"
            />

            <div v-if="form.fee_recovery_display && feeAmount > 0" class="flex items-start">
              <input
                id="cover-fees"
                v-model="coverFees"
                type="checkbox"
                class="fg-check mt-1 h-4 w-4 rounded border-gray-300"
              />
              <label for="cover-fees" class="ml-2 text-sm">
                {{ feeMessage }}
              </label>
            </div>

            <div>
              <label class="block text-sm font-medium mb-2">Frequency</label>
              <div class="flex gap-2">
                <button
                  v-for="opt in frequencyOptions"
                  :key="opt"
                  type="button"
                  :class="[
                    'flex-1 py-2 px-3 rounded-md border text-sm font-medium transition-colors',
                    frequency === opt
                      ? 'fg-level-selected'
                      : 'border-gray-300 hover:border-gray-400',
                  ]"
                  :style="frequency === opt ? null : { background: 'var(--fg-bg)' }"
                  @click="frequency = opt"
                >
                  {{ opt }}
                </button>
              </div>
            </div>

            <DonorFields
              v-model:donor="donor"
              :form="form"
              :hide-identity="portalMode && !!prefilledDonor"
            />

            <div v-if="form.allow_anonymous" class="flex items-start">
              <input
                id="anonymous"
                v-model="donor.is_anonymous"
                type="checkbox"
                class="fg-check mt-1 h-4 w-4 rounded border-gray-300"
              />
              <label for="anonymous" class="ml-2 text-sm">
                Give anonymously (hide my name in public reports)
              </label>
            </div>

            <div
              v-if="submitError"
              class="rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-700"
            >
              {{ submitError }}
            </div>

            <button
              type="submit"
              :disabled="initiating"
              class="fg-btn w-full py-3 px-4 rounded-md font-medium"
            >
              {{ initiating ? "Preparing…" : form.cta_label || "Donate Now" }}
            </button>
          </form>

          <!-- STEP: payment -->
          <div v-if="step === 'payment'" class="mt-6">
            <div class="mb-4 rounded-md border border-gray-200 p-3 text-sm" :style="{ background: 'color-mix(in srgb, var(--fg-bg) 70%, #f3f4f6)' }">
              <div class="flex justify-between">
                <span>Donation</span>
                <span class="font-medium">
                  {{ currencySymbol }}{{ Number(selectedAmount).toLocaleString() }}
                  <span v-if="frequency !== 'One-Time'" :style="{ color: 'var(--fg-muted)' }">
                    / {{ frequency.toLowerCase() }}
                  </span>
                </span>
              </div>
              <div v-if="coverFees && feeAmount > 0" class="flex justify-between mt-1">
                <span>Fee covered</span>
                <span class="font-medium">{{ currencySymbol }}{{ feeAmount.toFixed(2) }}</span>
              </div>
              <div v-if="coverFees && feeAmount > 0" class="flex justify-between mt-1 pt-1 border-t border-gray-200">
                <span>Total charged</span>
                <span class="font-medium">{{ currencySymbol }}{{ chargeTotal.toFixed(2) }}</span>
              </div>
            </div>

            <PaymentSection
              :client-secret="clientSecret"
              :publishable-key="publishableKey"
              :cta-label="form.cta_label || 'Confirm Donation'"
              @paid="handlePaid"
              @failed="handlePaymentFailed"
              @back="step = 'details'"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import GivingLevels from "../components/GivingLevels.vue";
import DonorFields from "../components/DonorFields.vue";
import PaymentSection from "../components/PaymentSection.vue";

const DEFAULT_THANKS = "<p>Your generosity makes our mission possible.</p>";

// Parse a #rrggbb / #rgb string to linear RGB triplet in [0,1]. Returns
// null for unrecognized input so callers can fall back gracefully.
function parseHex(hex) {
  if (!hex || typeof hex !== "string") return null;
  let s = hex.trim().replace(/^#/, "");
  if (s.length === 3) s = s.split("").map((c) => c + c).join("");
  if (!/^[0-9a-fA-F]{6}$/.test(s)) return null;
  return [
    parseInt(s.slice(0, 2), 16) / 255,
    parseInt(s.slice(2, 4), 16) / 255,
    parseInt(s.slice(4, 6), 16) / 255,
  ];
}

// WCAG relative luminance. Anything > ~0.5 reads as a "light" color and
// wants dark text on top; below that, white text reads better.
function luminance(rgb) {
  const lin = rgb.map((c) =>
    c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)
  );
  return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2];
}

function readableText(hex, { strong }) {
  const rgb = parseHex(hex);
  if (!rgb) return strong ? "#374151" : "#6b7280";
  const light = luminance(rgb) > 0.5;
  if (light) return strong ? "#111827" : "#4b5563";
  return strong ? "#f9fafb" : "#d1d5db";
}

function readableBorder(hex, { stronger = false } = {}) {
  const rgb = parseHex(hex);
  if (!rgb) return stronger ? "#d1d5db" : "#e5e7eb";
  return luminance(rgb) > 0.5
    ? stronger ? "#d1d5db" : "#e5e7eb"
    : stronger ? "rgba(255,255,255,0.25)" : "rgba(255,255,255,0.15)";
}

// Shade a hex color by `amount` in [-1, 1]. Negative darkens, positive
// lightens. Used for the button hover state so authors don't need a
// separate field for it.
function shade(hex, amount) {
  const rgb = parseHex(hex);
  if (!rgb) return hex;
  const t = amount < 0 ? 0 : 1;
  const p = Math.abs(amount);
  const mix = rgb.map((c) => Math.round((c + (t - c) * p) * 255));
  return (
    "#" +
    mix
      .map((v) => Math.max(0, Math.min(255, v)).toString(16).padStart(2, "0"))
      .join("")
  );
}

export default {
  name: "CampaignForm",
  components: { GivingLevels, DonorFields, PaymentSection },
  inject: ["$call"],
  props: {
    formName: { type: String, required: true },
    // Portal-mode extras: when an authenticated donor reaches this form
    // through the donor portal, we already know who they are and what
    // partnership shape we want to nudge toward. None of these props are
    // required — the standalone /donate/<form> path leaves them unset.
    prefilledDonor: { type: Object, default: null },
    defaultFrequency: { type: String, default: null },
    portalMode: { type: Boolean, default: false },
    headlineOverride: { type: String, default: null },
  },
  data() {
    return {
      form: null,
      loading: true,
      error: null,
      step: "details",
      initiating: false,
      submitError: null,
      donationName: null,
      receiptUrl: null,
      finalizationError: null,
      clientSecret: null,
      publishableKey: null,
      paymentMode: null,
      selectedAmount: null,
      coverFees: false,
      frequency: this.defaultFrequency || "One-Time",
      donor: {
        full_name: this.prefilledDonor?.full_name || "",
        email: this.prefilledDonor?.email || "",
        phone: "",
        address_line: "",
        city: "",
        state: "",
        country: "",
        donor_note: "",
        is_anonymous: false,
      },
      defaultThanks: DEFAULT_THANKS,
      frequencyOptions: ["One-Time", "Monthly", "Quarterly", "Annual"],
    };
  },
  computed: {
    currencySymbol() {
      return this.form?.currency === "USD" ? "$" : this.form?.currency || "$";
    },
    feeAmount() {
      const amount = Number(this.selectedAmount) || 0;
      const pct = Number(this.form?.fee_percentage) || 0;
      const fixed = Number(this.form?.fee_fixed) || 0;
      const p = pct / 100;
      if (amount <= 0 || p <= 0 || p >= 1) return 0;
      // Match the server gross-up formula and round to cents.
      return Math.round(((amount * p + fixed) / (1 - p)) * 100) / 100;
    },
    feePercentEffective() {
      const amount = Number(this.selectedAmount) || 0;
      if (amount <= 0) return 0;
      return (this.feeAmount / amount) * 100;
    },
    feeMessage() {
      const template =
        this.form?.fee_recovery_message_template ||
        "Add {fee} to cover transaction fees so 100% of your gift reaches the cause.";
      const valueText =
        this.form?.fee_recovery_display === "Percentage"
          ? `${this.feePercentEffective.toFixed(2)}%`
          : `${this.currencySymbol}${this.feeAmount.toFixed(2)}`;
      return template.replace(/\{fee\}/g, valueText);
    },
    chargeTotal() {
      const amount = Number(this.selectedAmount) || 0;
      return amount + (this.coverFees ? this.feeAmount : 0);
    },
    themeVars() {
      // Only override vars the author actually set; everything else falls
      // back to the defaults in index.css (.fg-form rule), so an unthemed
      // form looks exactly like the original.
      const bg = this.form?.background;
      const btn = this.form?.button_color;
      const vars = {};
      if (bg) {
        vars["--fg-bg"] = bg;
        vars["--fg-body"] = readableText(bg, { strong: true });
        vars["--fg-muted"] = readableText(bg, { strong: false });
        vars["--fg-border"] = readableBorder(bg);
        vars["--fg-input-border"] = readableBorder(bg, { stronger: true });
      }
      if (btn) {
        vars["--fg-btn"] = btn;
        vars["--fg-btn-text"] = readableText(btn, { strong: true });
        vars["--fg-btn-hover"] = shade(btn, -0.12);
      }
      return vars;
    },
  },
  async mounted() {
    try {
      const form = await this.$call(
        "frappe_giving.api.donate.get_campaign_form",
        { form_name: this.formName }
      );
      this.form = form;
      const defaultLevel = (form.giving_levels || []).find((l) => l.is_default);
      this.selectedAmount = defaultLevel
        ? defaultLevel.amount
        : (form.giving_levels?.[0]?.amount ?? null);
      this.coverFees = form.fee_recovery_default === "Opt-out";
    } catch (e) {
      this.error = e?.message || "This donation form is not available.";
    } finally {
      this.loading = false;
    }
  },
  methods: {
    async handleContinue() {
      this.submitError = null;

      if (!this.selectedAmount || this.selectedAmount <= 0) {
        this.submitError = "Please choose a donation amount.";
        return;
      }
      // Identity check applies only when the donor can actually edit those
      // fields. In portal mode they're prefilled from the session and the
      // UI hides them, so this validation would just be noise.
      if (
        !(this.portalMode && this.prefilledDonor) &&
        (!this.donor.full_name || !this.donor.email)
      ) {
        this.submitError = "Please fill in your name and email.";
        return;
      }

      this.initiating = true;
      try {
        const res = await this.$call(
          "frappe_giving.api.stripe.initiate_stripe_payment",
          {
            form_name: this.formName,
            amount: this.selectedAmount,
            frequency: this.frequency,
            donor_data: this.donor,
            cover_fees: this.coverFees ? 1 : 0,
          }
        );
        this.donationName = res.donation;
        this.clientSecret = res.client_secret;
        this.publishableKey = res.publishable_key;
        this.paymentMode = res.mode;
        this.step = "payment";
      } catch (e) {
        this.submitError =
          e?.message || "We couldn't start your donation. Please try again.";
      } finally {
        this.initiating = false;
      }
    },
    async handlePaid(paymentIntent) {
      try {
        const res = await this.$call(
          "frappe_giving.api.stripe.confirm_donation_payment",
          {
            donation_name: this.donationName,
            payment_intent_id: paymentIntent.id,
          }
        );
        this.receiptUrl = res?.receipt_url || null;
        this.step = "thanks";
      } catch (e) {
        // Payment succeeded on Stripe but server-side finalization failed.
        // Surface the error so staff can investigate; the webhook is still
        // the safety net, but the donor should know there's a hiccup.
        this.step = "thanks";
        this.submitError = null;
        console.error("Sync confirm failed:", e);
        this.finalizationError =
          e?.message ||
          "Your payment was received, but we couldn't finalize the receipt automatically. Our team will follow up.";
      }
    },
    handlePaymentFailed() {
      // Error is shown inside PaymentSection; stay on payment step for retry.
    },
  },
};
</script>

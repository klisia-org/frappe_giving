<template>
  <div class="min-h-screen bg-gray-50 py-8 px-4">
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
        class="rounded-lg bg-white shadow-sm border border-gray-200 p-8"
      >
        <h1 class="text-2xl font-semibold text-gray-900 mb-4">Thank you!</h1>
        <div
          class="prose prose-sm max-w-none text-gray-700"
          v-html="form.thank_you_message || defaultThanks"
        />
        <div
          v-if="finalizationError"
          class="mt-6 rounded-md bg-amber-50 border border-amber-200 p-3 text-sm text-amber-800"
        >
          <p class="font-medium">Note</p>
          <p class="mt-1">{{ finalizationError }}</p>
        </div>
        <p class="mt-6 text-sm text-gray-500">
          Reference: <span class="font-mono">{{ donationName }}</span>
        </p>
        <a
          v-if="receiptUrl"
          :href="receiptUrl"
          target="_blank"
          rel="noopener"
          class="inline-flex items-center mt-3 text-sm font-medium text-sky-600 hover:text-sky-700"
        >
          Print your receipt →
        </a>
      </div>

      <div
        v-else-if="form"
        class="rounded-lg bg-white shadow-sm border border-gray-200 overflow-hidden"
      >
        <img
          v-if="form.image"
          :src="form.image"
          :alt="form.hero_title || form.form_title"
          class="w-full h-56 object-cover"
        />

        <div class="p-6 sm:p-8">
          <h1 class="text-2xl font-semibold text-gray-900">
            {{ form.hero_title || form.form_title }}
          </h1>
          <p v-if="form.subtitle" class="mt-1 text-gray-600">
            {{ form.subtitle }}
          </p>

          <div
            v-if="form.description"
            class="mt-4 prose prose-sm max-w-none text-gray-700"
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

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">
                Frequency
              </label>
              <div class="flex gap-2">
                <button
                  v-for="opt in frequencyOptions"
                  :key="opt"
                  type="button"
                  :class="[
                    'flex-1 py-2 px-3 rounded-md border text-sm font-medium transition-colors',
                    frequency === opt
                      ? 'bg-sky-500 border-sky-500 text-white'
                      : 'bg-white border-gray-300 text-gray-700 hover:border-gray-400',
                  ]"
                  @click="frequency = opt"
                >
                  {{ opt }}
                </button>
              </div>
            </div>

            <DonorFields v-model:donor="donor" :form="form" />

            <div v-if="form.allow_anonymous" class="flex items-start">
              <input
                id="anonymous"
                v-model="donor.is_anonymous"
                type="checkbox"
                class="mt-1 h-4 w-4 rounded border-gray-300 text-sky-500 focus:ring-sky-500"
              />
              <label for="anonymous" class="ml-2 text-sm text-gray-700">
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
              class="w-full py-3 px-4 rounded-md bg-sky-500 text-white font-medium hover:bg-sky-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {{ initiating ? "Preparing…" : form.cta_label || "Donate Now" }}
            </button>
          </form>

          <!-- STEP: payment -->
          <div v-if="step === 'payment'" class="mt-6">
            <div class="mb-4 rounded-md bg-gray-50 border border-gray-200 p-3 text-sm text-gray-700">
              <div class="flex justify-between">
                <span>Donation</span>
                <span class="font-medium">
                  {{ currencySymbol }}{{ Number(selectedAmount).toLocaleString() }}
                  <span v-if="frequency !== 'One-Time'" class="text-gray-500">
                    / {{ frequency.toLowerCase() }}
                  </span>
                </span>
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

export default {
  name: "CampaignForm",
  components: { GivingLevels, DonorFields, PaymentSection },
  inject: ["$call"],
  props: {
    formName: { type: String, required: true },
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
      frequency: "One-Time",
      donor: {
        full_name: "",
        email: "",
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
      if (!this.donor.full_name || !this.donor.email) {
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

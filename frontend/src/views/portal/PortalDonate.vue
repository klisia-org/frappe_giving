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
      v-else-if="!formName"
      class="rounded-lg bg-white border border-gray-200 p-10 text-center"
    >
      <p class="text-gray-700 font-medium">No active donation forms right now.</p>
      <p class="text-sm text-gray-500 mt-1">
        Please check back soon, or contact us if you'd like to give in another way.
      </p>
    </div>

    <CampaignForm
      v-else
      :key="formName"
      :form-name="formName"
      :prefilled-donor="prefilledDonor"
      :default-frequency="'Monthly'"
      :portal-mode="true"
      :headline-override="'Thank you for considering a monthly partnership with us.'"
    />
  </section>
</template>

<script>
import CampaignForm from "../CampaignForm.vue";

export default {
  name: "PortalDonate",
  components: { CampaignForm },
  inject: ["$call"],
  data() {
    return {
      loading: true,
      error: null,
      formName: null,
      prefilledDonor: null,
    };
  },
  async mounted() {
    try {
      const res = await this.$call(
        "frappe_giving.api.portal.get_portal_donate_form"
      );
      this.formName = res?.form_name || null;
      this.prefilledDonor = res?.donor || null;
    } catch (e) {
      this.error = e?.message || "We couldn't load a donation form.";
    } finally {
      this.loading = false;
    }
  },
};
</script>

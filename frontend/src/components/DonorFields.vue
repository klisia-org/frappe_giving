<template>
  <div class="space-y-4">
    <!-- Portal mode: identity is known from the session, so we replace
         the editable name/email fields with a confirmation line. Donor
         updates their profile in account settings, not here. -->
    <div
      v-if="hideIdentity"
      class="rounded-md border border-gray-200 bg-gray-50 px-3 py-2 text-sm"
    >
      Donating as <strong>{{ donor.full_name }}</strong>
      <span class="text-gray-500">({{ donor.email }})</span>
    </div>

    <div v-if="!hideIdentity && form.show_full_name">
      <label class="block text-sm font-medium mb-1">
        Full Name <span class="text-red-500">*</span>
      </label>
      <input
        :value="donor.full_name"
        type="text"
        required
        class="fg-input w-full px-3 py-2 border rounded-md"
        @input="update('full_name', $event.target.value)"
      />
    </div>

    <div v-if="!hideIdentity && form.show_email">
      <label class="block text-sm font-medium mb-1">
        Email <span class="text-red-500">*</span>
      </label>
      <input
        :value="donor.email"
        type="email"
        required
        class="fg-input w-full px-3 py-2 border rounded-md"
        @input="update('email', $event.target.value)"
      />
    </div>

    <div v-if="form.show_phone">
      <label class="block text-sm font-medium mb-1">Phone</label>
      <input
        :value="donor.phone"
        type="tel"
        class="fg-input w-full px-3 py-2 border rounded-md"
        @input="update('phone', $event.target.value)"
      />
    </div>

    <div v-if="form.show_address" class="space-y-3">
      <div>
        <label class="block text-sm font-medium mb-1">Address</label>
        <input
          :value="donor.address_line"
          type="text"
          placeholder="Street address"
          class="fg-input w-full px-3 py-2 border rounded-md"
          @input="update('address_line', $event.target.value)"
        />
      </div>
      <div class="grid grid-cols-2 gap-3">
        <input
          :value="donor.city"
          type="text"
          placeholder="City"
          class="fg-input w-full px-3 py-2 border rounded-md"
          @input="update('city', $event.target.value)"
        />
        <input
          :value="donor.state"
          type="text"
          placeholder="State / Region"
          class="fg-input w-full px-3 py-2 border rounded-md"
          @input="update('state', $event.target.value)"
        />
      </div>
      <input
        :value="donor.country"
        type="text"
        placeholder="Country"
        class="fg-input w-full px-3 py-2 border rounded-md"
        @input="update('country', $event.target.value)"
      />
    </div>

    <div v-if="form.show_donor_note">
      <label class="block text-sm font-medium mb-1">
        Message (optional)
      </label>
      <textarea
        :value="donor.donor_note"
        rows="3"
        class="fg-input w-full px-3 py-2 border rounded-md"
        @input="update('donor_note', $event.target.value)"
      />
    </div>
  </div>
</template>

<script>
export default {
  name: "DonorFields",
  props: {
    donor: { type: Object, required: true },
    form: { type: Object, required: true },
    hideIdentity: { type: Boolean, default: false },
  },
  emits: ["update:donor"],
  methods: {
    update(field, value) {
      this.$emit("update:donor", { ...this.donor, [field]: value });
    },
  },
};
</script>

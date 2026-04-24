<template>
  <div class="space-y-4">
    <div v-if="form.show_full_name">
      <label class="block text-sm font-medium text-gray-700 mb-1">
        Full Name <span class="text-red-500">*</span>
      </label>
      <input
        :value="donor.full_name"
        type="text"
        required
        class="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900 focus:ring-2 focus:ring-sky-500 focus:border-sky-500"
        @input="update('full_name', $event.target.value)"
      />
    </div>

    <div v-if="form.show_email">
      <label class="block text-sm font-medium text-gray-700 mb-1">
        Email <span class="text-red-500">*</span>
      </label>
      <input
        :value="donor.email"
        type="email"
        required
        class="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900 focus:ring-2 focus:ring-sky-500 focus:border-sky-500"
        @input="update('email', $event.target.value)"
      />
    </div>

    <div v-if="form.show_phone">
      <label class="block text-sm font-medium text-gray-700 mb-1">Phone</label>
      <input
        :value="donor.phone"
        type="tel"
        class="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900 focus:ring-2 focus:ring-sky-500 focus:border-sky-500"
        @input="update('phone', $event.target.value)"
      />
    </div>

    <div v-if="form.show_address" class="space-y-3">
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Address</label>
        <input
          :value="donor.address_line"
          type="text"
          placeholder="Street address"
          class="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900 focus:ring-2 focus:ring-sky-500 focus:border-sky-500"
          @input="update('address_line', $event.target.value)"
        />
      </div>
      <div class="grid grid-cols-2 gap-3">
        <input
          :value="donor.city"
          type="text"
          placeholder="City"
          class="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900 focus:ring-2 focus:ring-sky-500 focus:border-sky-500"
          @input="update('city', $event.target.value)"
        />
        <input
          :value="donor.state"
          type="text"
          placeholder="State / Region"
          class="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900 focus:ring-2 focus:ring-sky-500 focus:border-sky-500"
          @input="update('state', $event.target.value)"
        />
      </div>
      <input
        :value="donor.country"
        type="text"
        placeholder="Country"
        class="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900 focus:ring-2 focus:ring-sky-500 focus:border-sky-500"
        @input="update('country', $event.target.value)"
      />
    </div>

    <div v-if="form.show_donor_note">
      <label class="block text-sm font-medium text-gray-700 mb-1">
        Message (optional)
      </label>
      <textarea
        :value="donor.donor_note"
        rows="3"
        class="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900 focus:ring-2 focus:ring-sky-500 focus:border-sky-500"
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
  },
  emits: ["update:donor"],
  methods: {
    update(field, value) {
      this.$emit("update:donor", { ...this.donor, [field]: value });
    },
  },
};
</script>

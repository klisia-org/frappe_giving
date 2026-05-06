<template>
  <div class="portal-app">
    <PortalHeader brand-href="/donate/donorportal" />
    <router-view />
  </div>
</template>

<script setup>
import { PortalHeader } from '@seminary/portal-shell';
</script>

<style>
.portal-app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}
</style>

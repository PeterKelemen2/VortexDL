<script setup>
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import NavBar from '@/components/NavBar.vue'

const auth = useAuthStore()
const route = useRoute()
</script>

<template>
  <NavBar v-if="auth.isAuthenticated && !route.meta.guestOnly" />
  <router-view></router-view>
</template>

<style scoped></style>

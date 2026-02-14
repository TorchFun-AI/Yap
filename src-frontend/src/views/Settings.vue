<script setup lang="ts">
/**
 * Settings View
 * Configuration page for Yap
 */
</script>

<template>
  <div class="settings-view">
    <h2>Settings</h2>

    <a-form layout="vertical">
      <a-form-item label="Language">
        <a-select default-value="zh-CN">
          <a-select-option value="zh-CN">Chinese (Simplified)</a-select-option>
          <a-select-option value="en-US">English (US)</a-select-option>
        </a-select>
      </a-form-item>

      <a-form-item label="VAD Sensitivity">
        <a-slider :default-value="50" />
      </a-form-item>

      <a-form-item label="Auto Start">
        <a-switch />
      </a-form-item>
    </a-form>
  </div>
</template>

<style scoped>
.settings-view {
  padding: 24px;
  max-width: 480px;
  margin: 0 auto;
}

h2 {
  margin-bottom: 24px;
}
</style>

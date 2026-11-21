<script setup lang="ts">
import { ref, watch } from 'vue'
import { Clock } from '@element-plus/icons-vue'

import { minutesToTime, parseTime } from '@/utils/time'

const props = withDefaults(
  defineProps<{
    modelValue: number | null | undefined
    placeholder?: string
    disabled?: boolean
    allow24?: boolean
  }>(),
  {
    placeholder: '09:00',
    disabled: false,
    allow24: true,
  },
)

const emit = defineEmits<{
  (event: 'update:modelValue', value: number | null): void
}>()

const text = ref(minutesToTime(props.modelValue, props.allow24))

watch(
  () => props.modelValue,
  (value) => {
    const parsed = parseTime(text.value)
    if (parsed !== (value ?? null)) {
      text.value = minutesToTime(value, props.allow24)
    }
  },
)

function commit() {
  if (!text.value.trim()) {
    if (props.modelValue !== null && props.modelValue !== undefined) {
      emit('update:modelValue', null)
    }
    return
  }
  const parsed = parseTime(text.value)
  if (parsed === null || (!props.allow24 && parsed >= 1440)) {
    text.value = minutesToTime(props.modelValue, props.allow24)
    return
  }
  emit('update:modelValue', parsed)
  text.value = minutesToTime(parsed, props.allow24)
}
</script>

<template>
  <el-input
    v-model="text"
    :placeholder="placeholder"
    :disabled="disabled"
    maxlength="5"
    clearable
    @blur="commit"
    @keyup.enter="commit"
  >
    <template #prefix>
      <el-icon><Clock /></el-icon>
    </template>
  </el-input>
</template>

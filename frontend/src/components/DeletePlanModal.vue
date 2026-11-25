<template>
  <n-modal
    :show="show" preset="card" title="删除计划" class="del-modal"
    :mask-closable="false" @update:show="onShow"
  >
    <p v-if="note" class="tip">{{ note }}</p>
    <p class="ask">为防止误操作，请输入下面的文字，再点「确定删除」：</p>
    <p class="phrase">我确认要删除计划</p>
    <n-input
      v-model:value="text" autofocus
      placeholder="请输入：我确认要删除计划"
      :status="text && !ok ? 'error' : undefined"
      @keyup.enter="confirm"
    />
    <p v-if="text && !ok" class="err">文字不一致，请照抄上方文字</p>
    <template #footer>
      <div class="foot">
        <n-button @click="close">取消</n-button>
        <n-button type="error" :disabled="!ok" @click="confirm">确定删除</n-button>
      </div>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { NButton, NInput, NModal } from "naive-ui";

const PHRASE = "我确认要删除计划";

const props = withDefaults(defineProps<{ show: boolean; note?: string }>(), { note: "" });
const emit = defineEmits<{
  "update:show": [value: boolean];
  confirm: [];
}>();

const text = ref("");
const ok = computed(() => text.value.trim() === PHRASE);

// 每次打开都清空，避免上次输入残留直接通过
watch(
  () => props.show,
  (v) => {
    if (v) text.value = "";
  },
);

function onShow(v: boolean): void {
  emit("update:show", v);
}
function close(): void {
  emit("update:show", false);
}
function confirm(): void {
  if (!ok.value) return;
  emit("update:show", false);
  emit("confirm");
}
</script>

<style scoped>
.tip { margin: 0 0 10px; color: var(--c-text-2); font-size: 13.5px; line-height: 1.6; }
.ask { margin: 0 0 8px; color: var(--c-text); font-size: 14px; }
.phrase {
  margin: 0 0 10px;
  padding: 8px 12px;
  border-radius: 8px;
  background: var(--c-danger-soft, #fef2f2);
  color: var(--c-danger, #dc2626);
  font-size: 16px;
  font-weight: 800;
  letter-spacing: 0.04em;
  text-align: center;
}
.err { margin: 8px 0 0; color: var(--c-danger, #dc2626); font-size: 12.5px; }
.foot { display: flex; justify-content: flex-end; gap: 10px; }
</style>

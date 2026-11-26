<template>
  <n-modal v-model:show="show" preset="card" title="额度设置" class="quota-modal">
    <div v-if="user" class="quota">
      <div class="q-user">
        <span class="adm-avatar">{{ initial }}</span>
        <span class="q-uid">
          <b>{{ user.display_name || user.username }}</b>
          <i class="adm-mono">@{{ user.username }}</i>
        </span>
        <i class="adm-tag" :class="user.ai_enabled ? 'ok' : ''">{{ user.ai_enabled ? "已开通" : "未开通" }}</i>
      </div>

      <div class="q-stats">
        <div><span>累计已用</span><b class="tnum">{{ fmtYuan(user.credit_used_milli) }}</b></div>
        <div><span>当前总额度</span><b class="tnum">{{ fmtYuan(user.credit_budget_milli) }}</b></div>
        <div><span>当前剩余</span><b class="tnum">{{ fmtYuan(user.remaining_milli) }}</b></div>
      </div>

      <div class="q-bar">
        <i :class="tone" :style="{ width: pct + '%' }"></i>
      </div>

      <label class="adm-field">
        <span class="adm-flabel">一次性总额度 <i class="adm-opt">元</i></span>
        <n-input-number
          v-model:value="qCredit" :min="0" :step="0.5" :precision="2" clearable
          placeholder="留空 = 跟随全局默认" style="width: 100%"
        />
        <span class="adm-fhint">留空跟随全局默认（{{ fmtYuan(user.default_credit_milli) }}）；填写后只对这个账号生效。</span>
      </label>

      <div class="q-quick">
        <n-button size="small" secondary @click="addQuota(0.5)">+0.5 元</n-button>
        <n-button size="small" secondary @click="addQuota(1)">+1 元</n-button>
        <n-button size="small" secondary @click="addQuota(2)">+2 元</n-button>
        <n-button size="small" quaternary @click="qCredit = null">跟随默认</n-button>
      </div>

      <div class="q-preview" :class="{ warn: belowUsed }">
        <span>调整后剩余</span>
        <b class="tnum">{{ fmtYuan(qRemaining) }}</b>
        <i v-if="belowUsed">低于已用额度，保存后付费 AI 会立即暂停</i>
      </div>

      <p class="adm-fhint">额度是一次性总额，不会按月重置；调高即可继续使用。已用金额按历史记账累计。</p>

      <div class="q-actions">
        <n-button quaternary @click="show = false">取消</n-button>
        <n-button type="primary" :loading="busy" @click="save">保存</n-button>
      </div>
    </div>
  </n-modal>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { NButton, NInputNumber, NModal } from "naive-ui";
import { fmtYuan } from "./format";
import type { AdminUserRow } from "./types";

const props = defineProps<{ user: AdminUserRow | null; busy?: boolean }>();
const emit = defineEmits<{ (e: "save", creditMilli: number | null): void }>();
const show = defineModel<boolean>("show", { required: true });

const qCredit = ref<number | null>(null);

const initial = computed(() => {
  const name = props.user?.display_name || props.user?.username || "?";
  return Array.from(name)[0]?.toUpperCase() ?? "?";
});

const qBudgetMilli = computed(() => {
  const u = props.user;
  if (!u) return 0;
  return qCredit.value == null ? u.default_credit_milli : Math.round(qCredit.value * 1000);
});
const qRemaining = computed(() =>
  Math.max(0, qBudgetMilli.value - (props.user?.credit_used_milli ?? 0)),
);
const belowUsed = computed(() =>
  !!props.user && qBudgetMilli.value < props.user.credit_used_milli,
);
const pct = computed(() => {
  const u = props.user;
  if (!u || qBudgetMilli.value <= 0) return 100;
  return Math.min(100, Math.round((u.credit_used_milli / qBudgetMilli.value) * 100));
});
const tone = computed(() => {
  if (!props.user) return "ok";
  if (qRemaining.value <= 0) return "danger";
  if (props.user.alert_stage === 1) return "warn";
  return "ok";
});

watch(
  () => [show.value, props.user?.id] as const,
  ([open]) => {
    if (!open || !props.user) return;
    qCredit.value = props.user.ai_credit_milli === null
      ? null
      : props.user.ai_credit_milli / 1000;
  },
  { immediate: true },
);

function addQuota(delta: number): void {
  const base = qCredit.value == null
    ? (props.user?.credit_budget_milli ?? 0) / 1000
    : qCredit.value;
  qCredit.value = Math.max(0, Math.round((base + delta) * 100) / 100);
}

function save(): void {
  emit("save", qCredit.value == null ? null : Math.round(qCredit.value * 1000));
}
</script>

<style scoped>
.quota { display: flex; flex-direction: column; gap: 14px; }
.q-user { display: flex; align-items: center; gap: 10px; }
.q-uid { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
.q-uid b { font-size: 14px; color: var(--c-text); }
.q-uid i { font-style: normal; font-size: 11.5px; color: var(--c-text-3); }
.q-user .adm-tag { margin-left: auto; }
.q-user .adm-tag.ok { background: var(--c-primary-soft); color: var(--c-primary-strong); }
.q-stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
.q-stats div {
  display: flex; flex-direction: column; gap: 3px; padding: 9px 10px;
  border-radius: var(--r-sm); background: var(--c-mint-bg); border: 1px solid var(--c-line);
}
.q-stats span { font-size: 11.5px; color: var(--c-text-3); }
.q-stats b { font-size: 13px; color: var(--c-text); }
.q-bar { height: 8px; border-radius: 999px; background: #edf3ef; overflow: hidden; margin-top: -6px; }
.q-bar i { display: block; height: 100%; border-radius: 999px; background: var(--c-primary); transition: width 0.2s ease; }
.q-bar i.warn { background: var(--c-accent, #d97706); }
.q-bar i.danger { background: var(--c-danger, #dc2626); }
.q-quick { display: flex; gap: 8px; flex-wrap: wrap; margin-top: -6px; }
.q-preview {
  display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap;
  padding: 10px 12px; border-radius: var(--r-sm); background: var(--c-primary-soft);
  font-size: 12.5px; color: var(--c-text-2);
}
.q-preview b { font-size: 16px; color: var(--c-primary-strong); }
.q-preview i { font-style: normal; font-size: 11.5px; color: var(--c-text-3); }
.q-preview.warn { background: var(--c-accent-soft, #fff7ed); }
.q-preview.warn b { color: var(--c-accent, #b45309); }
.q-preview.warn i { color: var(--c-accent, #b45309); }
.q-actions { display: flex; justify-content: flex-end; gap: 8px; }
@media (max-width: 520px) { .q-stats { grid-template-columns: 1fr; } }
</style>

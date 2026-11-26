<template>
  <article class="ucard" :class="{ off: !u.ai_enabled, admin: u.is_admin }">
    <header class="uc-head">
      <span class="adm-avatar">{{ initial }}</span>
      <span class="uc-id">
        <b>{{ u.display_name || u.username }}</b>
        <i class="adm-mono">@{{ u.username }}</i>
      </span>
      <span class="uc-tags">
        <i v-if="u.is_admin" class="adm-tag admin">管理员</i>
        <i class="adm-tag" :class="statusClass">{{ statusText }}</i>
      </span>
    </header>

    <div class="uc-perm">
      <span class="uc-perm-txt">
        <b>AI 权限</b>
        <i>跟读评分 · 实时对话</i>
      </span>
      <n-switch
        size="small"
        :value="u.ai_enabled"
        :loading="busy"
        :aria-label="`${u.username} 的 AI 权限`"
        @update:value="(v: boolean) => emit('toggle-ai', u, v)"
      />
    </div>

    <div class="uc-quota">
      <div class="uc-qrow">
        <span>总额度</span>
        <b class="tnum">{{ u.unlimited ? `已用 ${fmtYuanShort(u.credit_used_milli)} 元 · 不限` : `${fmtYuanShort(u.credit_used_milli)} / ${fmtYuanShort(u.credit_budget_milli)} 元` }}</b>
      </div>
      <div v-if="!u.unlimited" class="uc-bar">
        <i :class="tone" :style="{ width: pct + '%' }"></i>
      </div>
      <div class="uc-qmeta">
        <span v-if="!u.ai_enabled">当前未开通，开通后按总额度使用</span>
        <span v-else-if="u.unlimited">管理员账号不消耗总额度，仅记录用量</span>
        <span v-else>剩余 {{ fmtYuan(u.remaining_milli) }}</span>
        <span v-if="u.credit_custom && !u.unlimited" class="uc-custom">单独设置</span>
        <span v-else-if="!u.unlimited" class="uc-custom">跟随默认</span>
      </div>
    </div>

    <footer class="uc-ops">
      <n-button v-if="!u.unlimited" size="tiny" secondary @click="emit('open-quota', u)">额度</n-button>
      <n-button size="tiny" secondary @click="emit('import-words', u)">导入生词</n-button>
      <n-button size="tiny" secondary :loading="resetBusy" @click="emit('reset-password', u)">重置密码</n-button>
      <n-button v-if="u.alert_stage > 0" size="tiny" quaternary @click="emit('reset-alert', u)">清除告警</n-button>
    </footer>
  </article>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { NButton, NSwitch } from "naive-ui";
import { fmtYuan, fmtYuanShort } from "./format";
import type { AdminUserRow } from "./types";

const props = defineProps<{ u: AdminUserRow; busy?: boolean; resetBusy?: boolean }>();
const emit = defineEmits<{
  (e: "toggle-ai", u: AdminUserRow, on: boolean): void;
  (e: "open-quota", u: AdminUserRow): void;
  (e: "import-words", u: AdminUserRow): void;
  (e: "reset-password", u: AdminUserRow): void;
  (e: "reset-alert", u: AdminUserRow): void;
}>();

const initial = computed(() => {
  const name = props.u.display_name || props.u.username || "?";
  return Array.from(name)[0]?.toUpperCase() ?? "?";
});

const exhausted = computed(
  () => !props.u.unlimited && props.u.ai_enabled && props.u.remaining_milli <= 0,
);

const statusText = computed(() => {
  if (!props.u.ai_enabled) return "未开通";
  if (props.u.is_admin) return "不限额度";
  if (exhausted.value) return "额度用尽";
  if (props.u.alert_stage === 1) return "接近上限";
  return "已开通";
});

const statusClass = computed(() => {
  if (!props.u.ai_enabled) return "";
  if (exhausted.value) return "danger";
  if (props.u.alert_stage === 1) return "warn";
  return "ok";
});

const pct = computed(() => {
  const budget = props.u.credit_budget_milli;
  if (budget <= 0) return 100;
  return Math.min(100, Math.round((props.u.credit_used_milli / budget) * 100));
});

const tone = computed(() => {
  if (exhausted.value) return "danger";
  if (props.u.alert_stage === 1) return "warn";
  return "ok";
});
</script>

<style scoped>
.ucard {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px 15px 12px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-card);
  background: var(--c-card);
  box-shadow: var(--shadow-1);
  min-width: 0;
}
.ucard.off { background: #fbfcfb; }
.ucard.admin { border-color: #cfe3f5; }

.uc-head { display: flex; align-items: center; gap: 10px; min-width: 0; }
.uc-id { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
.uc-id b { font-size: 14px; font-weight: 800; color: var(--c-text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.uc-id i { font-style: normal; font-size: 11.5px; color: var(--c-text-3); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.uc-tags { margin-left: auto; display: flex; gap: 5px; flex-wrap: wrap; justify-content: flex-end; }
.adm-tag.ok { background: var(--c-primary-soft); color: var(--c-primary-strong); }

.uc-perm {
  display: flex; align-items: center; justify-content: space-between; gap: 10px;
  padding: 9px 11px; border-radius: var(--r-sm);
  background: var(--c-mint-bg); border: 1px solid var(--c-line);
}
.ucard.off .uc-perm { background: #f5f7f5; }
.uc-perm-txt { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
.uc-perm-txt b { font-size: 12.5px; color: var(--c-text); }
.uc-perm-txt i { font-style: normal; font-size: 11.5px; color: var(--c-text-3); }

.uc-quota { display: flex; flex-direction: column; gap: 6px; }
.uc-qrow { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; font-size: 12px; color: var(--c-text-2); }
.uc-qrow b { font-size: 12.5px; color: var(--c-text); font-weight: 700; }
.uc-bar { height: 7px; border-radius: 999px; background: #edf3ef; overflow: hidden; }
.uc-bar i { display: block; height: 100%; border-radius: 999px; background: var(--c-primary); transition: width 0.2s ease; }
.uc-bar i.warn { background: var(--c-accent, #d97706); }
.uc-bar i.danger { background: var(--c-danger, #dc2626); }
.uc-qmeta { display: flex; align-items: center; justify-content: space-between; gap: 8px; font-size: 11.5px; color: var(--c-text-3); }
.uc-custom { flex: none; padding: 1px 7px; border-radius: var(--r-pill); background: var(--c-mint-bg); color: var(--c-text-2); }

.uc-ops { display: flex; gap: 6px; flex-wrap: wrap; margin-top: auto; padding-top: 2px; }
</style>

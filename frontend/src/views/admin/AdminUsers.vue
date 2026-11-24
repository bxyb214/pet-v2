<template>
  <div class="adm-page">
    <section class="adm-panel">
      <div class="adm-panel-h row">
        <div>
          <h2>邀请码</h2>
          <p>一次性使用，给孩子注册时填写；空库第一个注册账号自动成为管理员。</p>
        </div>
        <div class="adm-actions">
          <n-input-number v-model:value="codeCount" :min="1" :max="20" size="small" style="width: 100px" />
          <n-button size="small" type="primary" :loading="making" @click="makeCodes">生成</n-button>
        </div>
      </div>

      <div v-if="codes.length" class="adm-cards">
        <button
          v-for="c in codes"
          :key="c.code"
          class="adm-code"
          :class="{ used: c.used }"
          :title="c.used ? `已被 ${c.used_by || '他人'} 使用` : '点击复制'"
          :disabled="c.used"
          @click="copyCode(c.code)"
        >
          <b class="adm-mono">{{ c.code }}</b>
          <span>{{ c.used ? `${c.used_by || "他人"} 已用` : "未使用 · 点击复制" }}</span>
        </button>
      </div>
      <p v-else class="adm-empty">还没有邀请码，点右上「生成」建几个。</p>
      <p class="adm-foot">注册路径：登录页 →「用邀请码注册」→ 填码 + 用户名 + 密码。</p>
    </section>

    <section class="adm-panel">
      <div class="adm-panel-h row">
        <div>
          <h2>账号与额度</h2>
          <p>共 {{ users.length }} 个；AI 开关是唯一付费闸门，关闭时付费接口一律 403。</p>
        </div>
        <n-button size="small" secondary :loading="loading" @click="loadUsers">刷新</n-button>
      </div>

      <div v-if="users.length">
        <div v-for="u in users" :key="u.id" class="adm-user">
          <span class="adm-avatar">{{ (u.display_name || u.username || "?").slice(0, 1).toUpperCase() }}</span>
          <span class="adm-uid">
            <b>{{ u.display_name || u.username }}</b>
            <i class="adm-mono">@{{ u.username }}</i>
          </span>
          <i v-if="u.is_admin" class="adm-tag admin">管理员</i>

          <div class="adm-uops">
            <span class="lbl">AI</span>
            <n-switch
              size="small"
              :value="u.ai_enabled"
              :loading="aiBusy === u.id"
              title="付费 AI 总开关：关闭后不调用外部模型"
              @update:value="(v: boolean) => toggleAi(u, v)"
            />
            <span class="adm-use tnum" :class="{ over: u.today_used_milli >= u.daily_budget_milli }">
              今日 {{ fmtYuanShort(u.today_used_milli) }} / {{ fmtYuanShort(u.daily_budget_milli) }}
            </span>
            <i v-if="u.alert_stage >= 2" class="adm-tag danger">已用尽</i>
            <i v-else-if="u.alert_stage === 1" class="adm-tag warn">接近上限</i>
            <n-button size="tiny" secondary @click="openQuota(u)">额度</n-button>
            <n-button v-if="u.alert_stage > 0" size="tiny" quaternary @click="resetAlert(u)">清除告警</n-button>
          </div>
        </div>
      </div>
      <p v-else class="adm-empty">还没有账号。</p>
      <p class="adm-foot">
        口语对所有账号开放，无需单独开通。额度按人可覆盖：留空表示跟随全局默认。日/月预算用尽后服务端返回 429，免费功能（单词、听力、题库）不受影响。
      </p>
    </section>

    <n-modal v-model:show="quotaOpen" preset="card" title="额度设置" class="quota-modal">
      <div v-if="editing" class="quota">
        <p class="quota-u">@{{ editing.username }}</p>
        <label class="adm-field">
          <span class="adm-flabel">每日预算 <i class="adm-opt">元</i></span>
          <n-input-number v-model:value="qDaily" :min="0" :step="1" :precision="2" clearable placeholder="留空 = 全局默认" style="width: 100%" />
          <span class="adm-fhint">当前生效：{{ fmtYuan(editing.daily_budget_milli) }}（今日已用 {{ fmtYuan(editing.today_used_milli) }}）</span>
        </label>
        <label class="adm-field">
          <span class="adm-flabel">每月预算 <i class="adm-opt">元</i></span>
          <n-input-number v-model:value="qMonthly" :min="0" :step="10" :precision="2" clearable placeholder="留空 = 全局默认" style="width: 100%" />
          <span class="adm-fhint">当前生效：{{ fmtYuan(editing.monthly_budget_milli) }}（本月已用 {{ fmtYuan(editing.month_used_milli) }}）</span>
        </label>
        <div class="quota-actions">
          <n-button quaternary @click="quotaOpen = false">取消</n-button>
          <n-button type="primary" :loading="quotaBusy" @click="saveQuota">保存</n-button>
        </div>
      </div>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { NButton, NInputNumber, NModal, NSwitch, useMessage } from "naive-ui";
import { api } from "../../core/api";
import { fmtYuan, fmtYuanShort } from "./format";

type CodeRow = { code: string; used: boolean; used_by: string; used_at: string | null };
type UserRow = {
  id: number;
  username: string;
  display_name: string;
  is_admin: boolean;
  created_at: string | null;
  ai_enabled: boolean;
  ai_daily_budget_milli: number | null;
  ai_monthly_budget_milli: number | null;
  today_used_milli: number;
  month_used_milli: number;
  daily_budget_milli: number;
  monthly_budget_milli: number;
  alert_stage: number;
};

const message = useMessage();
const codes = ref<CodeRow[]>([]);
const users = ref<UserRow[]>([]);
const codeCount = ref(3);
const making = ref(false);
const loading = ref(false);
const aiBusy = ref(0);

async function copyCode(code: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(code);
    message.success("已复制 " + code);
  } catch {
    message.info(code);
  }
}

async function loadCodes(): Promise<void> {
  try {
    codes.value = await api<CodeRow[]>("/admin/codes");
  } catch {
    /* 忽略 */
  }
}

async function loadUsers(): Promise<void> {
  loading.value = true;
  try {
    users.value = await api<UserRow[]>("/admin/users");
  } catch {
    /* 忽略 */
  } finally {
    loading.value = false;
  }
}

function patch(data: UserRow): void {
  const i = users.value.findIndex((u) => u.id === data.id);
  if (i >= 0) users.value[i] = data;
}

async function makeCodes(): Promise<void> {
  making.value = true;
  try {
    const made = await api<string[]>("/admin/codes", {
      method: "POST",
      body: JSON.stringify({ count: codeCount.value }),
    });
    message.success(`已生成 ${made.length} 个：${made.join(" ")}`);
    await loadCodes();
  } catch (e) {
    message.error("生成失败：" + (e as Error).message);
  } finally {
    making.value = false;
  }
}

async function toggleAi(u: UserRow, on: boolean): Promise<void> {
  aiBusy.value = u.id;
  try {
    patch(await api<UserRow>(`/admin/users/${u.id}/ai`, {
      method: "PUT",
      body: JSON.stringify({ enabled: on }),
    }));
    message.success(on ? `已为 ${u.username} 开通 AI` : `已关闭 ${u.username} 的 AI`);
  } catch (e) {
    message.error("修改失败：" + (e as Error).message);
  } finally {
    aiBusy.value = 0;
  }
}

// ---------------------------------------------------------------- 额度弹窗
const quotaOpen = ref(false);
const quotaBusy = ref(false);
const editing = ref<UserRow | null>(null);
const qDaily = ref<number | null>(null);
const qMonthly = ref<number | null>(null);

function openQuota(u: UserRow): void {
  editing.value = u;
  qDaily.value = u.ai_daily_budget_milli === null ? null : u.ai_daily_budget_milli / 1000;
  qMonthly.value = u.ai_monthly_budget_milli === null ? null : u.ai_monthly_budget_milli / 1000;
  quotaOpen.value = true;
}

async function saveQuota(): Promise<void> {
  const u = editing.value;
  if (!u) return;
  quotaBusy.value = true;
  try {
    patch(await api<UserRow>(`/admin/users/${u.id}/ai`, {
      method: "PUT",
      body: JSON.stringify({
        daily_milli: qDaily.value === null ? null : Math.round(qDaily.value * 1000),
        monthly_milli: qMonthly.value === null ? null : Math.round(qMonthly.value * 1000),
      }),
    }));
    quotaOpen.value = false;
    message.success("额度已更新");
  } catch (e) {
    message.error("保存失败：" + (e as Error).message);
  } finally {
    quotaBusy.value = false;
  }
}

async function resetAlert(u: UserRow): Promise<void> {
  try {
    const r = await api<{ removed: number }>(`/admin/users/${u.id}/ai/reset_alert`, { method: "POST" });
    message.success(`已清除 ${r.removed} 条告警`);
    await loadUsers();
  } catch (e) {
    message.error("清除失败：" + (e as Error).message);
  }
}

onMounted(() => {
  void loadCodes();
  void loadUsers();
});
</script>

<style scoped>
.adm-use { font-size: 12px; color: var(--c-text-2); white-space: nowrap; }
.adm-use.over { color: var(--c-danger); font-weight: 700; }
.quota { display: flex; flex-direction: column; gap: 16px; }
.quota-u { margin: 0; font-size: 13px; color: var(--c-text-2); }
.quota-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 4px; }
</style>

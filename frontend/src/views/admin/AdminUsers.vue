<template>
  <div class="adm-page">
    <section class="adm-stats">
      <div class="adm-stat"><b class="tnum">{{ users.length }}</b><span>账号总数</span></div>
      <div class="adm-stat"><b class="tnum">{{ enabledCount }}</b><span>AI 已开通</span></div>
      <div class="adm-stat"><b class="tnum">{{ disabledCount }}</b><span>未开通</span></div>
      <div class="adm-stat"><b class="tnum" :class="{ 'stat-danger': exhaustedCount > 0 }">{{ exhaustedCount }}</b><span>额度告罄</span></div>
    </section>

    <section class="adm-panel">
      <div class="adm-panel-h row">
        <div>
          <h2>账号与 AI 权限</h2>
          <p>AI 权限控制跟读评分与实时对话；关闭后普通功能不受影响。额度是一次性总额，用尽自动暂停付费 AI。</p>
        </div>
        <n-button size="small" secondary :loading="loading" @click="loadUsers">刷新</n-button>
      </div>

      <div class="users-toolbar">
        <n-input
          v-model:value="query" clearable class="users-search"
          placeholder="搜索用户名 / 昵称"
        />
        <div class="users-filters" role="group" aria-label="账号筛选">
          <button
            v-for="f in FILTERS" :key="f.id" type="button"
            class="ufilter" :class="{ on: filter === f.id }"
            :aria-pressed="filter === f.id"
            @click="filter = f.id"
          >{{ f.name }} <i>{{ filterCount(f.id) }}</i></button>
        </div>
      </div>

      <div v-if="filteredUsers.length" class="ucards">
        <AdminUserCard
          v-for="u in filteredUsers" :key="u.id" :u="u"
          :busy="aiBusy === u.id" :reset-busy="resetBusy === u.id"
          @toggle-ai="toggleAi"
          @open-quota="openQuota"
          @import-words="openImport"
          @reset-password="resetPwd"
          @reset-alert="resetAlert"
        />
      </div>
      <p v-else-if="loading" class="adm-empty">加载中…</p>
      <p v-else class="adm-empty">
        {{ users.length ? "没有符合筛选条件的账号。" : "还没有账号。" }}
      </p>

      <p class="adm-foot">
        新注册的普通账号默认未开通 AI，由管理员按需开启。额度按人可覆盖：留空跟随全局默认。
        总额度用尽后付费接口返回 429，调高额度即可继续；单词、阅读、听力、题库等免费功能不受影响。
        管理员账号不受总额度限制。
      </p>
    </section>

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

    <AdminQuotaModal
      v-model:show="quotaOpen" :user="editing" :busy="quotaBusy"
      @save="saveQuota"
    />

    <!-- Excel 批量导入生词 -->
    <n-modal v-model:show="importOpen" preset="card" title="导入生词" class="quota-modal">
      <div v-if="importTarget" class="quota">
        <p class="quota-u">@{{ importTarget.username }}（{{ importTarget.display_name || importTarget.username }}）</p>
        <label class="adm-field">
          <span class="adm-flabel">级别</span>
          <n-radio-group v-model:value="importExam" size="small">
            <n-radio-button value="pet">PET</n-radio-button>
            <n-radio-button value="ket">KET</n-radio-button>
            <n-radio-button value="fce">FCE</n-radio-button>
          </n-radio-group>
          <span class="adm-fhint">词库列填：PET 必默/高频/固搭/同义；KET 核心词/生难词/短语/易混词/同义</span>
        </label>
        <div class="imp-actions">
          <n-button size="small" secondary @click="downloadTemplate">下载 Excel 模板</n-button>
          <input ref="fileInput" type="file" accept=".xlsx" hidden @change="onImportFile" />
          <n-button size="small" type="primary" :loading="importBusy" :disabled="importBusy" @click="pickFile">
            {{ importBusy ? "导入中…" : "选择文件上传" }}
          </n-button>
        </div>
        <p class="adm-fhint">模板列：单词 / 词库 / 词性 / 释义 / 英文例句 / 中文翻译。已存在的词自动跳过；词库与级别不匹配的行会提示。</p>
        <n-alert v-if="importResult" type="success" size="small" closable>
          成功导入 {{ importResult.added }} 个词{{ importResult.skipped.length ? `；跳过 ${importResult.skipped.length} 行` : "" }}
          <n-ul v-if="importResult.skipped.length" class="imp-skips">
            <n-li v-for="s in importResult.skipped" :key="s">{{ s }}</n-li>
          </n-ul>
        </n-alert>
        <n-alert v-if="importErr" type="error" size="small" closable>{{ importErr }}</n-alert>
      </div>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import {
  NAlert, NButton, NInput, NInputNumber, NLi, NModal, NRadioButton, NRadioGroup,
  NUl, useMessage,
} from "naive-ui";
import { api, downloadFile } from "../../core/api";
import AdminQuotaModal from "./AdminQuotaModal.vue";
import AdminUserCard from "./AdminUserCard.vue";
import type { AdminUserRow } from "./types";

type CodeRow = { code: string; used: boolean; used_by: string; used_at: string | null };
type FilterId = "all" | "on" | "off" | "exhausted";
const FILTERS: { id: FilterId; name: string }[] = [
  { id: "all", name: "全部" },
  { id: "on", name: "已开通" },
  { id: "off", name: "未开通" },
  { id: "exhausted", name: "额度告罄" },
];

const message = useMessage();
const codes = ref<CodeRow[]>([]);
const users = ref<AdminUserRow[]>([]);
const codeCount = ref(3);
const making = ref(false);
const loading = ref(false);
const aiBusy = ref(0);
const query = ref("");
const filter = ref<FilterId>("all");

const enabledCount = computed(() => users.value.filter((u) => u.ai_enabled).length);
const disabledCount = computed(() => users.value.length - enabledCount.value);
const exhaustedCount = computed(
  () => users.value.filter((u) => !u.unlimited && u.ai_enabled && u.remaining_milli <= 0).length,
);

const filteredUsers = computed(() => {
  const needle = query.value.trim().toLowerCase();
  return users.value.filter((u) => {
    if (needle) {
      const hay = `${u.username} ${u.display_name}`.toLowerCase();
      if (!hay.includes(needle)) return false;
    }
    if (filter.value === "on") return u.ai_enabled;
    if (filter.value === "off") return !u.ai_enabled;
    if (filter.value === "exhausted") {
      return !u.unlimited && u.ai_enabled && u.remaining_milli <= 0;
    }
    return true;
  });
});

function filterCount(id: FilterId): number {
  if (id === "on") return enabledCount.value;
  if (id === "off") return disabledCount.value;
  if (id === "exhausted") return exhaustedCount.value;
  return users.value.length;
}

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
    users.value = await api<AdminUserRow[]>("/admin/users");
  } catch {
    /* 忽略 */
  } finally {
    loading.value = false;
  }
}

function patch(data: AdminUserRow): void {
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

async function toggleAi(u: AdminUserRow, on: boolean): Promise<void> {
  aiBusy.value = u.id;
  try {
    patch(await api<AdminUserRow>(`/admin/users/${u.id}/ai`, {
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
const editing = ref<AdminUserRow | null>(null);

function openQuota(u: AdminUserRow): void {
  editing.value = u;
  quotaOpen.value = true;
}

async function saveQuota(creditMilli: number | null): Promise<void> {
  const u = editing.value;
  if (!u) return;
  quotaBusy.value = true;
  try {
    patch(await api<AdminUserRow>(`/admin/users/${u.id}/ai`, {
      method: "PUT",
      body: JSON.stringify({ credit_milli: creditMilli }),
    }));
    quotaOpen.value = false;
    message.success(creditMilli == null ? "已恢复全局默认额度" : "额度已更新");
  } catch (e) {
    message.error("保存失败：" + (e as Error).message);
  } finally {
    quotaBusy.value = false;
  }
}

async function resetAlert(u: AdminUserRow): Promise<void> {
  try {
    const r = await api<{ removed: number }>(`/admin/users/${u.id}/ai/reset_alert`, { method: "POST" });
    message.success(`已清除 ${r.removed} 条告警`);
    await loadUsers();
  } catch (e) {
    message.error("清除失败：" + (e as Error).message);
  }
}

// ---- 重置密码
const resetBusy = ref(0);

async function resetPwd(u: AdminUserRow): Promise<void> {
  resetBusy.value = u.id;
  try {
    const r = await api<{ username: string; temp_password: string }>(
      `/admin/users/${u.id}/reset_password`,
      { method: "POST" },
    );
    try {
      await navigator.clipboard.writeText(r.temp_password);
      message.success(`已为 @${r.username} 重置密码：${r.temp_password}（已复制，请发给用户）`);
    } catch {
      message.warning(`已为 @${r.username} 重置密码：${r.temp_password}（请手动记下，仅显示一次）`);
    }
  } catch (e) {
    message.error("重置失败：" + (e as Error).message);
  } finally {
    resetBusy.value = 0;
  }
}

onMounted(() => {
  void loadCodes();
  void loadUsers();
});

// ---- Excel 导入生词
const importOpen = ref(false);
const importTarget = ref<AdminUserRow | null>(null);
const importExam = ref<"pet" | "ket" | "fce">("pet");
const importBusy = ref(false);
const importErr = ref("");
const importResult = ref<{ added: number; skipped: string[]; skipped_more: number } | null>(null);

function openImport(u: AdminUserRow): void {
  importTarget.value = u;
  importExam.value = "pet";
  importErr.value = "";
  importResult.value = null;
  importOpen.value = true;
}

function downloadTemplate(): void {
  void downloadFile("/admin/words/import/template", "生词导入模板.xlsx");
}

/** 隐藏 file input 用 JS 触发：label 包 n-button 时点击不转发（button 是交互元素） */
const fileInput = ref<HTMLInputElement | null>(null);
function pickFile(): void {
  fileInput.value?.click();
}

async function onImportFile(ev: Event): Promise<void> {
  const input = ev.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = ""; // 允许重选同一个文件
  const u = importTarget.value;
  if (!file || !u) return;
  importBusy.value = true;
  importErr.value = "";
  try {
    const form = new FormData();
    form.append("file", file);
    // 附件上传（multipart）：api() 走 JSON，这里用裸 fetch 但仍带鉴权头
    const token = localStorage.getItem("pet_access") ?? "";
    const res = await fetch(`/api/v1/admin/users/${u.id}/words/import?exam=${importExam.value}`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    });
    const body = await res.json().catch(() => null);
    if (!res.ok) throw new Error(body?.detail ?? `导入失败 (${res.status})`);
    importResult.value = body;
    message.success(`已导入 ${body.added} 个词到 @${u.username}`);
  } catch (e) {
    importErr.value = e instanceof Error ? e.message : "导入失败";
  } finally {
    importBusy.value = false;
  }
}
</script>

<style scoped>
.stat-danger { color: var(--c-danger); }
.users-toolbar { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 14px; }
.users-search { flex: 1 1 200px; max-width: 300px; }
.users-filters { display: flex; gap: 6px; flex-wrap: wrap; }
.ufilter {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 5px 11px; min-height: 32px; border-radius: 999px;
  border: 1px solid var(--c-line); background: var(--c-surface);
  color: var(--c-text-2); font: inherit; font-size: 12.5px; font-weight: 600;
  cursor: pointer; white-space: nowrap;
}
.ufilter:hover { border-color: var(--c-primary); color: var(--c-text); }
.ufilter.on { background: var(--c-primary-strong); border-color: var(--c-primary-strong); color: #fff; }
.ufilter i { font-style: normal; font-size: 11px; opacity: 0.65; font-variant-numeric: tabular-nums; }
.ucards { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 12px; }
.quota { display: flex; flex-direction: column; gap: 16px; }
.quota-u { margin: 0; font-size: 13px; color: var(--c-text-2); }
.imp-actions { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.imp-skips { max-height: 160px; overflow: auto; margin: 8px 0 0; }
@media (max-width: 640px) {
  .users-search { max-width: none; flex-basis: 100%; }
  .ucards { grid-template-columns: 1fr; }
}
</style>

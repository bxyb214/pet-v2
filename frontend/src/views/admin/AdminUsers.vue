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
          <p>共 {{ users.length }} 个；AI 开关是付费总闸门，关闭时付费接口一律 403；总额度用尽后自动暂停付费 AI。</p>
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
            <span class="adm-use tnum" :class="{ over: !u.unlimited && u.credit_used_milli >= u.credit_budget_milli }">
              {{ u.unlimited ? "管理员 · 不限额度" : `总额 ${fmtYuanShort(u.credit_used_milli)} / ${fmtYuanShort(u.credit_budget_milli)}` }}
            </span>
            <i v-if="!u.unlimited && u.alert_stage >= 2" class="adm-tag danger">已用尽</i>
            <i v-else-if="!u.unlimited && u.alert_stage === 1" class="adm-tag warn">接近上限</i>
            <n-button size="tiny" secondary @click="openQuota(u)">额度</n-button>
            <n-button size="tiny" secondary @click="openImport(u)">导入生词</n-button>
            <n-button size="tiny" secondary :loading="resetBusy === u.id" @click="resetPwd(u)">重置密码</n-button>
            <n-button v-if="u.alert_stage > 0" size="tiny" quaternary @click="resetAlert(u)">清除告警</n-button>
          </div>
        </div>
      </div>
      <p v-else class="adm-empty">还没有账号。</p>
      <p class="adm-foot">
        口语对所有账号开放，普通账号默认获赠一次性总额度（默认 0.5 元）。额度按人可覆盖：留空表示跟随全局默认。
        总额度用尽后服务端返回 429，调高额度即可继续；免费功能（单词、听力、题库）不受影响。管理员账号不受总额度限制。
      </p>
    </section>

    <n-modal v-model:show="quotaOpen" preset="card" title="额度设置" class="quota-modal">
      <div v-if="editing" class="quota">
        <p class="quota-u">@{{ editing.username }}</p>
        <label class="adm-field">
          <span class="adm-flabel">一次性总额度 <i class="adm-opt">元</i></span>
          <n-input-number v-model:value="qCredit" :min="0" :step="0.5" :precision="2" clearable placeholder="留空 = 全局默认" style="width: 100%" />
          <span class="adm-fhint">
            当前生效：{{ fmtYuan(editing.credit_budget_milli) }}（累计已用 {{ fmtYuan(editing.credit_used_milli) }}）
            <template v-if="editing.unlimited"> · 管理员账号不受总额度限制</template>
          </span>
        </label>
        <p class="adm-fhint">额度用完即暂停付费 AI；调高此值即可继续使用，无需按日/月恢复。</p>
        <div class="quota-actions">
          <n-button quaternary @click="quotaOpen = false">取消</n-button>
          <n-button type="primary" :loading="quotaBusy" @click="saveQuota">保存</n-button>
        </div>
      </div>
    </n-modal>

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
import { onMounted, ref } from "vue";
import { NAlert, NButton, NInputNumber, NLi, NModal, NRadioButton, NRadioGroup, NSwitch, NUl, useMessage } from "naive-ui";
import { downloadFile } from "../../core/api";
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
  unlimited: boolean;
  ai_credit_milli: number | null;
  credit_used_milli: number;
  credit_budget_milli: number;
  remaining_milli: number;
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
const qCredit = ref<number | null>(null);

function openQuota(u: UserRow): void {
  editing.value = u;
  qCredit.value = u.ai_credit_milli === null ? null : u.ai_credit_milli / 1000;
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
        credit_milli: qCredit.value === null ? null : Math.round(qCredit.value * 1000),
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

// ---- 重置密码
const resetBusy = ref(0);

async function resetPwd(u: UserRow): Promise<void> {
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
const importTarget = ref<UserRow | null>(null);
const importExam = ref<"pet" | "ket" | "fce">("pet");
const importBusy = ref(false);
const importErr = ref("");
const importResult = ref<{ added: number; skipped: string[]; skipped_more: number } | null>(null);

function openImport(u: UserRow): void {
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
.adm-use { font-size: 12px; color: var(--c-text-2); white-space: nowrap; }
.adm-use.over { color: var(--c-danger); font-weight: 700; }
.quota { display: flex; flex-direction: column; gap: 16px; }
.quota-u { margin: 0; font-size: 13px; color: var(--c-text-2); }
.quota-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 4px; }
.imp-actions { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.imp-skips { max-height: 160px; overflow: auto; margin: 8px 0 0; }
</style>

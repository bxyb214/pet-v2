<template>
  <div class="page">
    <n-card size="small">
      <template #header>⚙️ 管理后台</template>
      <template #header-extra>
        <n-button type="primary" :loading="saving" @click="save">保存全部配置</n-button>
      </template>

      <n-tabs type="line" animated v-model:value="tab">
        <!-- ---------- LLM ---------- -->
        <n-tab-pane name="llm" tab="AI 加词补全">
          <n-form label-placement="top" size="medium">
            <n-grid :cols="2" :x-gap="16">
              <n-gi span="2">
                <n-form-item label="API Key（保存后只显示尾 4 位）">
                  <n-input v-model:value="llm.api_key" type="password" show-password-on="click" placeholder="sk-…" />
                </n-form-item>
              </n-gi>
              <n-gi>
                <n-form-item label="接口地址">
                  <n-input v-model:value="llm.base_url" placeholder="https://dashscope.aliyuncs.com/compatible-mode/v1" />
                </n-form-item>
              </n-gi>
              <n-gi>
                <n-form-item label="模型">
                  <n-input v-model:value="llm.model" placeholder="qwen3.8-flash" />
                </n-form-item>
              </n-gi>
            </n-grid>
          </n-form>
        </n-tab-pane>

        <!-- ---------- Qwen Realtime ---------- -->
        <n-tab-pane name="qwen" tab="口语对话（Qwen Realtime）">
          <n-form label-placement="top" size="medium">
            <n-grid :cols="2" :x-gap="16">
              <n-gi span="2">
                <n-form-item label="API Key">
                  <n-input v-model:value="qwen.api_key" type="password" show-password-on="click" placeholder="sk-…" />
                </n-form-item>
              </n-gi>
              <n-gi span="2">
                <n-form-item label="业务空间 ID（workspace，qwen3.8 系列必填）">
                  <n-input v-model:value="qwen.workspace" placeholder="ws-xxxx" />
                </n-form-item>
              </n-gi>
              <n-gi>
                <n-form-item label="对话模型">
                  <n-input v-model:value="qwen.model" placeholder="qwen3.8-omni-flash-realtime" />
                </n-form-item>
              </n-gi>
              <n-gi>
                <n-form-item label="对话音色">
                  <n-input v-model:value="qwen.voice" placeholder="Tina" />
                </n-form-item>
              </n-gi>
              <n-gi>
                <n-form-item label="跟读模型（可选，留空用对话模型）">
                  <n-input v-model:value="qwen.shadow_model" placeholder="留空则同对话模型" />
                </n-form-item>
              </n-gi>
              <n-gi>
                <n-form-item label="跟读音色（可选）">
                  <n-input v-model:value="qwen.voice_shadow" placeholder="longanqian_v3.1" />
                </n-form-item>
              </n-gi>
              <n-gi>
                <n-form-item label="TTS 模型">
                  <n-input v-model:value="qwen.tts_model" placeholder="qwen3-tts-flash" />
                </n-form-item>
              </n-gi>
              <n-gi>
                <n-form-item label="TTS 音色">
                  <n-input v-model:value="qwen.tts_voice" placeholder="Ryan" />
                </n-form-item>
              </n-gi>
            </n-grid>
          </n-form>
        </n-tab-pane>

        <!-- ---------- SOE ---------- -->
        <n-tab-pane name="soe" tab="发音评测（腾讯 SOE）">
          <n-alert type="info" :bordered="false" style="margin-bottom: 14px">
            跟读页的「精准发音评分」按钮；配置后自动启用。需在
            <a href="https://console.cloud.tencent.com/soenew" target="_blank" rel="noopener">SOE 控制台</a>
            开通「口语评测（新版）」并购买资源包。
          </n-alert>
          <n-form label-placement="top" size="medium">
            <n-grid :cols="2" :x-gap="16">
              <n-gi>
                <n-form-item label="AppID">
                  <n-input v-model:value="soe.appid" placeholder="1300000000" />
                </n-form-item>
              </n-gi>
              <n-gi>
                <n-form-item label="引擎">
                  <n-input v-model:value="soe.engine" placeholder="16k_en" />
                </n-form-item>
              </n-gi>
              <n-gi>
                <n-form-item label="SecretId">
                  <n-input v-model:value="soe.secret_id" type="password" show-password-on="click" placeholder="AKID…" />
                </n-form-item>
              </n-gi>
              <n-gi>
                <n-form-item label="SecretKey（不出服务端）">
                  <n-input v-model:value="soe.secret_key" type="password" show-password-on="click" placeholder="签名用密钥" />
                </n-form-item>
              </n-gi>
              <n-gi span="2">
                <n-form-item label="评分苛刻指数（1.0 适合儿童）">
                  <n-input-number v-model:value="soe.coeff" :min="1" :max="4" :step="0.1" style="width: 160px" />
                </n-form-item>
              </n-gi>
            </n-grid>
          </n-form>
        </n-tab-pane>

        <!-- ---------- 账号与邀请码 ---------- -->
        <n-tab-pane name="accounts" tab="账号与邀请码">
          <div class="uhead">
            <n-input-number v-model:value="codeCount" :min="1" :max="20" size="small" style="width: 110px" />
            <n-button size="small" type="primary" :loading="making" @click="makeCodes">生成邀请码</n-button>
            <span class="tot">未使用 <b>{{ unusedCount }}</b> 个</span>
          </div>
          <n-data-table size="small" :columns="codeCols" :data="codes" :bordered="false" />
          <p class="hint">
            把邀请码给孩子：打开登录页 → 「用邀请码注册」→ 填邀请码 + 用户名 + 密码即可。邀请码一次性使用。
          </p>

          <div class="uhead" style="margin-top: 22px"><span>已有账号</span></div>
          <n-data-table size="small" :columns="userCols" :data="users" :bordered="false" />
          <p v-if="!users.length" class="hint">还没有账号。</p>
        </n-tab-pane>

        <!-- ---------- 用量 ---------- -->
        <n-tab-pane name="usage" tab="AI 用量（只记录）">
          <div class="uhead">
            <n-date-picker v-model:value="dayTs" type="date" size="small" style="width: 150px" :clearable="false" @update:value="loadUsage" />
            <span class="tot">当日预估 <b>{{ fmtYuan(dayTotal) }}</b></span>
          </div>
          <n-data-table size="small" :columns="usageCols" :data="dayUsers" :bordered="false" />
          <p v-if="!dayUsers.length" class="hint">当天还没有用量记录。</p>

          <div class="uhead" style="margin-top: 22px">
            <n-date-picker v-model:value="monthTs" type="month" size="small" style="width: 150px" :clearable="false" @update:value="loadMonth" />
            <span class="tot">本月预估 <b>{{ fmtYuan(monthTotal) }}</b></span>
          </div>
          <n-data-table size="small" :columns="usageCols" :data="monthUsers" :bordered="false" />
          <p v-if="!monthUsers.length" class="hint">本月还没有用量记录。</p>
        </n-tab-pane>
      </n-tabs>

      <template #footer>
        <span class="status">{{ status }}</span>
      </template>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from "vue";
import { NButton, NCard, NForm, NFormItem, NGi, NGrid, NInput, NInputNumber, NAlert, NTabPane, NTabs, NDatePicker, NDataTable, useMessage, type DataTableColumns } from "naive-ui";
import { api } from "../core/api";

type CfgMap = Record<string, string>;

const tab = ref("llm");
const llm = reactive({ api_key: "", base_url: "", model: "" });
const qwen = reactive({
  base: "", workspace: "", api_key: "", model: "", voice: "",
  shadow_model: "", voice_shadow: "", tts_model: "", tts_voice: "",
});
const soe = reactive<{ appid: string; secret_id: string; secret_key: string; engine: string; coeff: number }>({
  appid: "", secret_id: "", secret_key: "", engine: "", coeff: 1.0,
});
const status = ref("");
const saving = ref(false);
const message = useMessage();

// ---------- 用量 ----------
type UsageRow = {
  user_id: number; username: string; rt_seconds: number; soe_calls: number;
  llm_in_tok: number; llm_out_tok: number; est_cost_milli: number;
};
const dayUsers = ref<UsageRow[]>([]);
const monthUsers = ref<UsageRow[]>([]);
const dayTotal = ref(0);
const monthTotal = ref(0);
const dayTs = ref(Date.now());
const monthTs = ref(Date.now());

function fmtYuan(milli: number): string {
  return (milli / 1000).toFixed(2) + " 元";
}
const dayStr = (): string => new Date(dayTs.value).toISOString().slice(0, 10);
const monthStr = (): string => new Date(monthTs.value).toISOString().slice(0, 7);

const usageCols: DataTableColumns<UsageRow> = [
  { title: "用户", key: "username" },
  { title: "对话分钟", key: "rt_seconds", width: 110, render: (r) => Math.round(r.rt_seconds / 60) },
  { title: "评测次数", key: "soe_calls", width: 100 },
  {
    title: "预估费用",
    key: "est_cost_milli",
    width: 120,
    render: (r) => h("b", { style: "color:var(--c-primary,#16a34a)" }, fmtYuan(r.est_cost_milli)),
  },
];

async function loadUsage(): Promise<void> {
  try {
    const r = await api<{ total_cost_milli: number; users: UsageRow[] }>(`/admin/usage?day=${dayStr()}`);
    dayUsers.value = r.users ?? [];
    dayTotal.value = r.total_cost_milli ?? 0;
  } catch { /* 忽略 */ }
}
async function loadMonth(): Promise<void> {
  try {
    const r = await api<{ total_cost_milli: number; users: UsageRow[] }>(`/admin/usage/summary?month=${monthStr()}`);
    monthUsers.value = r.users ?? [];
    monthTotal.value = r.total_cost_milli ?? 0;
  } catch { /* 忽略 */ }
}

// ---------- 账号与邀请码 ----------
type CodeRow = { code: string; used: boolean; used_by: string; used_at: string | null };
type UserRow = { id: number; username: string; display_name: string; is_admin: boolean; perms: string };

const codes = ref<CodeRow[]>([]);
const users = ref<UserRow[]>([]);
const codeCount = ref(3);
const making = ref(false);
const unusedCount = computed(() => codes.value.filter((c) => !c.used).length);

const codeCols: DataTableColumns<CodeRow> = [
  {
    title: "邀请码",
    key: "code",
    render: (r) =>
      h(
        "b",
        {
          style: `font-family:ui-monospace,Consolas,monospace;letter-spacing:.5px;cursor:pointer;color:${
            r.used ? "#9aa8a0" : "var(--c-primary,#16a34a)"
          }`,
          title: "点击复制",
          onClick: () => copyCode(r.code),
        },
        r.code,
      ),
  },
  {
    title: "状态",
    key: "used",
    width: 150,
    render: (r) =>
      r.used
        ? h("span", { style: "color:#9aa8a0" }, `已被 ${r.used_by || "他人"} 使用`)
        : h("span", { style: "color:var(--c-primary,#16a34a)" }, "未使用"),
  },
];

const userCols: DataTableColumns<UserRow> = [
  { title: "用户名", key: "username" },
  { title: "昵称", key: "display_name" },
  { title: "管理员", key: "is_admin", width: 90, render: (r) => (r.is_admin ? "是" : "—") },
  { title: "权限", key: "perms", render: (r) => r.perms || "—" },
];

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
  } catch { /* 忽略 */ }
}
async function loadUsers(): Promise<void> {
  try {
    users.value = await api<UserRow[]>("/admin/users");
  } catch { /* 忽略 */ }
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

// ---------- 配置加载 / 保存 ----------
function pick(d: Record<string, string>, k: string): string {
  return String(d[k] ?? "");
}

onMounted(async () => {
  try {
    const cfg: CfgMap = await api<CfgMap>("/admin/cfg");
    llm.api_key = pick(cfg, "llm.api_key");
    llm.base_url = pick(cfg, "llm.base_url");
    llm.model = pick(cfg, "llm.model");
    if (cfg["speak.qwen"]) {
      const q = JSON.parse(cfg["speak.qwen"]) as Record<string, string>;
      for (const k of Object.keys(qwen)) (qwen as Record<string, string>)[k] = String(q[k] ?? "");
    }
    if (cfg["speak.soe"]) {
      const s = JSON.parse(cfg["speak.soe"]) as Record<string, string | number>;
      for (const k of Object.keys(soe)) {
        if (s[k] !== undefined) (soe as Record<string, string | number>)[k] = s[k];
      }
    }
    status.value = "";
  } catch (e) {
    status.value = "加载失败：" + (e as Error).message;
  }
  await loadUsage();
  await loadMonth();
  await loadCodes();
  await loadUsers();
});

async function save(): Promise<void> {
  saving.value = true;
  status.value = "";
  try {
    await api("/admin/cfg", { method: "PUT", body: JSON.stringify({ key: "llm.api_key", value: llm.api_key }) });
    await api("/admin/cfg", { method: "PUT", body: JSON.stringify({ key: "llm.base_url", value: llm.base_url }) });
    await api("/admin/cfg", { method: "PUT", body: JSON.stringify({ key: "llm.model", value: llm.model }) });
    await api("/admin/cfg", { method: "PUT", body: JSON.stringify({ key: "speak.qwen", value: JSON.stringify(qwen) }) });
    await api("/admin/cfg", { method: "PUT", body: JSON.stringify({ key: "speak.soe", value: JSON.stringify(soe) }) });
    status.value = "刚刚已保存";
    message.success("配置已保存");
  } catch (e) {
    status.value = "保存失败";
    message.error("保存失败：" + (e as Error).message);
  } finally {
    saving.value = false;
  }
}
</script>

<style scoped>
.page { width: 100%; }
.uhead { display: flex; align-items: center; gap: 14px; margin: 10px 0 8px; flex-wrap: wrap; }
.tot { margin-left: auto; color: var(--c-text-2, #6b7f74); font-size: 13px; }
.tot b { color: var(--c-primary, #16a34a); font-size: 15px; }
.hint { font-size: 12px; color: var(--c-text-2, #6b7f74); margin: 6px 0; }
.status { color: var(--c-text-2, #6b7f74); font-size: 13px; }
</style>

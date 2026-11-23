<template>
  <div class="page admin">
    <header class="pagehead">
      <div class="ph-l">
        <p class="eyebrow">Admin Console</p>
        <h1>管理后台</h1>
        <p class="sub">AI 能力配置 · 邀请码与账号 · 每天的用量账本</p>
      </div>
      <div class="ph-r">
        <span v-if="isConfigTab" class="savechip" :class="saveTone">{{ saveText }}</span>
        <n-button v-if="isConfigTab" type="primary" :loading="saving" @click="save">保存配置</n-button>
      </div>
    </header>

    <!-- 概览：四件事，一眼看完 -->
    <section class="stats">
      <div v-for="s in stats" :key="s.label" class="stat">
        <span class="sv tnum">{{ s.value }}</span>
        <span class="sl">{{ s.label }}</span>
      </div>
    </section>

    <nav class="ptabs" role="tablist">
      <button
        v-for="t in TABS"
        :key="t.id"
        class="ptab"
        role="tab"
        :aria-selected="tab === t.id"
        :class="{ on: tab === t.id }"
        @click="tab = t.id"
      >{{ t.name }}</button>
    </nav>

    <!-- ================= AI 加词 ================= -->
    <section v-if="tab === 'llm'" class="panel">
      <div class="panel-h">
        <h2>AI 加词补全</h2>
        <p>手动加生词时，用这套模型补词性、释义与例句</p>
      </div>

      <div class="notice">
        <span class="ni">i</span>
        <p>
          需在
          <a href="https://bailian.console.aliyun.com/cn-beijing/model/settings/api-key" target="_blank" rel="noopener">阿里云百炼 · API-KEY</a>
          创建 Key，并开通通义千问文本模型；Key 只存在服务端配置表里，保存后仅回显尾 4 位。
        </p>
      </div>
      <div class="grid2">
        <label class="field span2">
          <span class="flabel">API Key</span>
          <n-input v-model:value="llm.api_key" type="password" show-password-on="click" placeholder="sk-…" />
          <span class="fhint">保存后只回显尾 4 位，明文不出服务端</span>
        </label>
        <label class="field">
          <span class="flabel">接口地址</span>
          <n-input v-model:value="llm.base_url" placeholder="https://dashscope.aliyuncs.com/compatible-mode/v1" />
        </label>
        <label class="field">
          <span class="flabel">模型</span>
          <n-input v-model:value="llm.model" placeholder="qwen3.8-flash" />
        </label>
      </div>
    </section>

    <!-- ================= 口语对话 ================= -->
    <section v-if="tab === 'qwen'" class="panel">
      <div class="panel-h">
        <h2>口语对话 · Qwen Realtime</h2>
        <p>浏览器直连，服务端只负责签发临时凭证，Key 不下发到前端</p>
      </div>

      <div class="notice">
        <span class="ni">i</span>
        <p>
          需在
          <a href="https://bailian.console.aliyun.com/cn-beijing/model/settings/api-key" target="_blank" rel="noopener">阿里云百炼 · API-KEY</a>
          创建 Key（可与「AI 加词」共用），并在控制台开通实时语音模型；
          Key 只存在服务端配置表里，保存后仅回显尾 4 位。
        </p>
      </div>

      <h3 class="grp">连接</h3>
      <div class="grid2">
        <label class="field span2">
          <span class="flabel">API Key</span>
          <n-input v-model:value="qwen.api_key" type="password" show-password-on="click" placeholder="sk-…" />
        </label>
        <label class="field span2">
          <span class="flabel">业务空间 ID <i class="req">必填</i></span>
          <n-input v-model:value="qwen.workspace" placeholder="ws-xxxx" />
          <span class="fhint">qwen3.8 系列必须带 workspace；Key 也要属于该空间并已开通对话模型，否则报 Workspace endpoint access denied</span>
        </label>
      </div>

      <h3 class="grp">对话</h3>
      <div class="grid2">
        <label class="field">
          <span class="flabel">对话模型</span>
          <n-input v-model:value="qwen.model" placeholder="qwen3.8-omni-flash-realtime" />
        </label>
        <label class="field">
          <span class="flabel">对话音色</span>
          <n-input v-model:value="qwen.voice" placeholder="Tina" />
        </label>
      </div>

      <h3 class="grp">跟读与朗读</h3>
      <div class="grid2">
        <label class="field">
          <span class="flabel">跟读模型 <i class="opt">可选</i></span>
          <n-input v-model:value="qwen.shadow_model" placeholder="留空则同对话模型" />
        </label>
        <label class="field">
          <span class="flabel">跟读音色 <i class="opt">可选</i></span>
          <n-input v-model:value="qwen.voice_shadow" placeholder="longanqian_v3.1" />
        </label>
        <label class="field">
          <span class="flabel">TTS 模型</span>
          <n-input v-model:value="qwen.tts_model" placeholder="qwen3-tts-flash" />
        </label>
        <label class="field">
          <span class="flabel">TTS 音色</span>
          <n-input v-model:value="qwen.tts_voice" placeholder="Ryan" />
        </label>
      </div>
    </section>

    <!-- ================= SOE ================= -->
    <section v-if="tab === 'soe'" class="panel">
      <div class="panel-h">
        <h2>发音评测 · 腾讯 SOE</h2>
        <p>跟读页的「跟读评分」走这套接口，配好即启用</p>
      </div>

      <div class="notice">
        <span class="ni">i</span>
        <p>
          需在
          <a href="https://console.cloud.tencent.com/soenew" target="_blank" rel="noopener">SOE 控制台</a>
          开通「口语评测（新版）」并购买资源包；SecretKey 只存在服务端配置表里。
        </p>
      </div>

      <div class="grid2">
        <label class="field">
          <span class="flabel">AppID</span>
          <n-input v-model:value="soe.appid" placeholder="1300000000" />
        </label>
        <label class="field">
          <span class="flabel">引擎</span>
          <n-input v-model:value="soe.engine" placeholder="16k_en" />
        </label>
        <label class="field">
          <span class="flabel">SecretId</span>
          <n-input v-model:value="soe.secret_id" type="password" show-password-on="click" placeholder="AKID…" />
        </label>
        <label class="field">
          <span class="flabel">SecretKey</span>
          <n-input v-model:value="soe.secret_key" type="password" show-password-on="click" placeholder="签名用密钥" />
        </label>
        <label class="field">
          <span class="flabel">苛刻指数</span>
          <n-input-number v-model:value="soe.coeff" :min="1" :max="4" :step="0.1" style="width: 100%" />
          <span class="fhint">1.0 最宽松，适合儿童；4.0 最严格</span>
        </label>
      </div>
    </section>

    <!-- ================= 账号与邀请码 ================= -->
    <template v-if="tab === 'accounts'">
      <section class="panel">
        <div class="panel-h row">
          <div>
            <h2>邀请码</h2>
            <p>一次性使用，给孩子注册时填写</p>
          </div>
          <div class="pact">
            <n-input-number v-model:value="codeCount" :min="1" :max="20" size="small" style="width: 100px" />
            <n-button size="small" type="primary" :loading="making" @click="makeCodes">生成</n-button>
          </div>
        </div>

        <div v-if="codes.length" class="codes">
          <button
            v-for="c in codes"
            :key="c.code"
            class="code"
            :class="{ used: c.used }"
            :title="c.used ? `已被 ${c.used_by || '他人'} 使用` : '点击复制'"
            :disabled="c.used"
            @click="copyCode(c.code)"
          >
            <span class="code-t mono">{{ c.code }}</span>
            <span class="code-s">{{ c.used ? `${c.used_by || "他人"} 已用` : "未使用 · 点击复制" }}</span>
          </button>
        </div>
        <p v-else class="empty">还没有邀请码，点右上「生成」建几个。</p>

        <p class="foot-hint">孩子的操作：登录页 →「用邀请码注册」→ 填码 + 用户名 + 密码，建好直接进入。</p>
      </section>

      <section class="panel">
        <div class="panel-h row">
          <div>
            <h2>账号</h2>
            <p>共 {{ users.length }} 个，权限由开通状态决定</p>
          </div>
        </div>

        <div v-if="users.length" class="users">
          <div v-for="u in users" :key="u.id" class="urow">
            <span class="avatar">{{ (u.display_name || u.username || "?").slice(0, 1).toUpperCase() }}</span>
            <span class="uid">
              <b>{{ u.display_name || u.username }}</b>
              <i class="mono">@{{ u.username }}</i>
            </span>
            <span class="uright">
              <i v-if="u.is_admin" class="tg admin">管理员</i>
              <span class="uperm">
                <span class="pl">口语</span>
                <n-switch
                  size="small"
                  :value="u.perms.includes('speak')"
                  :loading="permBusy === u.id"
                  :title="u.is_admin ? '管理员默认开通，也可以关闭自己的口语权限' : '开通后可进入跟读 / 对话 / 造句'"
                  @update:value="(v: boolean) => toggleSpeak(u, v)"
                />
              </span>
            </span>
          </div>
        </div>
        <p v-else class="empty">还没有账号。</p>
        <p class="foot-hint">
          口语按账号开通：打开后该账号即可进入「跟读 / 对话 / 造句」，关闭后相关接口一律拒绝。管理员默认开通，也可关闭自己的口语权限。
        </p>
      </section>
    </template>

    <!-- ================= 用量 ================= -->
    <template v-if="tab === 'usage'">
      <section class="panel">
        <div class="panel-h row">
          <div>
            <h2>当日用量</h2>
            <p>只记账、不限流；费用按配置里的单价估算</p>
          </div>
          <div class="pact">
            <n-date-picker v-model:value="dayTs" type="date" size="small" style="width: 140px" :clearable="false" @update:value="loadUsage" />
            <span class="total">合计 <b>{{ fmtYuan(dayTotal) }}</b></span>
          </div>
        </div>
        <div v-if="dayUsers.length" class="tbl">
          <div class="thead">
            <span>用户</span><span>对话</span><span>评测</span><span>预估</span>
          </div>
          <div v-for="r in dayUsers" :key="r.user_id" class="trow">
            <span class="tname">{{ r.username }}</span>
            <span class="tnum">{{ Math.round(r.rt_seconds / 60) }} 分</span>
            <span class="tnum">{{ r.soe_calls }} 次</span>
            <span class="tcost tnum">{{ fmtYuan(r.est_cost_milli) }}</span>
          </div>
        </div>
        <p v-else class="empty">当天还没有用量记录。</p>
      </section>

      <section class="panel">
        <div class="panel-h row">
          <div>
            <h2>本月用量</h2>
            <p>按月汇总，用于对账</p>
          </div>
          <div class="pact">
            <n-date-picker v-model:value="monthTs" type="month" size="small" style="width: 140px" :clearable="false" @update:value="loadMonth" />
            <span class="total">合计 <b>{{ fmtYuan(monthTotal) }}</b></span>
          </div>
        </div>
        <div v-if="monthUsers.length" class="tbl">
          <div class="thead">
            <span>用户</span><span>对话</span><span>评测</span><span>预估</span>
          </div>
          <div v-for="r in monthUsers" :key="r.user_id" class="trow">
            <span class="tname">{{ r.username }}</span>
            <span class="tnum">{{ Math.round(r.rt_seconds / 60) }} 分</span>
            <span class="tnum">{{ r.soe_calls }} 次</span>
            <span class="tcost tnum">{{ fmtYuan(r.est_cost_milli) }}</span>
          </div>
        </div>
        <p v-else class="empty">本月还没有用量记录。</p>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { NButton, NDatePicker, NInput, NInputNumber, NSwitch, useMessage } from "naive-ui";
import { api } from "../core/api";

type CfgMap = Record<string, string>;

const TABS = [
  { id: "llm", name: "AI 加词" },
  { id: "qwen", name: "口语对话" },
  { id: "soe", name: "发音评测" },
  { id: "accounts", name: "账号与邀请码" },
  { id: "usage", name: "用量" },
];
const tab = ref("llm");
const isConfigTab = computed(() => ["llm", "qwen", "soe"].includes(tab.value));

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

/** 保存状态的三种语气：未改 / 已存 / 失败 */
const saveTone = computed(() => (status.value.startsWith("保存失败") ? "bad" : status.value ? "ok" : ""));
const saveText = computed(() => status.value || "改动后记得保存");

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

const stats = computed(() => [
  { label: "账号", value: String(users.value.length) },
  { label: "可用邀请码", value: String(unusedCount.value) },
  { label: "今日费用", value: fmtYuan(dayTotal.value) },
  { label: "本月费用", value: fmtYuan(monthTotal.value) },
]);

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
const permBusy = ref(0);

/** 开通 / 关闭某个账号的口语权限（管理员恒开通，开关不可操作） */
async function toggleSpeak(u: UserRow, on: boolean): Promise<void> {
  permBusy.value = u.id;
  try {
    const r = await api<UserRow>(`/admin/users/${u.id}/perms`, {
      method: "PUT",
      body: JSON.stringify({ speak: on }),
    });
    u.perms = r.perms;
    message.success(on ? `已为 ${u.username} 开通口语` : `已关闭 ${u.username} 的口语`);
  } catch (e) {
    message.error("修改失败：" + (e as Error).message);
  } finally {
    permBusy.value = 0;
  }
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
    status.value = "保存失败：" + (e as Error).message;
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

/* ---------- 页头 ---------- */
.pagehead {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}
.eyebrow {
  margin: 0 0 4px;
  font-size: 11px; font-weight: 700; letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--c-primary-strong);
}
h1 { margin: 0 0 4px; font-size: 22px; font-weight: 800; letter-spacing: 0.2px; color: var(--c-text); }
.sub { margin: 0; font-size: 12.5px; color: var(--c-text-2); }
.ph-r { display: flex; align-items: center; gap: 10px; flex: none; }
.savechip {
  font-size: 12px; color: var(--c-text-3);
  padding: 5px 10px; border-radius: var(--r-pill);
  background: #f4f8f6;
}
.savechip.ok { color: var(--c-primary-strong); background: var(--c-primary-soft); }
.savechip.bad { color: #b42318; background: var(--c-danger-soft); }

/* ---------- 概览 ---------- */
.stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 16px;
}
.stat {
  display: flex; flex-direction: column; gap: 2px;
  padding: 12px 14px;
  background: var(--c-card);
  border: 1px solid var(--c-line);
  border-radius: var(--r-card);
}
.sv { font-size: 20px; font-weight: 800; color: var(--c-text); letter-spacing: -0.01em; }
.sl { font-size: 12px; color: var(--c-text-2); }

/* ---------- 分段页签 ---------- */
.ptabs {
  display: flex; gap: 2px; flex-wrap: nowrap;
  padding: 4px;
  background: var(--c-card);
  border: 1px solid var(--c-line);
  border-radius: var(--r-pill);
  margin-bottom: 14px;
  overflow-x: auto; scrollbar-width: none;
}
.ptabs::-webkit-scrollbar { display: none; }
.ptab {
  flex: none;
  padding: 8px 16px; min-height: 38px;
  border: 0; border-radius: var(--r-pill);
  background: none; color: var(--c-text-2);
  font-size: 13.5px; font-weight: 600; font-family: inherit;
  cursor: pointer; white-space: nowrap;
  transition: background var(--dur-2) var(--ease-out), color var(--dur-2) var(--ease-out);
}
.ptab:hover { color: var(--c-text); background: var(--c-mint-bg); }
.ptab.on { background: var(--c-primary-strong); color: #fff; }

/* ---------- 面板 ---------- */
.panel {
  background: var(--c-card);
  border: 1px solid var(--c-line);
  border-radius: var(--r-card);
  box-shadow: var(--shadow-1);
  padding: 18px 20px 20px;
  margin-bottom: 14px;
}
.panel-h { margin-bottom: 16px; }
.panel-h.row {
  display: flex; align-items: flex-start; justify-content: space-between;
  gap: 12px; flex-wrap: wrap;
}
.panel-h h2 { margin: 0 0 4px; font-size: 15px; font-weight: 800; color: var(--c-text); }
.panel-h p { margin: 0; font-size: 12.5px; color: var(--c-text-2); line-height: 1.6; }
.pact { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.total { font-size: 12.5px; color: var(--c-text-2); }
.total b { color: var(--c-primary-strong); font-size: 14px; font-weight: 800; }

.grp {
  margin: 20px 0 10px;
  font-size: 11.5px; font-weight: 700; letter-spacing: 0.08em;
  color: var(--c-text-3);
}
.grp:first-of-type { margin-top: 0; }

/* ---------- 字段 ---------- */
.grid2 { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px 16px; }
.span2 { grid-column: span 2; }
.field { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.flabel {
  display: flex; align-items: center; gap: 6px;
  font-size: 12.5px; font-weight: 700; color: var(--c-text-2);
}
.req, .opt {
  font-style: normal; font-size: 10.5px; font-weight: 700;
  padding: 1px 6px; border-radius: var(--r-pill);
}
.req { background: #fdf2e7; color: #9c6c17; }
.opt { background: #f1f5f3; color: var(--c-text-3); }
.fhint { font-size: 11.5px; color: var(--c-text-3); line-height: 1.5; }

.notice {
  display: flex; gap: 10px; align-items: flex-start;
  padding: 12px 14px; margin-bottom: 16px;
  border-radius: var(--r-sm);
  background: #f4f9ff; border: 1px solid #dbe8fb;
}
.ni {
  flex: none; width: 18px; height: 18px; border-radius: 50%;
  background: #2563eb; color: #fff;
  font-size: 11px; font-weight: 800; font-style: italic;
  display: inline-flex; align-items: center; justify-content: center;
  margin-top: 1px;
}
.notice p { margin: 0; font-size: 12.5px; line-height: 1.7; color: #29496f; }
.notice a { color: #1d4ed8; font-weight: 600; }

/* ---------- 邀请码 ---------- */
.codes {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  gap: 10px;
}
.code {
  display: flex; flex-direction: column; gap: 3px;
  padding: 11px 13px;
  border: 1px dashed #b9e3ca;
  border-radius: var(--r-btn);
  background: #f7fdf9;
  cursor: pointer; text-align: left;
  transition: border-color var(--dur-2) var(--ease-out), background var(--dur-2) var(--ease-out);
}
.code:hover { border-color: var(--c-primary); background: #f0fbf5; }
.code.used { border-style: solid; border-color: var(--c-line); background: #fafcfb; cursor: default; }
.code-t { font-size: 14px; font-weight: 700; color: var(--c-primary-strong); letter-spacing: 0.4px; }
.code.used .code-t { color: var(--c-text-3); text-decoration: line-through; }
.code-s { font-size: 11.5px; color: var(--c-text-3); }

/* ---------- 账号 ---------- */
.users { display: flex; flex-direction: column; }
.urow {
  display: flex; align-items: center; gap: 12px;
  padding: 11px 2px;
  border-bottom: 1px solid var(--c-line);
}
.urow:last-child { border-bottom: none; }
.avatar {
  flex: none;
  width: 34px; height: 34px; border-radius: 50%;
  background: var(--c-primary-soft); color: var(--c-primary-strong);
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: 800;
}
.uid { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
.uid b { font-size: 14px; font-weight: 700; color: var(--c-text); }
.uid i { font-style: normal; font-size: 11.5px; color: var(--c-text-3); }
.uright { margin-left: auto; display: flex; align-items: center; gap: 10px; flex: none; }
.uperm { display: flex; align-items: center; gap: 6px; }
.uperm .pl { font-size: 12px; color: var(--c-text-2); }
.tg {
  font-style: normal; font-size: 11px; font-weight: 700;
  padding: 2px 8px; border-radius: var(--r-pill);
  white-space: nowrap;
}
.tg.admin { background: #eef4ff; color: #2f5fd0; }

/* ---------- 用量表 ---------- */
.tbl { display: flex; flex-direction: column; }
.thead, .trow {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) repeat(3, minmax(0, 1fr));
  gap: 10px; align-items: center;
}
.thead {
  padding: 0 2px 8px;
  font-size: 11.5px; font-weight: 700; color: var(--c-text-3);
  border-bottom: 1px solid var(--c-line);
}
.trow { padding: 10px 2px; border-bottom: 1px solid #f2f7f4; font-size: 13px; color: var(--c-text-2); }
.trow:last-child { border-bottom: none; }
.tname { color: var(--c-text); font-weight: 600; overflow: hidden; text-overflow: ellipsis; }
.tcost { color: var(--c-primary-strong); font-weight: 700; }
.thead span:not(:first-child), .trow span:not(.tname) { text-align: right; }

.empty { margin: 0; padding: 18px 2px; font-size: 12.5px; color: var(--c-text-3); }
.foot-hint {
  margin: 14px 0 0; padding-top: 12px;
  border-top: 1px dashed var(--c-line);
  font-size: 12px; color: var(--c-text-3); line-height: 1.7;
}

.mono { font-family: ui-monospace, "SFMono-Regular", Consolas, monospace; }

@media (max-width: 767px) {
  .pagehead { flex-direction: column; align-items: stretch; }
  .ph-r { justify-content: space-between; }
  .stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .grid2 { grid-template-columns: 1fr; }
  .span2 { grid-column: span 1; }
  .panel { padding: 14px 12px 16px; }
  .thead, .trow { grid-template-columns: minmax(0, 1.4fr) 1fr 1fr 1fr; font-size: 12.5px; }
}
</style>

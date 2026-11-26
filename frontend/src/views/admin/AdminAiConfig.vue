<template>
  <div class="adm-page">
    <div class="adm-notice">
      <span class="adm-ni">i</span>
      <p>密钥只存服务端配置表，保存后只回显尾 4 位；每组独立保存，改哪组存哪组。</p>
    </div>

    <nav class="adm-tabs small" role="tablist">
      <button
        v-for="g in GROUPS"
        :key="g.id"
        class="adm-tab"
        :class="{ on: group === g.id }"
        role="tab"
        :aria-selected="group === g.id"
        @click="group = g.id"
      >{{ g.name }}</button>
    </nav>

    <AiLlmForm
      v-if="group === 'llm'"
      v-model:llm="llm"
      :test="tests.llm"
      :save-msg="saveMsg.llm || ''"
      :busy="saving === 'llm'"
      :test-busy="testBusy === 'llm'"
      @save="saveGroup('llm')"
      @test="runTest('llm')"
    />
    <AiRealtimeForm
      v-else-if="group === 'realtime'"
      v-model:qwen="qwen"
      :test="tests.realtime"
      :save-msg="saveMsg.realtime || ''"
      :busy="saving === 'realtime'"
      :test-busy="testBusy === 'realtime'"
      @save="saveGroup('realtime')"
      @test="runTest('realtime')"
    />
    <AiTtsForm
      v-else-if="group === 'tts'"
      v-model:qwen="qwen"
      :test="tests.tts"
      :save-msg="saveMsg.tts || ''"
      :busy="saving === 'tts'"
      :test-busy="testBusy === 'tts'"
      @save="saveGroup('tts')"
      @test="runTest('tts')"
    />
    <AiSoeForm
      v-else-if="group === 'soe'"
      v-model:soe="soe"
      :test="tests.soe"
      :save-msg="saveMsg.soe || ''"
      :busy="saving === 'soe'"
      :test-busy="testBusy === 'soe'"
      @save="saveGroup('soe')"
      @test="runTest('soe')"
    />
    <AiPriceForm
      v-else-if="group === 'price'"
      v-model:prices="prices"
      v-model:credit="creditYuan"
      v-model:alert="alertPct"
      v-model:hard="hardStop"
      :save-msg="saveMsg.price || ''"
      :busy="saving === 'price'"
      @save="saveGroup('price')"
    />
    <AiCacheForm
      v-else
      v-model:max="cacheMax"
      :cache="cache"
      :save-msg="saveMsg.cache || ''"
      :busy="saving === 'cache'"
      @save="saveGroup('cache')"
      @clear="clearCache"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { useDialog, useMessage } from "naive-ui";
import { api } from "../../core/api";
import AiLlmForm from "./AiLlmForm.vue";
import AiRealtimeForm from "./AiRealtimeForm.vue";
import AiTtsForm from "./AiTtsForm.vue";
import AiSoeForm from "./AiSoeForm.vue";
import AiPriceForm from "./AiPriceForm.vue";
import AiCacheForm from "./AiCacheForm.vue";
import type { CacheStats, LlmCfg, QwenCfg, SoeCfg, TestResult } from "./types";

const GROUPS = [
  { id: "llm", name: "AI 加词" },
  { id: "realtime", name: "实时对话" },
  { id: "tts", name: "语音合成" },
  { id: "soe", name: "发音评测" },
  { id: "price", name: "单价与默认额度" },
  { id: "cache", name: "TTS 缓存" },
];

const group = ref("llm");
const saving = ref("");
const testBusy = ref("");
const saveMsg = reactive<Record<string, string>>({});
const tests = reactive<Record<string, TestResult | null>>({});
const message = useMessage();
const dialog = useDialog();

const llm = reactive<LlmCfg>({ api_key: "", base_url: "", model: "" });
const qwen = reactive<QwenCfg>({
  base: "", workspace: "", api_key: "", model: "", fallback_model: "", voice: "",
  shadow_model: "", voice_shadow: "", vad: "", mcp: false,
  tts_model: "", tts_voice: "",
});
const soe = reactive<SoeCfg>({
  appid: "", secret_id: "", secret_key: "", engine: "", coeff: 1.0,
});

const prices = reactive<Record<string, number>>({});
const creditYuan = ref<number | null>(0.5);
const alertPct = ref<number | null>(80);
const hardStop = ref(true);
const cacheMax = ref<number | null>(512);
const cache = reactive<CacheStats>({ files: 0, bytes: 0, max_mb: 512 });

function qwenJson(): string {
  return JSON.stringify({ ...qwen, mcp: qwen.mcp ? "1" : "" });
}

async function putCfg(key: string, value: string): Promise<void> {
  await api("/admin/cfg", { method: "PUT", body: JSON.stringify({ key, value }) });
}

async function saveGroup(g: string): Promise<void> {
  saving.value = g;
  saveMsg[g] = "";
  try {
    if (g === "llm") {
      await Promise.all([
        putCfg("llm.api_key", llm.api_key),
        putCfg("llm.base_url", llm.base_url),
        putCfg("llm.model", llm.model),
      ]);
    } else if (g === "realtime" || g === "tts") {
      await putCfg("speak.qwen", qwenJson());
    } else if (g === "soe") {
      await putCfg("speak.soe", JSON.stringify(soe));
    } else if (g === "price") {
      const clean: Record<string, number> = {};
      for (const [k, v] of Object.entries(prices)) clean[k] = Math.max(0, Number(v) || 0);
      await api("/admin/ai/prices", {
        method: "PUT",
        body: JSON.stringify({
          prices: clean,
          budget: {
            credit_milli: Math.round((creditYuan.value ?? 0) * 1000),
            alert_ratio: (alertPct.value ?? 80) / 100,
            hard_stop: hardStop.value,
          },
        }),
      });
    } else if (g === "cache") {
      const r = await api<{ tts_cache: { max_mb: number } }>("/admin/ai/prices", {
        method: "PUT",
        body: JSON.stringify({ tts_cache: { max_mb: Math.round(cacheMax.value ?? 512) } }),
      });
      cache.max_mb = r.tts_cache.max_mb;
      cacheMax.value = r.tts_cache.max_mb;
    }
    saveMsg[g] = "刚刚已保存";
    message.success("配置已保存");
  } catch (e) {
    saveMsg[g] = "保存失败";
    message.error("保存失败：" + (e as Error).message);
  } finally {
    saving.value = "";
  }
}

async function runTest(kind: string): Promise<void> {
  testBusy.value = kind;
  tests[kind] = null;
  try {
    tests[kind] = await api<TestResult>(`/admin/test/${kind}`, { method: "POST" });
  } catch (e) {
    tests[kind] = { ok: false, detail: (e as Error).message };
  } finally {
    testBusy.value = "";
  }
}

async function loadCache(): Promise<void> {
  try {
    const r = await api<Partial<CacheStats>>("/admin/tts_cache");
    if (typeof r.files === "number" && typeof r.bytes === "number" && typeof r.max_mb === "number") {
      Object.assign(cache, r);
      cacheMax.value = r.max_mb;
    }
  } catch {
    /* 忽略 */
  }
}

function clearCache(): void {
  dialog.warning({
    title: "清空 TTS 缓存",
    content: "删除后再次播放会重新合成并产生费用，确定清空？",
    positiveText: "清空",
    negativeText: "取消",
    async onPositiveClick() {
      try {
        const r = await api<{ removed: number } & CacheStats>("/admin/tts_cache", { method: "DELETE" });
        Object.assign(cache, r);
        message.success(`已清空 ${r.removed} 个文件`);
      } catch (e) {
        message.error("清空失败：" + (e as Error).message);
      }
    },
  });
}

onMounted(async () => {
  try {
    const raw = await api<Record<string, string>>("/admin/cfg");
    llm.api_key = raw["llm.api_key"] ?? "";
    llm.base_url = raw["llm.base_url"] ?? "";
    llm.model = raw["llm.model"] ?? "";
    if (raw["speak.qwen"]) {
      const q = JSON.parse(raw["speak.qwen"]) as Record<string, unknown>;
      for (const k of Object.keys(qwen)) {
        if (k === "mcp") {
          qwen.mcp = ["1", "true", "yes", "on"].includes(String(q.mcp ?? "").toLowerCase());
        } else if (q[k] !== undefined && q[k] !== null) {
          (qwen as unknown as Record<string, string>)[k] = String(q[k]);
        }
      }
    }
    if (raw["speak.soe"]) {
      const s = JSON.parse(raw["speak.soe"]) as Record<string, unknown>;
      for (const k of Object.keys(soe)) {
        if (s[k] !== undefined && s[k] !== null) {
          (soe as unknown as Record<string, string | number>)[k] = s[k] as string | number;
        }
      }
    }
  } catch {
    /* 配置读取失败时保留空表单 */
  }
  try {
    const p = await api<{
      prices: Record<string, number>;
      budget: { credit_milli: number; alert_ratio: number; hard_stop: boolean };
      tts_cache: { max_mb: number };
    }>("/admin/ai/prices");
    Object.assign(prices, p.prices ?? {});
    if (p.budget) {
      creditYuan.value = p.budget.credit_milli / 1000;
      alertPct.value = Math.round(p.budget.alert_ratio * 100);
      hardStop.value = p.budget.hard_stop;
    }
    if (p.tts_cache) {
      cache.max_mb = p.tts_cache.max_mb;
      cacheMax.value = p.tts_cache.max_mb;
    }
  } catch {
    /* 忽略 */
  }
  await loadCache();
});
</script>

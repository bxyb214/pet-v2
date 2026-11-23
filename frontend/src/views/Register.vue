<template>
  <AuthShell
    :eyebrow="isFirst ? 'Setup' : 'Join'"
    :title="isFirst ? '先建一个管理员账号，再开始学' : '输入邀请码，给自己建个账号'"
    :points="[
      '邀请码找小淏要，一次性使用',
      '学习记录跟账号走，换设备不丢',
      '昵称只用来在页面上称呼你',
    ]"
    foot="邀请码区分大小写？不区分，会自动转大写"
  >
    <header class="head">
      <h2>{{ isFirst ? "第一次使用" : "创建账号" }}</h2>
      <p>{{ isFirst ? "这是本机的第一个账号，将拥有管理权限" : "" }}</p>
    </header>

    <n-form label-placement="top" size="large" @submit.prevent="submit">
      <n-form-item label="邀请码" class="field">
        <n-input
          v-model:value="invite"
          placeholder="PET-8F3K-2M7Q"
          :input-props="{ autocapitalize: 'characters', spellcheck: 'false' }"
          @keyup.enter="submit"
        />
      </n-form-item>
      <n-form-item label="用户名" class="field">
        <n-input v-model:value="username" placeholder="登录用，英文或数字" @keyup.enter="submit" />
      </n-form-item>
      <n-form-item label="密码" class="field">
        <n-input
          v-model:value="password"
          type="password"
          show-password-on="click"
          placeholder="至少 6 位"
          autocomplete="new-password"
          @keyup.enter="submit"
        />
      </n-form-item>
      <n-form-item label="昵称（可不填）" class="field">
        <n-input v-model:value="nickname" placeholder="页面上显示的名字" @keyup.enter="submit" />
      </n-form-item>

      <p v-if="error" class="err" role="alert">
        <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round">
          <circle cx="12" cy="12" r="9" />
          <path d="M12 7.5v5.5M12 16.4v.1" />
        </svg>
        {{ error }}
      </p>

      <n-button type="primary" size="large" block :loading="busy" attr-type="button" @click="submit">
        {{ isFirst ? "创建管理员并登录" : "创建并登录" }}
      </n-button>
    </n-form>

    <template #alt>
      已经有账号？
      <router-link to="/login">去登录</router-link>
    </template>
  </AuthShell>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { NButton, NForm, NFormItem, NInput } from "naive-ui";
import { api } from "../core/api";
import { useAuthStore } from "../stores/auth";
import AuthShell from "../components/AuthShell.vue";

const auth = useAuthStore();
const router = useRouter();

const invite = ref("");
const username = ref("");
const password = ref("");
const nickname = ref("");
const error = ref("");
const busy = ref(false);
const isFirst = ref(false);   // 库里还没有任何账号 → 走 claim 建管理员

onMounted(async () => {
  try {
    const s = await api<{ initialized: boolean; allow_claim: boolean }>("/auth/setup");
    isFirst.value = !s.initialized && s.allow_claim;
  } catch {
    // 拿不到就按普通注册处理，提交时的报错信息足够定位
  }
});

async function submit(): Promise<void> {
  if (busy.value) return;
  const code = invite.value.trim().toUpperCase();
  if (!code || !username.value.trim() || !password.value) {
    error.value = "邀请码、用户名、密码都要填";
    return;
  }
  if (password.value.length < 6) {
    error.value = "密码至少 6 位";
    return;
  }
  error.value = "";
  busy.value = true;
  try {
    await api(isFirst.value ? "/auth/claim" : "/auth/register", {
      method: "POST",
      body: JSON.stringify({
        invite_code: code,
        username: username.value.trim(),
        password: password.value,
        display_name: nickname.value.trim() || username.value.trim(),
      }),
    });
    // 建号成功后直接登录，顺便建立同步引擎
    await auth.login(username.value.trim(), password.value);
    await router.push("/");
  } catch (e) {
    error.value = e instanceof Error ? e.message : "创建失败";
  } finally {
    busy.value = false;
  }
}
</script>

<style scoped>
.head { margin-bottom: 18px; }
.head h2 {
  margin: 0 0 6px;
  font-size: 19px;
  font-weight: 800;
  letter-spacing: 0.2px;
  color: var(--c-text);
}
.head p { margin: 0; font-size: 12.5px; color: var(--c-text-2); line-height: 1.6; }

.field { margin-bottom: 12px; }
:deep(.n-form-item-label) {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: var(--c-text-2);
  padding-bottom: 4px;
}
:deep(.n-button) { margin-top: 6px; }

.err {
  display: flex;
  align-items: center;
  gap: 7px;
  margin: 0 0 12px;
  padding: 9px 11px;
  border-radius: var(--r-sm);
  background: var(--c-danger-soft);
  border: 1px solid #f6d5d5;
  color: #b42318;
  font-size: 13px;
  line-height: 1.5;
  animation: err-in var(--dur-2) var(--ease-out) both;
}
.err svg { flex: none; }

@keyframes err-in {
  from { opacity: 0; transform: translateY(-3px); }
  to { opacity: 1; transform: none; }
}
</style>

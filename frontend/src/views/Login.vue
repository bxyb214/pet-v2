<template>
  <AuthShell
    eyebrow="Welcome back"
    title="把每天的 20 分钟，变成看得见的进步"
    :points="[
      '3,164 个 PET / KET 词条，按天切好',
      '错题按 1 · 2 · 4 · 7 · 15 天自动回来',
      '单词、阅读、听力、口语，一站练完',
    ]"
    foot="PET · KET · FCE 陆续开通"
  >
    <header class="head">
      <h2>登录</h2>
    </header>

    <n-form :show-label="false" size="large" @submit.prevent="submit">
      <n-form-item class="field">
        <n-input v-model:value="username" placeholder="用户名" autocomplete="username" @keyup.enter="submit" />
      </n-form-item>
      <n-form-item class="field">
        <n-input
          v-model:value="password"
          type="password"
          show-password-on="click"
          placeholder="密码"
          autocomplete="current-password"
          @keyup.enter="submit"
        />
      </n-form-item>

      <p v-if="error" class="err" role="alert">
        <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round">
          <circle cx="12" cy="12" r="9" />
          <path d="M12 7.5v5.5M12 16.4v.1" />
        </svg>
        {{ error }}
      </p>

      <n-button type="primary" size="large" block :loading="busy" attr-type="button" @click="submit">
        登录
      </n-button>
    </n-form>

    <template #alt>
      没有账号？
      <router-link to="/register">用邀请码注册</router-link>
    </template>
  </AuthShell>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { NButton, NForm, NFormItem, NInput } from "naive-ui";
import { useAuthStore } from "../stores/auth";
import AuthShell from "../components/AuthShell.vue";

const auth = useAuthStore();
const router = useRouter();
const username = ref("");
const password = ref("");
const error = ref("");
const busy = ref(false);

async function submit(): Promise<void> {
  if (busy.value) return;
  if (!username.value.trim() || !password.value) {
    error.value = "请输入用户名和密码";
    return;
  }
  error.value = "";
  busy.value = true;
  try {
    await auth.login(username.value, password.value);
    await router.push("/");
  } catch (e) {
    error.value = e instanceof Error ? e.message : "登录失败";
  } finally {
    busy.value = false;
  }
}
</script>

<style scoped>
.head { margin-bottom: 22px; }
.head h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 800;
  letter-spacing: 0.2px;
  color: var(--c-text);
}

.field { margin-bottom: 14px; }

.err {
  display: flex;
  align-items: center;
  gap: 7px;
  margin: 0 0 14px;
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

<template>
  <main class="login-wrap">
    <div class="login-card">
      <div class="brand">
        <div class="logo">🌱</div>
        <h1>PET 备考小助手</h1>
        <p class="sub">每天进步一点点，从一棵小苗长成大树</p>
      </div>

      <n-form :show-label="false" size="large" @submit.prevent="submit">
        <n-form-item :show-feedback="error.length > 0" :validation-status="error ? 'error' : undefined" :feedback="error">
          <n-input v-model:value="username" placeholder="用户名" autocomplete="username" @keyup.enter="submit" />
        </n-form-item>
        <n-form-item :show-feedback="false">
          <n-input
            v-model:value="password"
            type="password"
            show-password-on="click"
            placeholder="密码"
            autocomplete="current-password"
            @keyup.enter="submit"
          />
        </n-form-item>
        <n-button type="primary" size="large" block :loading="busy" attr-type="button" @click="submit">
          登录
        </n-button>
      </n-form>

      <p class="hint">没有账号？向老师要一个邀请码注册</p>
    </div>
  </main>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { NButton, NForm, NFormItem, NInput } from "naive-ui";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const router = useRouter();
const username = ref("");
const password = ref("");
const error = ref("");
const busy = ref(false);

async function submit(): Promise<void> {
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
.login-wrap {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: linear-gradient(160deg, #eaf7ef 0%, #f6fbf7 45%, #ffffff 100%);
}
.login-card {
  width: 100%;
  max-width: 380px;
  background: #fff;
  border-radius: 20px;
  box-shadow: 0 12px 40px rgba(22, 101, 52, 0.12);
  padding: 36px 32px 28px;
}
.brand { text-align: center; margin-bottom: 24px; }
.logo {
  width: 64px; height: 64px; margin: 0 auto 12px;
  border-radius: 20px;
  background: linear-gradient(135deg, #e7f6ec, #d1efdd);
  display: flex; align-items: center; justify-content: center;
  font-size: 32px;
}
h1 { font-size: 22px; font-weight: 800; color: var(--c-text, #1f3d2b); margin: 0 0 6px; }
.sub { font-size: 13px; color: var(--c-text-2, #6b7f74); margin: 0; }
.hint { text-align: center; font-size: 12px; color: var(--c-text-2, #6b7f74); margin: 16px 0 0; }
</style>

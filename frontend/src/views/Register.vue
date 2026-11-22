<template>
  <main class="login-wrap">
    <div class="login-card">
      <div class="brand">
        <div class="logo">🌱</div>
        <h1>{{ isFirst ? "第一次使用" : "创建账号" }}</h1>
        <p class="sub">
          {{ isFirst ? "用老师给的邀请码建立管理员账号" : "输入老师给的邀请码，给自己建个账号" }}
        </p>
      </div>

      <n-form label-placement="top" size="large" @submit.prevent="submit">
        <n-form-item label="邀请码" :show-feedback="false">
          <n-input
            v-model:value="invite"
            placeholder="邀请码，例如 PET-8F3K-2M7Q"
            :input-props="{ autocapitalize: 'characters' }"
            @keyup.enter="submit"
          />
        </n-form-item>
        <n-form-item label="用户名" :show-feedback="false">
          <n-input v-model:value="username" placeholder="用户名（登录用，英文/数字）" @keyup.enter="submit" />
        </n-form-item>
        <n-form-item label="密码" :show-feedback="!!error" :validation-status="error ? 'error' : undefined" :feedback="error">
          <n-input
            v-model:value="password"
            type="password"
            show-password-on="click"
            placeholder="密码，至少 6 位"
            @keyup.enter="submit"
          />
        </n-form-item>
        <n-form-item label="昵称" :show-feedback="false">
          <n-input v-model:value="nickname" placeholder="昵称（可不填，显示在页头）" @keyup.enter="submit" />
        </n-form-item>

        <n-button type="primary" size="large" block :loading="busy" attr-type="button" @click="submit">
          {{ isFirst ? "创建管理员并登录" : "创建并登录" }}
        </n-button>
      </n-form>

      <p class="hint">
        已经有账号？
        <router-link to="/login">去登录</router-link>
      </p>
    </div>
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { NButton, NForm, NFormItem, NInput } from "naive-ui";
import { api } from "../core/api";
import { useAuthStore } from "../stores/auth";

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
  max-width: 420px;
  background: #fff;
  border-radius: 20px;
  box-shadow: 0 12px 40px rgba(22, 101, 52, 0.12);
  padding: 32px 32px 24px;
}
.brand { text-align: center; margin-bottom: 20px; }
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
.hint a { color: #1f7a4d; text-decoration: none; font-weight: 600; }
:deep(.n-form-item) { margin-bottom: 16px; }
:deep(.n-form-item-label) {
  font-size: 12px;
  color: var(--c-text-2, #6b7f74);
  padding-bottom: 4px;
  font-weight: 600;
}
:deep(.n-button) { margin-top: 4px; }
</style>

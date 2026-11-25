<template>
  <div class="page">
    <!-- 个人资料头卡 -->
    <section class="profile card">
      <div class="avatar" aria-hidden="true">{{ initial }}</div>
      <div class="p-main">
        <div class="p-name">
          <b>{{ auth.displayName || auth.username }}</b>
          <i v-if="auth.isAdmin" class="p-tag">管理员</i>
        </div>
        <span class="p-user">@{{ auth.username }}</span>
      </div>
    </section>

    <!-- 基本资料 -->
    <n-card size="small" class="card">
      <div class="sect-head">
        <h2>基本资料</h2>
        <span class="sect-hint">昵称会显示在页面右上角与学习记录里</span>
      </div>
      <label class="field">
        <span class="flabel">昵称</span>
        <div class="field-row">
          <n-input
            v-model:value="newName"
            maxlength="64"
            show-count
            placeholder="1-64 个字符"
            :disabled="nameBusy"
            @keydown.enter="saveName"
          />
          <n-button type="primary" secondary :loading="nameBusy" :disabled="!nameChanged" @click="saveName">
            保存
          </n-button>
        </div>
      </label>
      <div class="info-row"><span class="flabel">用户名</span><span class="fvalue">{{ auth.username }}</span></div>
      <div class="info-row"><span class="flabel">可用板块</span><span class="fvalue perms">{{ permText }}</span></div>
    </n-card>

    <!-- 修改密码 -->
    <n-card size="small" class="card">
      <div class="sect-head">
        <h2>修改密码</h2>
        <span class="sect-hint">修改后请记住新密码；其他设备需重新登录</span>
      </div>
      <label class="field">
        <span class="flabel">旧密码</span>
        <n-input
          v-model:value="oldPwd"
          type="password"
          show-password-on="click"
          placeholder="输入当前密码"
          :disabled="pwdBusy"
        />
      </label>
      <label class="field">
        <span class="flabel">新密码</span>
        <n-input
          v-model:value="newPwd"
          type="password"
          show-password-on="click"
          placeholder="至少 6 位"
          :disabled="pwdBusy"
        />
        <span class="fhint">至少 6 位，建议字母 + 数字组合</span>
      </label>
      <label class="field">
        <span class="flabel">确认新密码</span>
        <n-input
          v-model:value="newPwd2"
          type="password"
          show-password-on="click"
          placeholder="再输入一遍新密码"
          :disabled="pwdBusy"
        />
        <span v-if="newPwd2 && newPwd !== newPwd2" class="fhint err">两次输入的密码不一致</span>
      </label>
      <div class="pwd-actions">
        <n-button
          type="primary"
          :loading="pwdBusy"
          :disabled="!canSubmitPwd"
          @click="savePwd"
        >
          确认修改
        </n-button>
      </div>
    </n-card>

    <!-- 退出登录 -->
    <n-card size="small" class="card">
      <div class="logout-row">
        <div>
          <b>退出登录</b>
          <span class="sect-hint">本地学习记录会保留，下次登录继续</span>
        </div>
        <n-button tertiary type="error" @click="confirmLogout">退出</n-button>
      </div>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { NButton, NCard, NInput, useDialog, useMessage } from "naive-ui";
import { api } from "../core/api";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const router = useRouter();
const message = useMessage();
const dialog = useDialog();

const permText = "词汇 · 阅读 · 听力 · 口语";

const initial = computed(() => {
  const name = auth.displayName || auth.username || "学";
  const ch = Array.from(name)[0] ?? "学";
  return /^[a-z]$/.test(ch) ? ch.toUpperCase() : ch;
});

/* 昵称 */
const newName = ref(auth.displayName || auth.username);
const nameBusy = ref(false);
const nameChanged = computed(() => newName.value.trim() !== (auth.displayName || auth.username));

async function saveName(): Promise<void> {
  if (!nameChanged.value || nameBusy.value) return;
  nameBusy.value = true;
  try {
    const me = await api<{ display_name: string }>("/auth/me", {
      method: "PUT",
      body: JSON.stringify({ display_name: newName.value.trim() }),
    });
    auth.displayName = me.display_name;
    message.success("昵称已更新");
  } catch (err) {
    message.error("修改失败：" + (err as Error).message);
  } finally {
    nameBusy.value = false;
  }
}

/* 密码 */
const oldPwd = ref("");
const newPwd = ref("");
const newPwd2 = ref("");
const pwdBusy = ref(false);
const canSubmitPwd = computed(
  () => oldPwd.value.length > 0 && newPwd.value.length >= 6 && newPwd.value === newPwd2.value,
);

async function savePwd(): Promise<void> {
  if (!canSubmitPwd.value || pwdBusy.value) return;
  pwdBusy.value = true;
  try {
    await api("/auth/me/password", {
      method: "POST",
      body: JSON.stringify({ old_password: oldPwd.value, new_password: newPwd.value }),
    });
    oldPwd.value = "";
    newPwd.value = "";
    newPwd2.value = "";
    message.success("密码已修改，请记住新密码");
  } catch (err) {
    message.error("修改失败：" + (err as Error).message);
  } finally {
    pwdBusy.value = false;
  }
}

/* 退出 */
function confirmLogout(): void {
  dialog.warning({
    title: "退出登录",
    content: "确定要退出当前账号吗？",
    positiveText: "退出",
    negativeText: "取消",
    onPositiveClick: () => {
      auth.logout();
      void router.push("/login");
    },
  });
}
</script>

<style scoped>
.page { width: 100%; }
.card { margin-bottom: 16px; }

/* 个人资料头卡 */
.profile {
  display: flex; align-items: center; gap: 18px;
  padding: 22px 24px; margin-bottom: 16px;
  background: linear-gradient(135deg, var(--c-primary-soft) 0%, var(--c-surface) 62%);
  border: 1px solid var(--c-line); border-radius: var(--r-card);
  box-shadow: var(--shadow-card);
}
.avatar {
  width: 64px; height: 64px; flex: none;
  display: flex; align-items: center; justify-content: center;
  border-radius: 50%;
  background: linear-gradient(135deg, #22c55e, #16a34a);
  color: #fff; font-size: 28px; font-weight: 800;
  box-shadow: 0 4px 12px rgba(22, 163, 74, 0.25);
}
.p-main { min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.p-name { display: flex; align-items: center; gap: 8px; }
.p-name b { font-size: 20px; color: var(--c-text); overflow-wrap: anywhere; }
.p-tag {
  font-style: normal; font-size: 11px; font-weight: 700;
  padding: 2px 8px; border-radius: 999px;
  background: var(--c-primary-strong); color: #fff; white-space: nowrap;
}
.p-user { font-size: 13px; color: var(--c-text-2); }

/* 分区头 */
.sect-head {
  display: flex; align-items: baseline; gap: 10px;
  flex-wrap: wrap; margin-bottom: 14px;
}
.sect-head h2 {
  margin: 0; font-size: 14px; font-weight: 800;
  color: var(--c-text); letter-spacing: 0.02em;
}
.sect-hint { font-size: 12px; color: var(--c-text-3); }

/* 表单 */
.field { display: block; margin-bottom: 16px; }
.field:last-of-type { margin-bottom: 4px; }
.flabel { display: block; font-size: 12.5px; color: var(--c-text-3); margin-bottom: 6px; }
.field-row { display: flex; gap: 10px; align-items: stretch; }
.field-row .n-input { flex: 1; }
.fhint { display: block; font-size: 11.5px; color: var(--c-text-3); margin-top: 5px; }
.fhint.err { color: var(--c-danger, #dc2626); }
.pwd-actions { margin-top: 4px; }

.info-row {
  display: flex; align-items: baseline; gap: 16px;
  padding: 10px 0; border-top: 1px solid var(--c-line);
}
.info-row .flabel { margin: 0; flex: none; width: 76px; }
.fvalue { font-size: 14px; font-weight: 600; color: var(--c-text); overflow-wrap: anywhere; }
.perms { color: var(--c-primary-strong); }

/* 退出登录 */
.logout-row { display: flex; align-items: center; justify-content: space-between; gap: 14px; flex-wrap: wrap; }
.logout-row b { display: block; font-size: 14px; color: var(--c-text); }
</style>

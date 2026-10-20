<template>
  <div class="card panel">
    <h1>真实生成（官方 API）</h1>
    <p class="lead">
      与线上一致的推理走 <strong>api.genspicy.ai</strong>。须使用你在
      <a href="https://genspicy.ai" target="_blank" rel="noopener">genspicy.ai</a>
      登录后的会员 Token（<strong>访客 Guest Token 无法生成</strong>，官方返回 10022）。
    </p>

    <ol class="steps">
      <li>在官网正常登录（邮箱/Google 等，有钻石的账号）</li>
      <li>F12 → Network，随便点一个请求，复制 Request Header 里的 <code>Bearer eyJ...</code>（只要 eyJ 开头那段 JWT）</li>
      <li>粘贴到下面 → 点「验证并连接」</li>
    </ol>

    <label class="field">
      Access Token
      <textarea v-model="tokenInput" rows="4" placeholder="eyJhbGciOi..." />
    </label>

    <div class="actions">
      <button type="button" class="btn btn-primary" :disabled="busy || !tokenInput.trim()" @click="connect">
        {{ busy ? '验证中…' : '验证并连接' }}
      </button>
      <button v-if="live.isActive.value" type="button" class="btn btn-ghost" @click="disconnect">断开</button>
    </div>

    <p v-if="live.lastError.value" class="err">{{ live.lastError.value }}</p>

    <div v-if="live.whoami.value" class="ok card inner">
      <p><strong>已连接官方账号</strong></p>
      <pre>{{ JSON.stringify(live.whoami.value, null, 2) }}</pre>
      <p class="hint">现在去任意模板页点 Generate，将走真实队列（耗时会比 mock 长）。</p>
    </div>

    <p v-else-if="live.isActive.value" class="hint">Token 已保存，请点验证。</p>
  </div>
</template>

<script setup lang="ts">
const live = useGenspicyLive()
const tokenInput = ref('')
const busy = ref(false)

onMounted(() => {
  live.loadTokenFromStorage()
  if (live.token.value) tokenInput.value = live.token.value
  if (live.token.value) live.verify().catch(() => {})
})

async function connect() {
  busy.value = true
  try {
    const raw = tokenInput.value.trim().replace(/^Bearer\s+/i, '')
    live.setToken(raw)
    await live.verify()
  } catch {
    /* lastError set in composable */
  } finally {
    busy.value = false
  }
}

function disconnect() {
  live.disconnect()
  tokenInput.value = ''
}
</script>

<style scoped>
.panel {
  padding: 24px;
  max-width: 720px;
}
.lead {
  color: var(--muted);
  line-height: 1.6;
}
.lead a {
  color: var(--accent);
}
.steps {
  color: var(--muted);
  font-size: 14px;
  line-height: 1.7;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 16px 0;
}
textarea {
  padding: 12px;
  border-radius: 10px;
  border: 1px solid var(--divider);
  background: var(--surface);
  color: var(--text);
  font-family: ui-monospace, monospace;
  font-size: 12px;
}
.actions {
  display: flex;
  gap: 10px;
}
.err {
  color: #ff6b8a;
  margin-top: 12px;
}
.ok {
  margin-top: 16px;
}
.inner {
  padding: 16px;
}
pre {
  overflow: auto;
  font-size: 11px;
  max-height: 240px;
}
.hint {
  font-size: 13px;
  color: var(--muted);
}
</style>

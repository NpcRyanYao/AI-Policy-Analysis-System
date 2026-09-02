<template>
  <div class="layout-shell">
    <header class="layout-header">
      <router-link to="/" class="brand" style="color:#fff">
        AI 政策合规追踪
        <small>公开政策 · 可追溯分析 · 非法律意见</small>
      </router-link>
      <nav>
        <router-link class="nav-link" to="/">概览</router-link>
        <router-link class="nav-link" to="/policies">政策库</router-link>
        <router-link class="nav-link" to="/compare">对比</router-link>
        <router-link class="nav-link" to="/subscriptions">订阅</router-link>
        <router-link class="nav-link" to="/ingest">补录/采集</router-link>
      </nav>
      <div style="margin-left:auto;min-width:280px">
        <el-input
          v-model="keyword"
          placeholder="检索政策关键词"
          clearable
          @keyup.enter="goSearch"
        >
          <template #append>
            <el-button @click="goSearch">搜索</el-button>
          </template>
        </el-input>
      </div>
    </header>
    <main class="layout-main">
      <router-view />
    </main>
    <footer class="layout-footer">
      分析结果区分事实 / 模型推断 / 建议；建议不构成法律意见。数据来自公开官方渠道并保留原文链接。
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";

const keyword = ref("");
const router = useRouter();

function goSearch() {
  router.push({ path: "/policies", query: { q: keyword.value } });
}
</script>

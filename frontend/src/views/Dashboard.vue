<template>
  <div class="page">
    <h1 class="page-title">监管动态概览</h1>
    <p class="page-sub">
      数据模式 {{ dash?.data_mode }} · 快照 {{ dash?.snapshot_id }} ·
      大模型 {{ dash?.llm_ready ? "已配置" : "未配置（规则引擎兜底）" }}
    </p>
    <div class="card-grid">
      <div class="stat-card"><div class="label">政策总量</div><div class="value">{{ dash?.total ?? "-" }}</div></div>
      <div class="stat-card"><div class="label">今日入库</div><div class="value">{{ dash?.today_new ?? "-" }}</div></div>
      <div class="stat-card"><div class="label">分类覆盖</div><div class="value">{{ dash?.by_category?.length ?? "-" }}</div></div>
      <div class="stat-card"><div class="label">最近采集</div><div class="value" style="font-size:16px;padding-top:10px">{{ formatTime(dash?.crawled_at) }}</div></div>
    </div>

    <el-row :gutter="16" style="margin-top:18px">
      <el-col :md="8" :xs="24">
        <el-card shadow="never">
          <template #header>分类占比</template>
          <div v-for="item in dash?.by_category || []" :key="item.value" style="margin-bottom:10px">
            <div style="display:flex;justify-content:space-between;font-size:13px">
              <span>{{ item.label }}</span><b>{{ item.count }}</b>
            </div>
            <el-progress :percentage="pct(item.count)" :show-text="false" color="#163a5f" />
          </div>
        </el-card>
        <el-card shadow="never" style="margin-top:12px">
          <template #header>监管主题</template>
          <el-tag
            v-for="tag in dash?.tags || []"
            :key="tag.value"
            style="margin:0 8px 8px 0;cursor:pointer"
            @click="$router.push({ path: '/policies', query: { category: tag.value } })"
          >{{ tag.label }}</el-tag>
        </el-card>
      </el-col>
      <el-col :md="16" :xs="24">
        <el-card shadow="never">
          <template #header>最新政策</template>
          <div v-for="item in dash?.latest || []" :key="item.id" class="policy-card" style="margin-bottom:10px">
            <h3>
              <router-link :to="`/policies/${item.id}`">{{ item.title }}</router-link>
              <span v-if="item.importance === 'high'" class="badge-high" style="margin-left:8px">重点提醒</span>
            </h3>
            <div class="meta">
              <span>{{ item.issuing_org }}</span>
              <span>发布 {{ item.publish_time || "-" }}</span>
              <span>{{ levelLabel(item.policy_level) }}</span>
            </div>
            <p style="margin:8px 0 0;color:#475467;font-size:13px">{{ item.summary }}</p>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api } from "../api";

const dash = ref<any>(null);

onMounted(async () => {
  dash.value = (await api.dashboard()).data;
});

function pct(count: number) {
  const total = dash.value?.total || 1;
  return Math.min(100, Math.round((count / total) * 100));
}
function formatTime(v?: string) {
  return v ? String(v).replace("T", " ").slice(0, 16) : "-";
}
function levelLabel(v: string) {
  return { national: "国家", provincial: "省", municipal: "市" }[v] || v;
}
</script>

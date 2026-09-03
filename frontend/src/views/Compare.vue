<template>
  <div class="page">
    <h1 class="page-title">多政策对比</h1>
    <p class="page-sub">选择 2–5 条政策，输出共同要求与差异点。结论属推断，需对照原文。</p>
    <el-select v-model="ids" multiple filterable placeholder="选择政策" style="width:100%;margin-bottom:12px">
      <el-option v-for="p in all" :key="p.id" :label="p.title" :value="p.id" />
    </el-select>
    <el-button type="primary" :loading="loading" @click="run">开始对比</el-button>
    <el-alert
      v-if="result"
      style="margin-top:12px"
      :closable="false"
      :type="result.provenance?.llm_used ? 'success' : 'info'"
      :title="result.provenance?.llm_used ? '本轮对比由大模型生成' : '本轮对比由规则引擎生成（模型未返回可展示字段时会自动回退）'"
    />
    <el-row :gutter="16" style="margin-top:16px" v-if="result">
      <el-col :span="12">
        <el-card shadow="never">
          <template #header>共同要求</template>
          <p v-for="(item, i) in result.common_requirements" :key="'c' + i">{{ displayText(item) }}</p>
          <el-empty v-if="!result.common_requirements?.length" description="没有共同要求" :image-size="64" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never">
          <template #header>差异点</template>
          <p v-for="(item, i) in result.differences" :key="'d' + i">
            <b v-if="item.policy_title">{{ item.policy_title }}：</b>{{ displayText(item) }}
          </p>
          <el-empty v-if="!result.differences?.length" description="没有差异点" :image-size="64" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";

const route = useRoute();
const all = ref<any[]>([]);
const ids = ref<string[]>([]);
const result = ref<any>(null);
const loading = ref(false);

onMounted(async () => {
  all.value = (await api.policies({ page_size: 50 })).data.items;
  if (route.query.ids) ids.value = String(route.query.ids).split(",").filter(Boolean);
  if (ids.value.length >= 2) await run();
});

function displayText(item: any) {
  if (item == null) return "";
  if (typeof item === "string") return item;
  return item.text || item.content || item.requirement || item.summary || item.point || "";
}

async function run() {
  if (ids.value.length < 2) return ElMessage.warning("至少选择 2 条");
  loading.value = true;
  try {
    result.value = (await api.compare(ids.value)).data;
    if (!result.value.common_requirements?.length && !result.value.differences?.length) {
      ElMessage.warning("对比结果为空");
    }
  } catch (e: any) {
    const msg = e.message || "对比失败";
    ElMessage.error(msg.includes("timeout") ? "对比超时：模型响应过慢或开发热重载中断了请求，请去掉 --reload 后重试" : msg);
  } finally {
    loading.value = false;
  }
}
</script>

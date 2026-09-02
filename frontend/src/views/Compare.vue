<template>
  <div class="page">
    <h1 class="page-title">多政策对比</h1>
    <p class="page-sub">选择 2–5 条政策，输出共同要求与差异点。结论属推断，需对照原文。</p>
    <el-select v-model="ids" multiple filterable placeholder="选择政策" style="width:100%;margin-bottom:12px">
      <el-option v-for="p in all" :key="p.id" :label="p.title" :value="p.id" />
    </el-select>
    <el-button type="primary" @click="run">开始对比</el-button>
    <el-row :gutter="16" style="margin-top:16px" v-if="result">
      <el-col :span="12">
        <el-card shadow="never">
          <template #header>共同要求</template>
          <p v-for="(item, i) in result.common_requirements" :key="i">{{ item.text || item }}</p>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never">
          <template #header>差异点</template>
          <p v-for="(item, i) in result.differences" :key="i">
            <b>{{ item.policy_title }}</b> {{ item.text }}
          </p>
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

onMounted(async () => {
  all.value = (await api.policies({ page_size: 50 })).data.items;
  if (route.query.ids) ids.value = String(route.query.ids).split(",").filter(Boolean);
  if (ids.value.length >= 2) await run();
});

async function run() {
  if (ids.value.length < 2) return ElMessage.warning("至少选择 2 条");
  result.value = (await api.compare(ids.value)).data;
}
</script>

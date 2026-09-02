<template>
  <div class="page">
    <h1 class="page-title">订阅中心</h1>
    <p class="page-sub">按关键词、分类、发文机构订阅；日报在站内生成。邮件推送需配置 SMTP。</p>
    <el-row :gutter="16">
      <el-col :md="10" :xs="24">
        <el-card shadow="never">
          <template #header>新建订阅</template>
          <el-form label-position="top">
            <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
            <el-form-item label="关键词（逗号分隔）"><el-input v-model="form.keywords" /></el-form-item>
            <el-form-item label="分类">
              <el-select v-model="form.categories" multiple filterable>
                <el-option v-for="c in cats" :key="c.value" :label="c.label" :value="c.value" />
              </el-select>
            </el-form-item>
            <el-form-item label="机构关键词（逗号分隔）"><el-input v-model="form.orgs" /></el-form-item>
            <el-form-item>
              <el-button type="primary" @click="create">保存订阅</el-button>
              <el-button @click="gen">生成今日日报</el-button>
            </el-form-item>
          </el-form>
        </el-card>
        <el-card shadow="never" style="margin-top:12px">
          <template #header>我的订阅</template>
          <div v-for="s in subs" :key="s.id" class="policy-card">
            <b>{{ s.name }}</b>
            <div class="meta">关键词 {{ (s.keywords || []).join("、") || "无" }} · 分类 {{ (s.categories || []).join("、") || "无" }}</div>
            <el-button size="small" type="danger" text @click="remove(s.id)">删除</el-button>
          </div>
        </el-card>
      </el-col>
      <el-col :md="14" :xs="24">
        <el-card shadow="never">
          <template #header>历史日报</template>
          <div v-for="d in digests" :key="d.id" class="policy-card">
            <h3>{{ d.title }}</h3>
            <p>{{ d.summary }}</p>
            <div v-for="h in d.highlights" :key="h.policy_id" style="margin:6px 0">
              <router-link :to="`/policies/${h.policy_id}`">{{ h.title }}</router-link>
              <span v-if="h.importance === 'high'" class="badge-high" style="margin-left:6px">高亮</span>
            </div>
          </div>
          <el-empty v-if="!digests.length" description="暂无日报，请先生成" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../api";

const cats = ref<any[]>([]);
const subs = ref<any[]>([]);
const digests = ref<any[]>([]);
const form = reactive({ name: "", keywords: "", categories: [] as string[], orgs: "" });

async function load() {
  cats.value = (await api.meta()).data.flat_categories || [];
  subs.value = (await api.subscriptions()).data;
  digests.value = (await api.digests()).data;
}
onMounted(load);

async function create() {
  if (!form.name) return ElMessage.warning("请填写名称");
  await api.addSubscription({
    name: form.name,
    keywords: form.keywords.split(/[,，]/).map((s) => s.trim()).filter(Boolean),
    categories: form.categories,
    orgs: form.orgs.split(/[,，]/).map((s) => s.trim()).filter(Boolean),
    channel: "in_app",
  });
  ElMessage.success("已保存");
  form.name = "";
  form.keywords = "";
  form.categories = [];
  form.orgs = "";
  await load();
}

async function remove(id: string) {
  await api.deleteSubscription(id);
  await load();
}

async function gen() {
  await api.generateDigest();
  await load();
  ElMessage.success("日报已生成");
}
</script>

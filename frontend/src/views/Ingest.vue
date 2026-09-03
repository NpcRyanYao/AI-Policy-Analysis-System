<template>
  <div class="page">
    <h1 class="page-title">补录与采集</h1>
    <p class="page-sub">
      实时抓取可能因政府网站反爬失败；失败时请使用快照装载或粘贴公开正文。写操作在生产环境需要管理员令牌。
    </p>
    <el-row :gutter="16">
      <el-col :md="12" :xs="24">
        <el-card shadow="never">
          <template #header>按 URL 补录</template>
          <el-form label-position="top">
            <el-form-item label="原文 URL"><el-input v-model="form.url" /></el-form-item>
            <el-form-item label="标题（可选，抓取失败时必填）"><el-input v-model="form.title" /></el-form-item>
            <el-form-item label="发文机构"><el-input v-model="form.issuing_org" /></el-form-item>
            <el-form-item label="发布时间"><el-date-picker v-model="form.publish_time" value-format="YYYY-MM-DD" /></el-form-item>
            <el-form-item label="正文（抓取失败时粘贴公开文本）">
              <el-input v-model="form.content" type="textarea" :rows="8" />
            </el-form-item>
            <el-button type="primary" :loading="loading" @click="submit">提交补录</el-button>
          </el-form>
        </el-card>
      </el-col>
      <el-col :md="12" :xs="24">
        <el-card shadow="never">
          <template #header>快照 / 实时采集</template>
          <el-space wrap>
            <el-button :loading="loading" @click="snap">重新装载当前快照</el-button>
            <el-button :loading="loading" @click="crawl">尝试实时抓取</el-button>
          </el-space>
          <pre style="margin-top:16px;background:#f8fafc;padding:12px;white-space:pre-wrap">{{ log }}</pre>
        </el-card>
        <el-alert
          style="margin-top:12px"
          type="warning"
          :closable="false"
          title="异常情形"
          description="官方站点超时、反爬拦截、缺正文时，系统会返回明确错误并保留已有快照数据，不会用空结果覆盖库。"
        />
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { useRouter } from "vue-router";
import { api } from "../api";

const router = useRouter();
const loading = ref(false);
const log = ref("尚未执行");
const form = reactive({
  url: "",
  title: "",
  issuing_org: "",
  publish_time: "",
  content: "",
});

async function submit() {
  if (!/^https?:\/\//i.test(form.url.trim())) {
    ElMessage.warning("请填写以 http:// 或 https:// 开头的原文链接");
    return;
  }
  loading.value = true;
  try {
    const payload = {
      url: form.url.trim(),
      title: form.title.trim() || null,
      issuing_org: form.issuing_org.trim() || null,
      publish_time: form.publish_time || null,
      content: form.content.trim() || null,
      source_id: "manual",
    };
    const { data } = await api.ingestUrl(payload);
    ElMessage.success("补录成功");
    router.push(`/policies/${data.id}`);
  } catch (e: any) {
    ElMessage.error(e.message);
    log.value = e.message;
  } finally {
    loading.value = false;
  }
}

async function snap() {
  loading.value = true;
  try {
    const { data } = await api.ingestSnapshot();
    log.value = JSON.stringify(data, null, 2);
    ElMessage.success("快照已装载");
  } catch (e: any) {
    log.value = e.message;
    ElMessage.error(e.message);
  } finally {
    loading.value = false;
  }
}

async function crawl() {
  loading.value = true;
  try {
    const { data } = await api.ingestCrawl();
    log.value = JSON.stringify(data, null, 2);
    ElMessage.success("采集任务完成");
  } catch (e: any) {
    log.value = e.message;
    ElMessage.error(e.message);
  } finally {
    loading.value = false;
  }
}
</script>

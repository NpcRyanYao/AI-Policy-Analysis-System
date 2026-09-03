<template>
  <div class="page" v-if="detail">
    <h1 class="page-title">{{ detail.title }}</h1>
    <div class="meta" style="margin-bottom:12px">
      <span>{{ detail.issuing_org }}</span>
      <span>发布 {{ detail.publish_time || "-" }}</span>
      <span>生效 {{ detail.effective_time || "-" }}</span>
      <span>入库 {{ detail.ingest_method }} / {{ detail.crawl_time }}</span>
      <span v-if="detail.importance === 'high'" class="badge-high">重点政策</span>
    </div>
    <p>
      <a class="src-link" :href="detail.original_url" target="_blank" rel="noopener">查看官方原文 ↗</a>
      <el-button size="small" style="margin-left:8px" @click="toggleFav">{{ detail.favorited ? "取消收藏" : "收藏" }}</el-button>
      <a class="el-button el-button--small" :href="api.pdfUrl(detail.id)" target="_blank" rel="noopener">导出 PDF</a>
      <el-button size="small" :loading="refreshing" @click="refresh">重新生成合规摘要</el-button>
    </p>
    <el-tag v-for="c in detail.categories" :key="c.category + c.subcategory" style="margin:0 8px 12px 0">{{ c.label }}</el-tag>

    <el-row :gutter="16">
      <el-col :md="17" :xs="24">
        <el-card shadow="never">
          <template #header>核心信息概览 <small style="color:#667085">（结构化解析，属推断）</small></template>
          <p><b>适用范围：</b>{{ detail.structured?.applicable_scope || "—" }}</p>
          <p><b>主题：</b>{{ (detail.structured?.themes || []).join("、") || "—" }}</p>
          <p><b>解析器：</b>{{ detail.structured?.parser }}</p>
        </el-card>

        <el-card shadow="never" style="margin-top:12px">
          <template #header>
            合规影响分析
            <small style="color:#667085">模型 {{ detail.analysis?.model_name }} · 不构成法律意见</small>
          </template>
          <div v-if="detail.analysis">
            <el-alert type="info" :closable="false" style="margin-bottom:12px" :title="disclaimer" />
            <h4>核心监管要求</h4>
            <div v-for="(item, i) in detail.analysis.core_requirements" :key="'r'+i">
              <p>{{ asText(item) }} <el-tag size="small" class="kind-inference">推断</el-tag></p>
              <div class="quote" v-if="item.source_quote">原文依据：{{ item.source_quote }} {{ item.article_no }}</div>
            </div>
            <h4>适用主体范围</h4>
            <p>{{ detail.analysis.applicable_subjects }}</p>
            <h4>违规风险与处罚依据</h4>
            <div v-for="(item, i) in detail.analysis.risk_and_penalties" :key="'p'+i">
              <p>
                {{ asText(item) }}
                <el-tag size="small" :class="item.kind === 'fact' ? 'kind-fact' : 'kind-inference'">{{ item.kind === 'fact' ? '事实' : '推断' }}</el-tag>
              </p>
              <div class="quote" v-if="item.source_quote">原文依据：{{ item.source_quote }}</div>
            </div>
            <h4>通用合规行动建议</h4>
            <p v-for="(item, i) in detail.analysis.action_suggestions" :key="'a'+i">
              {{ asText(item) }} <el-tag size="small" class="kind-advice">建议</el-tag>
            </p>
          </div>
          <el-empty v-else description="暂无分析结果" />
        </el-card>

        <el-card shadow="never" style="margin-top:12px">
          <template #header>政策原文（公开摘录，关键词高亮）</template>
          <el-input v-model="hl" placeholder="输入需高亮的关键词" clearable style="max-width:280px;margin-bottom:12px" />
          <div style="white-space:pre-wrap;line-height:1.7;font-size:14px" v-html="highlighted"></div>
        </el-card>
      </el-col>
      <el-col :md="7" :xs="24">
        <el-card shadow="never">
          <template #header>条款类型</template>
          <el-tag v-for="c in detail.clauses.slice(0, 12)" :key="c.paragraph_index + c.text" size="small" style="margin:0 6px 6px 0">{{ c.clause_type }} {{ c.article_no }}</el-tag>
        </el-card>
        <el-card shadow="never" style="margin-top:12px">
          <template #header>相关政策</template>
          <p v-for="r in related" :key="r.id" style="margin:8px 0">
            <router-link :to="`/policies/${r.id}`">{{ r.title }}</router-link>
          </p>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";

const route = useRoute();
const detail = ref<any>(null);
const related = ref<any[]>([]);
const hl = ref("");
const refreshing = ref(false);
const disclaimer = computed(
  () => detail.value?.analysis?.provenance?.disclaimer || "分析结论需对照原文使用，不构成法律意见。",
);
const highlighted = computed(() => {
  const text = (detail.value?.content || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
  if (!hl.value) return text;
  const re = new RegExp(hl.value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "g");
  return text.replace(re, (m: string) => `<mark>${m}</mark>`);
});

async function load() {
  const id = String(route.params.id);
  detail.value = (await api.policy(id)).data;
  related.value = (await api.related(id)).data;
}

onMounted(load);
watch(() => route.params.id, load);

function asText(item: any) {
  return typeof item === "string" ? item : item?.text || "";
}

async function toggleFav() {
  if (detail.value.favorited) await api.removeFavorite(detail.value.id);
  else await api.addFavorite(detail.value.id);
  await load();
}

async function refresh() {
  refreshing.value = true;
  try {
    await api.analyze(detail.value.id);
    await load();
    ElMessage.success("已重新生成");
  } catch (e: any) {
    const msg = e.message || "生成失败";
    ElMessage.error(msg.includes("timeout") ? "生成超时：DeepSeek 响应过慢，可把 .env 中 LLM_TIMEOUT_SECONDS 调到 120 后重启后端" : msg);
  } finally {
    refreshing.value = false;
  }
}
</script>

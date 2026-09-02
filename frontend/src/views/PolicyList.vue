<template>
  <div class="page">
    <h1 class="page-title">政策库</h1>
    <p class="page-sub">支持关键词、标题、层级、机构、分类、条款类型筛选；结果可导出 Excel。</p>
    <div class="two-col">
      <el-card shadow="never">
        <el-form label-position="top">
          <el-form-item label="关键词全文">
            <el-input v-model="filters.q" clearable />
          </el-form-item>
          <el-form-item label="标题">
            <el-input v-model="filters.title" clearable />
          </el-form-item>
          <el-form-item label="政策层级">
            <el-select v-model="filters.policy_level" clearable placeholder="全部">
              <el-option label="国家" value="national" />
              <el-option label="省" value="provincial" />
              <el-option label="市" value="municipal" />
            </el-select>
          </el-form-item>
          <el-form-item label="发文机构">
            <el-input v-model="filters.issuing_org" clearable />
          </el-form-item>
          <el-form-item label="分类">
            <el-select v-model="filters.category" clearable placeholder="全部" filterable>
              <el-option v-for="c in cats" :key="c.value" :label="c.label" :value="c.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="条款类型">
            <el-select v-model="filters.clause_type" clearable placeholder="全部">
              <el-option label="强制性" value="mandatory" />
              <el-option label="禁止性" value="prohibited" />
              <el-option label="推荐性" value="recommended" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="load(1)">筛选</el-button>
            <el-button @click="reset">重置</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <div>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
          <div>
            共 {{ total }} 条
            <el-radio-group v-model="filters.sort" size="small" style="margin-left:12px" @change="load(1)">
              <el-radio-button value="publish_time">按时间</el-radio-button>
              <el-radio-button value="relevance">按相关度</el-radio-button>
            </el-radio-group>
          </div>
          <div>
            <el-button @click="goCompare">对比已选 ({{ selected.length }})</el-button>
            <a class="el-button el-button--primary" :href="api.excelUrl(selected)" target="_blank" rel="noopener">导出 Excel</a>
          </div>
        </div>
        <div v-for="item in items" :key="item.id" class="policy-card">
          <el-checkbox :model-value="selected.includes(item.id)" @change="toggle(item.id)" style="margin-right:8px" />
          <h3 style="display:inline">
            <router-link :to="`/policies/${item.id}`">{{ item.title }}</router-link>
            <span v-if="item.importance === 'high'" class="badge-high" style="margin-left:8px">重点</span>
          </h3>
          <div class="meta" style="margin-top:8px">
            <span>{{ item.issuing_org }}</span>
            <span>发布 {{ item.publish_time || "-" }}</span>
            <span>{{ item.policy_level }}</span>
            <el-tag v-for="c in item.categories" :key="c.category + c.subcategory" size="small" style="margin-right:6px">{{ c.label }}</el-tag>
          </div>
          <p style="margin:8px 0 0;color:#475467;font-size:13px">{{ item.summary }}</p>
        </div>
        <el-pagination
          v-if="total > pageSize"
          background
          layout="prev, pager, next"
          :page-size="pageSize"
          :current-page="page"
          :total="total"
          @current-change="load"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";

const route = useRoute();
const router = useRouter();
const items = ref<any[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = 8;
const selected = ref<string[]>([]);
const cats = ref<{ value: string; label: string }[]>([]);
const filters = reactive({
  q: "",
  title: "",
  policy_level: "",
  issuing_org: "",
  category: "",
  clause_type: "",
  sort: "publish_time",
});

onMounted(async () => {
  const meta = (await api.meta()).data;
  cats.value = meta.flat_categories || [];
  filters.q = String(route.query.q || "");
  filters.category = String(route.query.category || "");
  await load(1);
});

watch(
  () => route.query,
  async () => {
    filters.q = String(route.query.q || filters.q);
    filters.category = String(route.query.category || filters.category);
    await load(1);
  },
);

async function load(p = 1) {
  page.value = p;
  const { data } = await api.policies({ ...filters, page: p, page_size: pageSize });
  items.value = data.items;
  total.value = data.total;
}

function reset() {
  Object.assign(filters, {
    q: "",
    title: "",
    policy_level: "",
    issuing_org: "",
    category: "",
    clause_type: "",
    sort: "publish_time",
  });
  load(1);
}

function toggle(id: string) {
  selected.value = selected.value.includes(id)
    ? selected.value.filter((x) => x !== id)
    : [...selected.value, id];
}

function goCompare() {
  if (selected.value.length < 2) {
    ElMessage.warning("请至少选择 2 条政策");
    return;
  }
  router.push({ path: "/compare", query: { ids: selected.value.join(",") } });
}
</script>

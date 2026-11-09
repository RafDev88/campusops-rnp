<script setup lang="ts">
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { BarChart, LineChart, GraphChart, PieChart } from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  AriaComponent,
  LegendComponent,
} from "echarts/components";
import VChart from "vue-echarts";
use([
  CanvasRenderer,
  BarChart,
  LineChart,
  GraphChart,
  PieChart,
  GridComponent,
  TooltipComponent,
  AriaComponent,
  LegendComponent,
]);
defineProps<{ option: object }>();
const emit = defineEmits<{
  select: [event: { name: string; dataType?: string; data?: { id?: string } }];
}>();
function selected(value: unknown) {
  const event = value as {
    name: string;
    dataType?: string;
    data?: { id?: string };
  };
  if (typeof event.name === "string") emit("select", event);
}
</script>
<template>
  <VChart
    class="chart"
    :option="{ aria: { enabled: true }, ...option }"
    autoresize
    @click="selected"
  />
</template>

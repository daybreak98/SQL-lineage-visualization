/**
 * vitest.config.ts - 前端测试配置
 *
 * P0 配置:
 * - jsdom 环境用于 DOM 渲染测试
 * - @vitejs/plugin-react 支持 JSX/TSX
 * - globals: true 使得 describe/it/expect 无需显式 import
 */

import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: [],
    // 匹配 __tests__ 目录下所有测试文件
    include: ["src/**/__tests__/**/*.{test,spec}.{ts,tsx}"],
  },
});

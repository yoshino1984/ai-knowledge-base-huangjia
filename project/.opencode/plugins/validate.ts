import type { Plugin } from "@opencode-ai/plugin"

export const ValidateHook: Plugin = async ({ $ }) => {
  return {
    "tool.execute.after": async (input) => {
      const tool = input.tool
      const args = input.args ?? {}
      const filePath = args.file_path ?? args.filePath

      if (!filePath || typeof filePath !== "string") {
        return
      }

      const normalizedFilePath = filePath.replace(/\\/g, "/")
      if (
        (tool !== "write" && tool !== "edit") ||
        !normalizedFilePath.endsWith(".json") ||
        !normalizedFilePath.includes("knowledge/articles/")
      ) {
        return
      }

      try {
        // 先做 JSON 结构校验，再做分值评估，失败不阻塞主流程
        await $`python3 hooks/validate_json.py ${normalizedFilePath}`.nothrow()
        await $`python3 hooks/check_quality.py ${normalizedFilePath}`.nothrow()
      } catch {
        // 避免插件异常把工具链阻塞住，保持和交互流程解耦
      }
    },
  }
}


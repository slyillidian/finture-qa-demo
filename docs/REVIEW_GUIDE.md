# 评审导读

## 解决的问题

页面在 App 内能打开，不代表通过外部链接、冷启动和运行中入口都能到达正确页面。Link Probe 将这些重复检查固化为 JSON 用例，重复执行并保留页面、业务参数、原生 UI 和截图证据。目标用户是可以修改自己 Flutter App 的 iOS 开发者；目前不是无需接入的通用 App 测试平台。

## 建议评审顺序

1. 阅读根目录 README，按步骤构建并安装示例 App。
2. 执行 cases/smoke.json：6 条用例，探针及 UI 断言通过。
3. 打开生成的 report.md 预览：每条用例的截图和预期/实际结果。
4. 执行 cases/ui-negative-control.json：预期退出码 1，证明探针通过不能掩盖 UI 不匹配。此用例故意配置错误 UI 预期，不是线上事故。
5. 查看 evidence/ui-assertions-2026-11-08.json 与 ui-rendering-fault.png：开发中还实际构建过只改坏页面显示、保持探针正确的版本，工具正确识别。正常源码已还原。
6. 查看 JOURNAL.md、完整 Git 历史，以及单独交付的原始 AI 对话文本。

## 已有证据

| 验证 | 结果 | 证据 |
|---|---|---|
| 初版模拟器运行 | 首跑失败并暴露原生路由假设错误，修正后通过 | JOURNAL；verification-2026-11-06.json |
| 首次系统确认框 | XCUITest 匹配并点击指定 App 的打开确认框 | alert-handling-2026-11-06.json |
| 独立 UI 断言 | 探针正确、UI 故意显示 999 时失败 | ui-assertions-2026-11-08.json；故障截图 |
| 所有用例截图 | 6 条通过且各有独立 PNG | JOURNAL 中 20261108-144251 运行记录 |
| 自动化逻辑验证 | 7 个 Python 测试通过；2 个 Flutter 测试通过 | tests/；example/test/；JOURNAL |

## AI 与人的分工

AI 实质参与 Python 执行器、Flutter 示例、XCUITest、测试与文档。提交者选择问题、质疑价值、亲自运行 iPhone 15 Pro Max 模拟器、要求独立 UI 断言及全部截图。工具运行时不调用 AI。

## 实际边界

只验证模拟器、自定义 scheme、约定的页面状态和 UI 文本。真机、Universal Links、登录和返回栈尚未实现；没有声称存在外部使用者、生产事故、节省工时或完整视觉正确性。示例 App 证明执行链路可用，跨项目可复用性仍需实际接入第二个 App 验证。

# 交付内容与核对方式

## 三个提交物

1. **完整 Git 仓库**：https://github.com/slyillidian/finture-qa-demo 。另提供 finture-qa-demo-repository.zip，包含完整 .git 历史，不是 git archive 或单次提交快照。
2. **Demo 视频**：Link-Probe-Demo.mp4，约 63 秒，无旁白、有中文说明，实际模拟器录制，包含正常用例及明确标注的错误 UI 预期反向检查。
3. **AI 会话**：AI-Conversation.zip，包含原始 user/assistant 对话文本、原始选定消息 JSONL、阅读索引、范围说明、校验信息及提交者补充确认。不是事后生成的对话摘要；不包含内部推理、系统/开发者配置或全部工具日志。

视频与对话作为附件单独交付，不向公共 Git 仓库提交整份私人会话。SESSION_NOTES.md 是早期摘要，与原始文本导出用途不同。

## 复核

- 解压仓库 ZIP 后，在项目目录运行 `git log --oneline`，应看到开发过程中的多次有效提交。
- 运行 README 的安装及 smoke 步骤，预期 6 条通过；UI 反向检查预期退出码 1。
- Markdown 预览 report.md，逐条看 PNG，文本断言通过不能替代视觉复核。
- 源代码和历史不会包含个人 SDK 绝对路径的 settings.json，也不包含生成的 build/reports 缓存。原开发目录中的生成性 .metadata 差异未带入仓库提交，交付以已提交的 iOS 元数据为准。
- 以 JOURNAL 的真实日程和边界为准：11/5 开始、11/9 计划提前提交，已确认允许提前交付；不虚构第 7 天或真机成功记录。

## 发送前最后检查

提交者审阅 JOURNAL 与角色思考、播放视频、确认附件可打开，并使用准备好的邮件草稿自行发送到作业指定邮箱。项目不会自动发送邮件，当前材料不声称已发送。

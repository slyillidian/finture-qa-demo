# Demo 录制脚本（建议 75～100 秒）

只拍模拟器、用例和报告，不展示私人通知、账户或其他项目。可以无旁白，配字幕。真实运行结果以实际输出为准；需要剪掉等待时明确标注“等待已剪辑”，不伪装成性能数据。

| 时间 | 画面 | 讲解/字幕 |
|---|---|---|
| 0～10 秒 | 项目名与一个商品链接 | Link Probe：本地 Flutter iOS Deep Link 回归工具。检查外部链接最终是否进入正确页面。运行时不调用 AI。 |
| 10～20 秒 | smoke.json 一条用例 | 同时声明启动状态、目标页面、商品 ID 和可见 UI 文本。 |
| 20～50 秒 | 执行 smoke；模拟器跳转 | 自动执行冷启动、运行中及异常链接；首次 URL 打开确认框可自动处理。 |
| 50～65 秒 | 报告汇总与 PNG | 探针与独立 XCUITest 都通过才通过；所有用例截图用于人工视觉复核。 |
| 65～85 秒 | ui-negative-control 的失败报告 | 此处故意配置错误 UI 期望，演示探针通过但 UI 失败。不是线上事故。 |
| 85～100 秒 | evidence 故障截图与限制 | 开发中也注入过真实显示错误并捕获。当前只支持模拟器，真机和完整视觉检查尚未实现。 |

## 运行命令

```sh
export DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer
xcrun simctl list devices booted
python3 -u src/link_probe.py --device <已启动模拟器UDID> --cases cases/smoke.json
python3 -u src/link_probe.py --device <同一UDID> --cases cases/ui-negative-control.json
```

第二条预期退出码 1，不是演示失败。打开本次生成目录，避免误看旧报告。用 VS Code 的 Markdown 预览展示 PNG；不要进入 xcresult 的 Info.plist 当作报告阅读。

## 不应宣称

不要宣称“全自动完整测试”“真机已支持”“节省多少工时”“七天每天都在开发”。尚未测量的收益、没有发生的体验不写进视频。

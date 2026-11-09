# Demo 录制脚本与最终视频说明

最终成片为 [Link-Probe-Demo.mp4](Link-Probe-Demo.mp4)，62.73 秒、无音轨、中文说明。真实模拟器录屏展示在右侧，左侧是说明卡片与基于本次实际输出的结果摘要；没有录入私人桌面内容。下表为实际成片结构，原计划较长，最终按真实执行时间收敛。

| 时间（约） | 画面与说明 |
|---|---|
| 0～5 秒 | 问题与工具定位：检查外部链接最终是否进入正确页面。 |
| 5～38 秒 | 6 条正常用例的真实模拟器页面跳转，说明探针、独立 UI 断言及截图。 |
| 38～55 秒 | 明确标注的反向检查：UI 预期故意为 Product 999，实际打开 Product 123，预期失败；不是线上事故。 |
| 55～63 秒 | 本次实际结果摘要：正常 6/6 通过、反向退出码 1，并说明报告、截图和能力边界。 |

视频没有展示终端或报告编辑器；报告差异与开发阶段注入渲染故障的证据可在仓库 evidence/ 阅读，不将字幕摘要冒充报告界面的录屏。

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

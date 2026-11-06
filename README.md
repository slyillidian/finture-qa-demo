# Link Probe

面向 Flutter iOS 开发者的本地 Deep Link 回归工具。将重复的“终止/启动 App → 打开链接 → 核对页面与参数”固化成可重复执行的用例。运行时不使用 AI、不需要 API Key。

项目正在开发中；进展与实际验证见 JOURNAL.md。示例 App 是可控验证对象，不代表已有真实用户或线上收益。

## 首版范围

- iOS Simulator、Flutter 示例 App、自定义 URL scheme。
- 冷启动与运行中链接；验证页面及商品 ID。
- JSON 用例、结果报告、失败截图。

## 环境

macOS、完整 Xcode（含 iOS Simulator runtime）、Flutter、Python 3.10+。CLI 只使用 Python 标准库。默认 Bundle ID 为 dev.sly.linkProbe。

```sh
export DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer
cd example
flutter pub get
flutter build ios --simulator --debug --dart-define=QA_PROBE=true
cd ..
xcrun simctl boot <模拟器UDID>  # 若尚未启动
xcrun simctl bootstatus <模拟器UDID> -b
xcrun simctl install <模拟器UDID> example/build/ios/iphonesimulator/Runner.app
python3 src/link_probe.py --device <模拟器UDID> --cases cases/smoke.json
```

运行前安装上述测试构建。成功退出码为 0，用例失败为 1，配置/环境错误为 2。结果写入 reports/ 下独立运行目录。运行会启动或终止指定 App，请使用测试模拟器。

```sh
python3 -m unittest discover -s tests -v
cd example && flutter test
```

## 判断方式与限制

测试构建在页面完成首帧回调后，向沙盒 tmp/link-probe-state.json 原子写入页面、业务参数及收到的路由。CLI 清除旧状态，发送链接并等待新状态，核对路由和预期字段。QA_PROBE 默认关闭；请勿将探针作为正式业务接口。

这证明测试探针所报告的页面状态符合预期，不证明所有像素、交互、数据加载或真实用户体验正确；截图仅辅助人工检查。首版不支持 Android、真机、Universal Links、登录自动化、并发运行和任意第三方 App。接入其他项目需要在目标页面就绪时提供同一格式的状态文件，不能仅在收到链接时报告成功。

## AI 协作与交付

AI 实质参与核心 App、CLI、测试和文档的编写；人工负责范围判断与验收。JOURNAL.md 仅记录实际发生的过程，不预填未来日期。evidence/ 保存协作摘要，不能代替原始 AI 会话记录；最终需另行导出/保存真实会话及录制 30 秒～2 分钟 Demo。

## 首次运行与路由约定

首次打开自定义 scheme 时，模拟器可能弹出“在 Link Probe 中打开”，请在 Simulator 确认后重新执行；未确认时工具会超时失败，不会自动点击系统弹窗。示例 URL 为 `linkprobe://app/product/123`，Flutter 页面使用 `/product/123`。首版对比 URL 的 path，不验证 host 或 query 的业务语义。Flutter 的 iOS 链接生命周期参考 [官方说明](https://docs.flutter.dev/ui/navigation/deep-linking)。

## 验证工具确实能失败

```sh
python3 src/link_probe.py --device <模拟器UDID> --cases cases/negative-control.json
```

该用例故意要求商品 999，但链接打开商品 123，预期退出码为 1，报告显示 product_id 不匹配并附失败截图。这是显式的反向检查，不是线上事故或真实 App 缺陷。

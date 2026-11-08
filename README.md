# Link Probe

面向 Flutter iOS 开发者的本地 Deep Link 回归工具。将重复的“终止/启动 App → 打开链接 → 核对页面与参数”固化成可重复执行的用例。运行时不使用 AI、不需要 API Key。

项目正在开发中；进展与实际验证见 JOURNAL.md。示例 App 是可控验证对象，不代表已有真实用户或线上收益。

## 首版范围

- iOS Simulator、Flutter 示例 App、自定义 URL scheme。
- 冷启动与运行中链接；验证页面及商品 ID。
- JSON 用例、结果报告、每条用例截图（成功与失败均保留）。
- 独立 XCUITest 检查可见 UI 文本与可访问性标识。

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

用例配置 `ui` 后，探针与原生 UI 断言都必须通过：UI 断言检查 App 处于前台，标识对应元素唯一、可交互且文本一致。它不证明所有像素、布局、交互、数据加载或真实用户体验正确；截图辅助人工检查。未配置 `ui` 的旧用例仍仅检查探针，报告明确标为 `not_requested`。首版不支持 Android、真机、Universal Links、登录自动化、并发运行和任意第三方 App。接入其他项目需要在目标页面就绪时提供同一格式的状态文件，不能仅在收到链接时报告成功。

## AI 协作与交付

AI 实质参与核心 App、CLI、测试和文档的编写；人工负责范围判断与验收。JOURNAL.md 仅记录实际发生的过程，不预填未来日期。evidence/ 保存协作摘要，不能代替原始 AI 会话记录；最终需另行导出/保存真实会话及录制 30 秒～2 分钟 Demo。

## 首次运行与路由约定

首次打开自定义 scheme 时，模拟器可能弹出“在 Link Probe 中打开”。现在默认自动处理：发送链接后约 1.5 秒仍未收到目标路由时，Python 调用仓库内独立的 XCUITest 辅助工程，精确匹配指定 App 的打开链接确认框并点击“打开”。随后继续验证页面和参数。辅助程序找不到弹窗时正常返回，遇到其他弹窗则拒绝点击并将用例判失败。示例 URL 为 `linkprobe://app/product/123`，Flutter 页面使用 `/product/123`。首版对比 URL 的 path，不验证 host 或 query 的业务语义。Flutter 的 iOS 链接生命周期参考 [官方说明](https://docs.flutter.dev/ui/navigation/deep-linking)。

## 验证工具确实能失败

```sh
python3 src/link_probe.py --device <模拟器UDID> --cases cases/negative-control.json
```

该用例故意要求商品 999，但链接打开商品 123，预期退出码为 1，报告显示 product_id 不匹配并附失败截图。这是显式的反向检查，不是线上事故或真实 App 缺陷。


## 自动处理系统确认框

默认命令不变，无需另装 Appium、Python 包或 Ruby gem；Xcode 会在需要时构建并安装测试辅助 Runner。辅助工程独立于 Flutter App，不修改 App 的正式 Target。

```sh
# 换成其他 App 时，必须指定弹窗中的准确显示名称
python3 src/link_probe.py --device <模拟器UDID> --bundle <BundleID> --app-name "应用显示名称"

# 调试时可禁用自动处理，恢复人工确认方式
python3 src/link_probe.py --device <模拟器UDID> --alert-policy manual
```

- 当前匹配简体中文及英文的已知 URL 打开确认标题，未知语言/文案会保留失败证据，不猜测按钮。
- 正常快速到达目标页面时，不启动弹窗检查；配置了 `ui` 的用例仍会启动独立 UI 检查。慢启动或路由异常也可能触发一次弹窗检查；没有弹窗时会继续等待页面。
- 第一次触发辅助程序会增加构建/测试启动耗时，本机真实首次确认用例约 16 秒。页面等待时间不包含辅助程序耗时；每个辅助构建/测试命令各有 120 秒上限。
- 报告中的 `alert_handling` 为 `opened` 或 `not_present`；辅助错误记录在 `error`。构建日志为 `alert-build.log`，每条检查的日志为 `NN-alert.log`，截图附件位于 `NN-alert.xcresult`，可通过 Xcode 打开。最终页面不符合预期仍然失败。
- 不支持并发运行（共享辅助构建缓存位于 `work/alert-helper`）；切换 Xcode/runtime 后如缓存异常，可删除这个生成目录后重跑。

实现使用 Apple 的 [XCUIAutomation](https://developer.apple.com/documentation/xcuiautomation) 访问系统弹窗；不预写授权、不修改系统安全配置。


## UI 断言（需要重新构建并安装示例 App）

`cases/smoke.json` 的 6 条用例现已包含 UI 断言。命令不变，但必须按上面的构建/安装步骤更新 App；旧构建没有 `qa.title` / `qa.reason` 标识，会报 UI 断言失败。

```json
{
  "name": "cold product 123",
  "url": "linkprobe://app/product/123",
  "launch": "cold",
  "expect": {"screen": "product_detail", "product_id": "123"},
  "ui": [{"id": "qa.title", "label": "Product 123"}]
}
```

- `id` 为 Flutter `Semantics(identifier: ...)` 导出的原生可访问性标识；`label` 为实际可见 Text 导出的精确文本，不是探针值。标识不携带商品编号，避免把预期藏在标识中。
- XCUITest 不主动 launch/activate App，不改变待验证的冷启动/运行中跳转结果；它独立查询当前原生 UI 树。检查要求 App 在前台，匹配元素恰好一个，且 `isHittable` 为真。
- 错误页同时检查 `qa.title` 的 `Invalid link` 和 `qa.reason` 的具体原因。断言列表非空、标识唯一；本版不支持滚动查找、模糊匹配或任意 UI 操作。
- 报告新增 `probe_passed` 和 `ui_assertions`，记录预期文本、实际文本、匹配数量、可交互状态。探针失败时 UI 检查标为 `probe_failed`；UI 测试异常时用例失败，不能退回探针结果算通过。
- 每条 UI 检查写入 `NN-ui.log` 和 `NN-ui.xcresult`；xcresult 包含截图，失败时附 UI 层级。每条用例结束后同时保存顶层 PNG：通过为 `NN-pass.png`，失败为 `NN-failure.png`。
- 每条用例启动一次 XCTest 会话，有明显额外耗时；首版优先确保断言独立可靠，尚未优化成常驻会话。`--alert-policy manual` 仅禁用自动点击系统弹窗，不禁用配置的 UI 断言。

UI 反向检查（探针期望正确，故意要求错误页面标题，预期退出码 1）：

```sh
python3 src/link_probe.py --device <模拟器UDID> --cases cases/ui-negative-control.json
```

这是明确标注的错误预期，用于验证断言路径；开发验证还临时构建了“UI 显示 999、探针报告 123”的渲染错误版本，记录见 JOURNAL.md。故障代码未保留在正式源文件中。


## 日常查看截图与原始诊断包

每条用例在检查结束后、下一条执行前，保存独立 PNG；成功和失败均截图。打开 `report.md` 的 Markdown 预览即可逐条查看截图，`results.json` 的 `screenshot` 为相对文件名。截图失败单独记录为 `screenshot_error`，报告明确提示缺失；截图本身不改变已有的自动断言结果。历史报告不会自动补图，需重新执行。

`.xcresult` 是 Xcode 的原始测试结果包，不是供文本编辑器阅读的目录。它保留 XCTest 执行详情、失败诊断、附件截图，UI 断言失败时还保留 UI 层级。需要深入排查时可在 macOS 终端执行 `open /完整路径/01-ui.xcresult`，由 Xcode 查看；平时直接阅读 Markdown、JSON、PNG 和 `.log` 即可。当前保留 xcresult 作为诊断证据；生成报告目录已被 Git 忽略，旧运行目录可按需自行清理。

独立 PNG 是检查结束时的设备画面，xcresult 附件是测试内部采集的证据，拍摄时间可能不同。文本断言通过仍可能存在布局、图片或遮挡问题，需要人工查看截图。

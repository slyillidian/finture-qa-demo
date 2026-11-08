import XCTest

/// Only accepts the named app's URL-open confirmation, never a generic permission.
final class AlertHelper: XCTestCase {
    static func allowedTitles(for name: String) -> Set<String> {
        [
            "Open in “\(name)”?", "Open in \"\(name)\"?",
            "Open this page in “\(name)”?", "Open this page in \"\(name)\"?",
            "在“\(name)”中打开？", "在“\(name)”中打开?"
        ]
    }

    func testOnlyExpectedURLTitlesMatch() {
        let titles = Self.allowedTitles(for: "Link Probe")
        XCTAssertTrue(titles.contains("在“Link Probe”中打开？"))
        XCTAssertTrue(titles.contains("Open in “Link Probe”?"))
        XCTAssertFalse(titles.contains("Open in “Other App”?"))
        XCTAssertFalse(titles.contains("“Link Probe” Would Like to Access Your Photos"))
    }

    func testHandleOpenAlert() throws {
        continueAfterFailure = false
        let name = ProcessInfo.processInfo.environment["LP_EXPECTED_APP_NAME"] ?? ""
        guard !name.isEmpty else {
            XCTFail("LP_EXPECTED_APP_NAME is required")
            return
        }
        let springboard = XCUIApplication(bundleIdentifier: "com.apple.springboard")
        let alert = springboard.alerts.firstMatch
        guard alert.waitForExistence(timeout: 2) else {
            print("LINK_PROBE_ALERT:not_present")
            return
        }
        let allowedTitles = Self.allowedTitles(for: name)
        let texts = Set([alert.label] + alert.staticTexts.allElementsBoundByIndex.map { $0.label })
        guard !texts.isDisjoint(with: allowedTitles) else {
            print("LINK_PROBE_ALERT:unrecognized")
            XCTFail("Refusing unrelated or unsupported alert: \(texts)")
            return
        }
        let buttons = alert.buttons.matching(NSPredicate(format: "label IN %@", ["Open", "打开"]))
        guard buttons.count == 1, buttons.firstMatch.isHittable else {
            XCTFail("Expected exactly one hittable Open button")
            return
        }
        let attachment = XCTAttachment(screenshot: springboard.screenshot())
        attachment.name = "URL confirmation before automatic tap"
        attachment.lifetime = .keepAlways
        add(attachment)
        buttons.firstMatch.tap()
        XCTAssertFalse(alert.waitForExistence(timeout: 0.5), "URL confirmation did not disappear")
        print("LINK_PROBE_ALERT:opened")
    }

    func testAssertUI() throws {
        continueAfterFailure = false
        let env = ProcessInfo.processInfo.environment
        guard let bundle = env["LP_BUNDLE_ID"], !bundle.isEmpty,
              let encoded = env["LP_UI_ASSERTIONS"], let data = encoded.data(using: .utf8),
              let assertions = try JSONSerialization.jsonObject(with: data) as? [[String: String]],
              !assertions.isEmpty else {
            XCTFail("Missing UI assertion configuration")
            return
        }
        let app = XCUIApplication(bundleIdentifier: bundle)
        // Do not launch/activate: doing so would alter the scenario being tested.
        let timeout = Double(env["LP_UI_TIMEOUT"] ?? "10") ?? 10
        let deadline = Date().addingTimeInterval(timeout)
        var checks: [[String: Any]] = []
        var passed = false
        repeat {
            checks = assertions.map { expected in
                let id = expected["id"] ?? ""
                let label = expected["label"] ?? ""
                let matches = app.descendants(matching: .any).matching(identifier: id)
                let count = matches.count
                let element = matches.firstMatch
                let actual = count == 1 ? element.label : ""
                let visible = count == 1 && element.isHittable
                return ["id": id, "expected_label": label, "actual_label": actual,
                        "matches": count, "hittable": visible,
                        "passed": visible && actual == label]
            }
            passed = app.state == .runningForeground && checks.allSatisfy { $0["passed"] as? Bool == true }
            if passed || Date() >= deadline { break }
            Thread.sleep(forTimeInterval: 0.2)
        } while true
        let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        attachment.name = "UI assertion screenshot"
        attachment.lifetime = .keepAlways
        add(attachment)
        if !passed {
            let tree = XCTAttachment(string: app.debugDescription)
            tree.name = "UI hierarchy on assertion failure"
            tree.lifetime = .keepAlways
            add(tree)
        }
        let result: [String: Any] = ["passed": passed, "app_foreground": app.state == .runningForeground,
                                     "checks": checks]
        let json = try JSONSerialization.data(withJSONObject: result, options: [.sortedKeys])
        print("LINK_PROBE_UI:" + String(data: json, encoding: .utf8)!)
        XCTAssertTrue(passed, "Visible UI does not match expectations; see structured result and attachments")
    }
}

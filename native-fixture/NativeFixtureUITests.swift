import XCTest

final class NativeFixtureUITests: XCTestCase {
    func testDummyInputScrollAndNativeAppSwitch() throws {
        continueAfterFailure = false
        let fixture = XCUIApplication()
        fixture.launch()
        XCTAssertTrue(fixture.staticTexts["fixture.marker"].waitForExistence(timeout: 10))
        let field = fixture.textFields["fixture.input"]
        field.tap()
        field.typeText("日本語ダミー123")
        XCTAssertEqual(fixture.staticTexts["fixture.proof.input"].label, "Input: 日本語ダミー123")
        fixture.buttons["fixture.tap"].tap()
        XCTAssertEqual(fixture.staticTexts["fixture.proof.taps"].label, "Taps: 1")
        let before = fixture.staticTexts["fixture.proof.row"].label
        fixture.scrollViews["fixture.scroll"].swipeUp()
        let changed = NSPredicate { _, _ in fixture.staticTexts["fixture.proof.row"].label != before }
        expectation(for: changed, evaluatedWith: nil)
        waitForExpectations(timeout: 5)

        // A simulator has no private account or device data. Only activate Settings;
        // never tap a setting, sign in, grant permissions, or change configuration.
        let settings = XCUIApplication(bundleIdentifier: "com.apple.Preferences")
        settings.launch()
        XCTAssertEqual(settings.state, .runningForeground)
        fixture.activate()
        XCTAssertEqual(fixture.state, .runningForeground)
        XCTAssertEqual(fixture.staticTexts["fixture.proof.input"].label, "Input: 日本語ダミー123")
        XCTAssertEqual(fixture.staticTexts["fixture.proof.taps"].label, "Taps: 1")
        fixture.terminate()
        XCTAssertNotEqual(fixture.state, .runningForeground)
    }
}

"""Run production page scripts in real macOS WKWebView. Not an iPhone test."""
import pathlib, subprocess, sys
source=pathlib.Path(sys.argv[1]); out=pathlib.Path(sys.argv[2]); out.mkdir(parents=True,exist_ok=True)
scripts=(source/'BrowserTools.swift').read_text().split('private enum BrowserScripts {',1)[1]
fixture=(pathlib.Path(__file__).parent/'fixture.html').read_text()
program=r'''
import Foundation
import WebKit
import AppKit

@main struct WebKitTrial {
    @MainActor static func main() async throws {
        _ = NSApplication.shared
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .nonPersistent()
        let web = WKWebView(frame: NSRect(x: 0,y: 0,width: 390,height: 844),configuration: configuration)
        let window = NSWindow(contentRect: web.frame,styleMask: [.titled],backing: .buffered,defer: false)
        window.contentView = web; window.makeKeyAndOrderFront(nil)
        let html = #"""
__FIXTURE_HTML__
"""#
        web.loadHTMLString(html,baseURL: URL(string: "https://fixture.invalid/"))
        for _ in 0..<200 { if !web.isLoading { break }; try await Task.sleep(for: .milliseconds(50)) }
        let world = WKContentWorld.world(name: "PhoneUseTools")
        func call(_ script: String,_ args: [String: Any]) async throws -> Any? {
            try await web.callAsyncJavaScript(script,arguments:args,in:nil,contentWorld:world)
        }
        func read(_ token: String) async throws -> [String: Any] {
            let result = try await call(BrowserScripts.read,["snapshotToken":token]) as! String
            return try JSONSerialization.jsonObject(with: Data(result.utf8)) as! [String: Any]
        }
        func require(_ condition: Bool,_ message: String) throws {
            if !condition { throw NSError(domain:"WebKitTrial",code:1,userInfo:[NSLocalizedDescriptionKey:message]) }
        }
        let first = try await read("first")
        try require(first["title"] as? String == "BROWSER-LOCAL-FIXTURE","Wrong fixture title")
        // WKWebView baseURL semantics must be measured, not assumed.
        try require((first["url"] as? String)?.hasPrefix("https://fixture.invalid/") == true,"Unexpected loadHTMLString URL: \(first["url"] ?? "nil")")
        let image = try await web.takeSnapshot(with:nil)
        try require(image.size.width > 0 && image.size.height > 0,"Empty screenshot")
        let elements = first["elements"] as! [[String: Any]]
        let field = elements.first { $0["label"] as? String == "Dummy input" }!
        let id = field["id"] as! Int
        _ = try await call(BrowserScripts.fill,["id":id,"token":"first","text":"DUMMY-20261102","personal":false])
        do {
            _ = try await call(BrowserScripts.fill,["id":id,"token":"first","text":"SECOND","personal":false])
            throw NSError(domain:"UnexpectedReplay",code:1)
        } catch { try require((error as NSError).domain != "UnexpectedReplay","Duplicate action was allowed") }
        let afterFill = try await read("after-fill")
        let current = (afterFill["elements"] as! [[String: Any]]).first { $0["id"] as? Int == id }
        try require(current?["value"] as? String == "DUMMY-20261102","Input result unknown")
        _ = try await call("window.scrollBy(0, innerHeight * 0.8); return true;",[:])
        try await Task.sleep(for: .milliseconds(350))
        let scrolled = try await read("after-scroll")
        try require((scrolled["text"] as? String)?.contains("SCROLLED") == true,"Scroll result not observed")
        // A page replacement must invalidate a previous observation, with no retry.
        web.loadHTMLString(html,baseURL: URL(string:"https://fixture.invalid/replaced"))
        for _ in 0..<200 { if !web.isLoading { break }; try await Task.sleep(for:.milliseconds(50)) }
        do {
            _ = try await call(BrowserScripts.fill,["id":id,"token":"after-scroll","text":"UNEXPECTED","personal":false])
            throw NSError(domain:"UnexpectedNavigationReplay",code:1)
        } catch { try require((error as NSError).domain != "UnexpectedNavigationReplay","Stale action allowed") }
        let value = try await web.evaluateJavaScript("document.querySelector('#dummy').value") as? String
        try require(value == "","Stale action mutated the new document")
        print("{\"runtime\":\"macOS WKWebView\",\"screenInMemory\":true,\"dummyFill\":true,\"scrollReadback\":true,\"duplicateRejected\":true,\"navigationRejectedWithoutResend\":true,\"deviceTested\":false}")
        web.stopLoading(); window.orderOut(nil)
    }
}
private enum BrowserScripts {
__PRODUCTION_SCRIPTS__
'''.replace('__FIXTURE_HTML__',fixture).replace('__PRODUCTION_SCRIPTS__',scripts)
swift=out/'main.swift'; swift.write_text(program)
subprocess.run(['swiftc','-parse-as-library',str(swift),'-o',str(out/'webkit-trial')],check=True)
subprocess.run([str(out/'webkit-trial')],check=True,timeout=90)

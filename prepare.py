"""Verify the public release, extract to a NEW directory, and apply a test-only safety overlay.
No install, signing, pairing, certificate creation or model calls.
"""
import argparse, hashlib, json, tarfile
from pathlib import Path, PurePosixPath

ROOT=Path(__file__).resolve().parent
LOCK=json.loads((ROOT/'upstream.lock.json').read_text(encoding='utf-8'))

def replace_once(text, old, new):
    if text.count(old)!=1: raise ValueError('Upstream source differs; refuse patch')
    return text.replace(old,new,1)

def prepare(archive, destination):
    archive=Path(archive).resolve(); destination=Path(destination).resolve()
    if destination.exists(): raise ValueError('Output already exists; no overwrite')
    if archive.stat().st_size!=LOCK['size'] or hashlib.sha256(archive.read_bytes()).hexdigest()!=LOCK['sha256']:
        raise ValueError('Release digest or size mismatch')
    with tarfile.open(archive) as t:
        members=t.getmembers()
        if sum(m.size for m in members)>200_000_000: raise ValueError('Archive too large')
        for m in members:
            path=PurePosixPath(m.name)
            if path.is_absolute() or '..' in path.parts or not path.parts or path.parts[0]!='app' or '\\' in m.name:
                raise ValueError('Unsafe archive path')
            if not (m.isfile() or m.isdir()): raise ValueError('Links or special files forbidden')
        destination.mkdir(parents=True)
        t.extractall(destination,filter='data')
    source=destination/'app/apps/ios/IPhoneUseRemote/Sources'
    p=source/'BrowserAgent.swift'; s=p.read_text(encoding='utf-8')
    anchor='    private func apply(_ decision: BrowserDecision, page: BrowserPage?) async throws {\n'
    s=replace_once(s,anchor,anchor+'''        // Owner's initial validation scope: never approve submission or arbitrary clicks.
        if [.click, .select, .site, .fillProfile].contains(decision.action) {
            throw BrowserToolError.actionFailed("検証版ではクリック・選択・送信・個人情報補完を実行しません")
        }
''')
    s=replace_once(s,'guard !configured.isEmpty else {','guard !configured.isEmpty || text == "LOCAL_FIXTURE" else {')
    s=replace_once(s,'            var staleRetries = 0','            let engine: any BrowserReasoning = goal == "LOCAL_FIXTURE" ? ValidationFixtureReasoning() : reasoning\n            var staleRetries = 0')
    s=replace_once(s,'try await reasoning.decide(goal: conversationGoal','try await engine.decide(goal: conversationGoal')
    s=replace_once(s,'if let checker = reasoning as? any BrowserCompletionChecking {','if let checker = engine as? any BrowserCompletionChecking {')
    s+='''
// Explicit deterministic acceptance fixture. This is NOT an AI model.
@MainActor
private final class ValidationFixtureReasoning: BrowserReasoning {
    func decide(goal: String, page: BrowserPage?, steps: [BrowserAgentStep], models: [ModelsPayload.Assist]) async throws -> BrowserDecision {
        guard let page, page.url.hasPrefix("https://fixture.invalid/"), page.title == "BROWSER-LOCAL-FIXTURE" else { throw BrowserToolError.humanRequired }
        guard let field = page.elements.first(where: { $0.label == "Dummy input" }) else { throw BrowserToolError.invalidResult }
        if !steps.contains(where: { $0.action == "fill" }) {
            guard field.value == "" else { throw BrowserToolError.humanRequired }
            return .init(action: .fill, explanation: "MOCK: ダミー入力", element: field.id, text: "DUMMY-20261102")
        }
        guard field.value == "DUMMY-20261102" else { throw BrowserToolError.invalidResult }
        if !steps.contains(where: { $0.action == "scroll" }) { return .init(action: .scroll, explanation: "MOCK: スクロール", text: "down") }
        guard page.text.contains("SCROLLED") else { throw BrowserToolError.invalidResult }
        return .init(action: .done, explanation: "MOCKダミー入力・スクロール・結果読取成功。AI推論と実機全体制御の成功ではありません。")
    }
}
'''
    p.write_text(s,encoding='utf-8')
    p=source/'BrowserTools.swift'; s=p.read_text(encoding='utf-8')
    s=replace_once(s,'globalThis.phoneUseSnapshot = { token, nodes, document, url: location.href, signatures:',
                   'globalThis.phoneUseSnapshot = { created: Date.now(), used: false, token, nodes, document, url: location.href, signatures:')
    s=replace_once(s,"e.innerText || ''].join('|');", "e.innerText || '', sensitive(e) ? '[sensitive]' : (e.value || '')].join('|');")
    s=replace_once(s,'if (!snapshot || snapshot.token !== token ||',
                   'if (!snapshot || snapshot.used || Date.now() - snapshot.created > 15000 || snapshot.token !== token ||')
    s=replace_once(s,"    element.scrollIntoView({ block: 'center' });\n    element.click();\n    return true;",
                   "    throw new Error('HUMAN: Clicks are disabled in the validation build.');")
    s=replace_once(s,'    element.focus();\n', '''    if (!(element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement)) throw new Error('HUMAN: Unsupported input.');
    if (element.value !== '') throw new Error('HUMAN: Existing input is never overwritten.');
    if (element.maxLength >= 0 && text.length > element.maxLength) throw new Error('HUMAN: Input exceeds maxlength.');
    snapshot.used = true;
    element.focus();
''')
    s=replace_once(s,"    if (!(element instanceof HTMLSelectElement)) throw new Error('This control is not a dropdown.');",
                   "    throw new Error('HUMAN: Selections are disabled in the validation build.');\n    if (!(element instanceof HTMLSelectElement)) throw new Error('This control is not a dropdown.');")
    p.write_text(s,encoding='utf-8')
    # No page data is sent to any model in this first validation build.
    p=source/'BrowserModelClient.swift'; s=p.read_text(encoding='utf-8')
    s=replace_once(s,'        self.session = session ?? URLSession(configuration: .ephemeral, delegate: BrowserModelRedirectGuard(), delegateQueue: nil)',
                   '''        let validationConfiguration = URLSessionConfiguration.ephemeral
        validationConfiguration.protocolClasses = [ValidationNoModelNetwork.self]
        self.session = URLSession(configuration: validationConfiguration, delegate: BrowserModelRedirectGuard(), delegateQueue: nil)''')
    s+='''
private final class ValidationNoModelNetwork: URLProtocol, @unchecked Sendable {
    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() { client?.urlProtocol(self, didFailWithError: URLError(.notConnectedToInternet)) }
    override func stopLoading() {}
}
'''
    p.write_text(s,encoding='utf-8')
    fixture=(ROOT/'fixture.html').read_text(encoding='utf-8')
    if '"""' in fixture: raise ValueError('Unexpected Swift delimiter in fixture')
    p=source/'Browser.swift';s=p.read_text(encoding='utf-8')
    s=replace_once(s,'    func open(_ input: String) {\n','''    func open(_ input: String) {
        if input.trimmingCharacters(in: .whitespacesAndNewlines) == "local-test" {
            error = nil; hasPage = true; loading = true
            let html = #"""
'''+fixture+'''
"""#
            webView.loadHTMLString(html, baseURL: URL(string: "https://fixture.invalid/"))
            return
        }
''')
    p.write_text(s,encoding='utf-8')
    harden_and_add_local_ai(source)
    (destination/'PREPARED.json').write_text(json.dumps({'release':LOCK['release'],'sha256':LOCK['sha256'],
        'variant':'remote-only','safetyOverlay':'no automated click/select/site/profile; one-use 15s input snapshot; no overwrite; maxlength',
        'cloudModelNetworkBlocked':True,'fixtureGoal':'LOCAL_FIXTURE','fixtureAddress':'local-test',
        'modelCallsExecuted':False,'nativeBuildExecuted':False,'installed':False},indent=2),encoding='utf-8')
    return source

def harden_and_add_local_ai(source):
    p=source/'BrowserAgent.swift'; s=p.read_text(encoding='utf-8')
    s=replace_once(s,'guard !configured.isEmpty || text == "LOCAL_FIXTURE" else {',
                   'guard !configured.isEmpty || text == "LOCAL_FIXTURE" || text.hasPrefix("LOCAL_AI:") else {')
    s=replace_once(s,'            let engine: any BrowserReasoning = goal == "LOCAL_FIXTURE" ? ValidationFixtureReasoning() : reasoning', '''            let engine: any BrowserReasoning
            if goal == "LOCAL_FIXTURE" {
                engine = ValidationFixtureReasoning()
                try await browser.waitUntilReady()
                let image = try await browser.webView.takeSnapshot(with: nil)
                try check(id)
                guard image.size.width > 0, image.size.height > 0 else { throw BrowserToolError.invalidResult }
                steps.append(.init(text: "MOCK: 画面をメモリ内で取得（ファイル保存なし）", action: "screen"))
            } else if goal.hasPrefix("LOCAL_AI:") {
                #if canImport(FoundationModels)
                if #available(iOS 26.0, *) { engine = LocalBrowserReasoning() }
                else { throw BrowserToolError.actionFailed("端末内AIにはiOS 26以降が必要です") }
                #else
                throw BrowserToolError.actionFailed("このビルドは端末内AIを利用できません")
                #endif
            } else { throw BrowserToolError.actionFailed("この検証版はLOCAL_FIXTUREまたはLOCAL_AI:を使ってください。外部AIは無効です。") }''')
    # Never extract browser cookies into a model context, including locally.
    start=s.index('                if let client = reasoning as? BrowserModelClient, let library {')
    end=s.index('                let decision = try await engine.decide',start)
    s=s[:start]+s[end:]
    s=replace_once(s,'                    try await apply(decision, page: page)', '''                    guard let observed = page else { throw BrowserToolError.invalidResult }
                    let latest = try await browser.readPage()
                    try check(id)
                    let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
                    guard latest.url == observed.url, latest.title == observed.title, latest.text == observed.text,
                          try encoder.encode(latest.elements) == encoder.encode(observed.elements) else { throw BrowserToolError.stalePage }
                    try await apply(decision, page: latest)''')
    s=replace_once(s,'                    guard staleRetries <= 3 else { throw BrowserToolError.stalePage }',
                   '                    throw BrowserToolError.stalePage // Stop; never automatically resend after a stale/unknown result.')
    s+='\n'+(ROOT/'LocalBrowserReasoning.swift').read_text(encoding='utf-8')
    p.write_text(s,encoding='utf-8')
    # An ephemeral browser: no cookie/storage export, import, automatic history or goal draft persistence.
    p=source/'BrowserTaskViews.swift'; s=p.read_text(encoding='utf-8')
    def replace_function(text, signature, body):
        begin=text.index(signature); opening=text.index('{',begin); depth=1; end=opening+1
        # Only used for fixed, audited upstream functions with balanced literal braces.
        while depth:
            if text[end]=='{': depth+=1
            elif text[end]=='}': depth-=1
            end+=1
        return text[:opening+1]+'\n'+body+'\n    '+text[end-1:]
    s=replace_function(s,'    private static func store(for id: UUID)', '        return .nonPersistent()')
    s=replace_function(s,'    private func bindVisits()', '        // No cookie observer, automatic history or storage capture in this build.')
    s=replace_function(s,'    func cookiesDidChange(in cookieStore:', '        // Cookie export disabled.')
    s=replace_function(s,'    func capture() async', '        // No cookies, localStorage, private screens or page text are saved.')
    s=replace_function(s,'    func restore() async', '        // Session import and automatic reopening disabled.')
    s=replace_once(s,'@AppStorage("browser.goalDraft.v1") private var draft = ""', '@State private var draft = ""')
    p.write_text(s,encoding='utf-8')

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('archive');a.add_argument('--output',required=True);args=a.parse_args()
    prepare(args.archive,args.output)
    print('Prepared verified remote-only source with validation guard. No native build or device installation performed.')

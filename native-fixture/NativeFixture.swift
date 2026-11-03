import SwiftUI

@main
struct NativeFixtureApp: App {
    var body: some Scene { WindowGroup { NativeFixtureView() } }
}

struct NativeFixtureView: View {
    @State private var input = ""
    @State private var taps = 0
    @State private var row = 0
    @FocusState private var editing: Bool

    var body: some View {
        VStack(spacing: 8) {
            Text("NATIVE-AGENT-FIXTURE-20261103")
                .font(.caption2)
                .accessibilityIdentifier("fixture.marker")
            Text("Input: " + input).font(.caption)
                .accessibilityIdentifier("fixture.proof.input")
            Text("Taps: \(taps)").accessibilityIdentifier("fixture.proof.taps")
            Text("Row: \(row)").accessibilityIdentifier("fixture.proof.row")
            TextField("Dummy input", text: $input)
                .textFieldStyle(.roundedBorder)
                .autocorrectionDisabled()
                .textInputAutocapitalization(.never)
                .focused($editing)
                .accessibilityIdentifier("fixture.input")
            Button("Increment test counter") { editing = false; taps += 1 }
                .accessibilityIdentifier("fixture.tap")
            ScrollView {
                LazyVStack(spacing: 0) {
                    ForEach(0..<80) { index in
                        Text("Synthetic row \(index)")
                            .frame(maxWidth: .infinity, minHeight: 64)
                            .id(index)
                    }
                }
            }
            .onScrollGeometryChange(for: Int.self) { geometry in
                Int(max(0, geometry.contentOffset.y) / 64)
            } action: { _, visibleRow in
                row = visibleRow
            }
            .accessibilityIdentifier("fixture.scroll")
        }.padding()
    }
}

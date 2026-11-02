import MachineARKit
import SwiftUI

/// Example integration: copy generated machine.usdz, machine.json, and
/// animation_spec.json into your app's Copy Bundle Resources build phase.
struct TwoStrokeDemoView: View {
    @StateObject private var session = MachineSession()
    @State private var model: MachineAsset?
    @State private var assetError: String?

    var body: some View {
        VStack(spacing: 12) {
            ZStack {
                if let model {
                    MachineARView(session: session, asset: model)
                    MachineAnnotationOverlay(session: session)
                } else {
                    ContentUnavailableView("Model unavailable", systemImage: "cube.transparent",
                                           description: Text(assetError ?? "Copy generated assets to the app bundle"))
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)

            if let error = session.errorText {
                Text(error).foregroundStyle(.red).font(.footnote)
            }
            HStack {
                Button(session.isPlaying ? "Pause" : "Play") {
                    session.isPlaying ? session.stop() : session.play()
                }
                .disabled(!session.ready || session.exploded)
                Button(session.exploded ? "Assemble" : "Explode") {
                    session.toggleExploded()
                }
                .disabled(!session.ready)
                Button("Reset") { session.reset() }
                    .disabled(!session.ready)
            }
            HStack {
                Text("RPM \(Int(session.rpm))")
                Slider(value: $session.rpm, in: 0...6000, step: 100)
                    .disabled(!session.ready || session.exploded)
            }
            HStack {
                Text("Crank angle \(Int(session.angleDegrees))°")
                Slider(value: Binding(get: { session.angleDegrees }, set: {
                    session.stop()
                    session.setAngle(degrees: $0)
                }), in: 0...360)
                .disabled(!session.ready || session.exploded)
            }
        }
        .padding()
        .task { loadAsset() }
    }

    private func loadAsset() {
        guard let usd = Bundle.main.url(forResource: "machine", withExtension: "usdz"),
              let meta = Bundle.main.url(forResource: "machine", withExtension: "json"),
              let anim = Bundle.main.url(forResource: "animation_spec", withExtension: "json") else {
            assetError = "Missing machine.usdz, machine.json, or animation_spec.json"
            return
        }
        do {
            model = try MachineAsset(modelURL: usd, metadataURL: meta, animationURL: anim)
        } catch {
            assetError = error.localizedDescription
        }
    }
}

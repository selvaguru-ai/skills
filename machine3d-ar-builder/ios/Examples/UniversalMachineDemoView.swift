import MachineARKit
import SwiftUI

/// Demonstration of the generic RealityKit runtime with any v1 or v2 machine.
/// Ensure machine.usdz, machine.json and animation_spec.json are app resources.
struct UniversalMachineDemoView: View {
    @StateObject private var session = MachineSession()
    @State private var model: MachineAsset?
    @State private var assetError: String?

    var body: some View {
        VStack(spacing: 10) {
            ZStack {
                if let model {
                    MachineARView(session: session, asset: model)
                    MachineAnnotationOverlay(session: session)
                } else {
                    ContentUnavailableView("Machine unavailable", systemImage: "cube.transparent",
                                           description: Text(assetError ?? "Bundle machine assets first"))
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
                Text("Speed \(Int(session.rpm)) RPM")
                Slider(value: $session.rpm, in: 0...max(1, session.maxRPM))
                    .disabled(!session.ready || session.exploded)
            }
            HStack {
                Text("Cycle \(Int(session.angleDegrees))°")
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
        guard let modelURL = Bundle.main.url(forResource: "machine", withExtension: "usdz"),
              let metadataURL = Bundle.main.url(forResource: "machine", withExtension: "json"),
              let animationURL = Bundle.main.url(forResource: "animation_spec", withExtension: "json") else {
            assetError = "Missing machine.usdz, machine.json, or animation_spec.json"
            return
        }
        do {
            model = try MachineAsset(modelURL: modelURL, metadataURL: metadataURL,
                                     animationURL: animationURL)
        } catch {
            assetError = error.localizedDescription
        }
    }
}

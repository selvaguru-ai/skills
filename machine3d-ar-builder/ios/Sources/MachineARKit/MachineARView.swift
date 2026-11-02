import ARKit
import RealityKit
import SwiftUI
import UIKit

/// Add MachineARView(session: session, asset: asset) to an iOS SwiftUI screen.
/// On AR-capable hardware the model anchors to a horizontal plane.
/// In Simulator/non-AR devices it appears in a camera-free studio preview.
public struct MachineARView: UIViewRepresentable {
    @ObservedObject public var session: MachineSession
    public let asset: MachineAsset

    public init(session: MachineSession, asset: MachineAsset) {
        self.session = session
        self.asset = asset
    }

    public func makeCoordinator() -> Coordinator { Coordinator(session: session) }

    public func makeUIView(context: Context) -> ARView {
        let supportsAR = ARWorldTrackingConfiguration.isSupported
        let view = ARView(frame: .zero, cameraMode: supportsAR ? .ar : .nonAR,
                          automaticallyConfigureSession: false)
        view.environment.background = supportsAR ? .cameraFeed() : .color(.darkGray)
        context.coordinator.view = view
        let tap = UITapGestureRecognizer(target: context.coordinator, action: #selector(Coordinator.didTap(_:)))
        view.addGestureRecognizer(tap)

        if supportsAR {
            let configuration = ARWorldTrackingConfiguration()
            configuration.planeDetection = [.horizontal]
            view.session.run(configuration)
        }
        let anchor: AnchorEntity
        if supportsAR {
            anchor = AnchorEntity(plane: .horizontal)
        } else {
            anchor = AnchorEntity(world: SIMD3<Float>(0, -0.05, -0.65))
        }
        view.scene.addAnchor(anchor)
        do {
            try session.load(asset: asset, view: view, anchor: anchor)
        } catch {
            session.report(error)
        }
        return view
    }

    public func updateUIView(_ uiView: ARView, context: Context) {}

    public final class Coordinator: NSObject {
        private let session: MachineSession
        weak var view: ARView?

        init(session: MachineSession) { self.session = session }

        @objc func didTap(_ recognizer: UITapGestureRecognizer) {
            guard let view, let hit = view.entity(at: recognizer.location(in: view)) else { return }
            session.select(hit: hit)
        }
    }
}

/// Screen-space annotation anchored to the selected 3D component's projected position.
public struct MachineAnnotationOverlay: View {
    @ObservedObject public var session: MachineSession

    public init(session: MachineSession) { self.session = session }

    public var body: some View {
        GeometryReader { proxy in
            if let component = session.selectedComponent,
               let point = session.annotationPoint {
                VStack(spacing: 0) {
                    VStack(alignment: .leading, spacing: 3) {
                        Text(component.name).font(.headline)
                        Text(component.description).font(.caption)
                    }
                    .padding(10)
                    .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 12))
                    .frame(maxWidth: 260)
                    Image(systemName: "arrow.down")
                        .foregroundStyle(.primary)
                }
                .position(x: min(max(point.x, 130), max(130, proxy.size.width - 130)),
                          y: min(max(point.y - 62, 70), max(70, proxy.size.height - 80)))
                .allowsHitTesting(false)
            }
        }
        .accessibilityElement(children: .combine)
    }
}

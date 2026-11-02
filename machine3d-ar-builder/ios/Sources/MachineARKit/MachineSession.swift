import Combine
import Foundation
import QuartzCore
import RealityKit
import simd

/// Single mechanism and UI state. Does not require a server or user reference images.
@MainActor
public final class MachineSession: NSObject, ObservableObject {
    @Published public private(set) var isPlaying = false
    @Published public private(set) var selectedComponent: MachineComponent?
    @Published public private(set) var annotationPoint: CGPoint?
    @Published public private(set) var exploded = false
    @Published public private(set) var errorText: String?
    @Published public private(set) var ready = false
    @Published public var rpm: Double = 600 {
        didSet {
            let limit = asset?.animation.maxRPM ?? 6000
            let bounded = min(max(rpm, 0), limit)
            if bounded != rpm { rpm = bounded }
        }
    }
    @Published public var angleDegrees: Double = 0 {
        didSet {
            let bounded = min(max(angleDegrees, 0), 360)
            if angleDegrees != bounded { angleDegrees = bounded }
        }
    }

    public var maxRPM: Double { asset?.animation.maxRPM ?? 6000 }

    private var asset: MachineAsset?
    private weak var sceneView: ARView?
    private var machineRoot: Entity?
    private var motion: (any MachineMotionController)?
    private var displayLink: CADisplayLink?
    private var angle: Float = 0
    private var selectedEntity: Entity?
    private var explodedTransforms: [(Entity, Transform)] = []

    public func load(asset: MachineAsset, view: ARView, anchor: AnchorEntity) throws {
        stop()
        self.asset = asset
        sceneView = view
        let model = try Entity.load(contentsOf: asset.modelURL)
        model.name = "LoadedMachine"
        if asset.animation.schemaVersion == 1 {
            model.position.y = 0.065 // Legacy engine stand correction
        }
        for entry in asset.metadata.components {
            // Selection hits actual ModelEntity children; then walks up to named parts.
            if let entity = model.findEntity(named: entry.entityName) {
                installCollisionTargets(on: entity)
            }
        }
        let controller: any MachineMotionController
        if asset.animation.mechanism == "crank_slider" {
            controller = try CrankSliderController(root: model, spec: asset.animation)
        } else {
            controller = try GenericJointController(root: model, spec: asset.animation)
        }
        anchor.addChild(model)
        machineRoot = model
        motion = controller
        rpm = asset.animation.defaultRPM
        ready = true
        setAngle(degrees: 0)
    }

    private func installCollisionTargets(on entity: Entity) {
        if let mesh = entity as? ModelEntity {
            mesh.generateCollisionShapes(recursive: false)
            mesh.components.set(InputTargetComponent())
        }
        for child in entity.children { installCollisionTargets(on: child) }
    }

    public func report(_ error: Error) {
        errorText = error.localizedDescription
        ready = false
        stop()
    }

    public func select(hit: Entity) {
        guard let asset else { return }
        var next: Entity? = hit
        while let entity = next {
            if let component = asset.metadata.components.first(where: { $0.entityName == entity.name }) {
                selectedComponent = component
                selectedEntity = entity
                updateAnnotation()
                return
            }
            next = entity.parent
        }
        selectedComponent = nil
        selectedEntity = nil
        annotationPoint = nil
    }

    private func updateAnnotation() {
        guard let view = sceneView, let entity = selectedEntity else {
            annotationPoint = nil
            return
        }
        annotationPoint = view.project(entity.position(relativeTo: nil))
    }

    public func play() {
        guard ready, !exploded, !isPlaying else { return }
        isPlaying = true
        let link = CADisplayLink(target: self, selector: #selector(tick(_:)))
        link.add(to: .main, forMode: .common)
        displayLink = link
    }

    public func stop() {
        displayLink?.invalidate()
        displayLink = nil
        isPlaying = false
    }

    public func setAngle(degrees: Double) {
        guard !exploded else { return }
        angle = Float(degrees * .pi / 180)
        angleDegrees = degrees
        motion?.apply(angle: angle)
        updateAnnotation()
    }

    @objc private func tick(_ link: CADisplayLink) {
        guard isPlaying else { return }
        let step = min(max(link.targetTimestamp - link.timestamp, 0), 0.05)
        angle = (angle + Float(step * rpm / 60 * 2 * .pi))
            .truncatingRemainder(dividingBy: 2 * .pi)
        angleDegrees = Double(angle) * 180 / .pi
        motion?.apply(angle: angle)
        updateAnnotation()
    }

    public func toggleExploded() {
        guard let root = machineRoot else { return }
        if !exploded {
            stop()
            // Generic educational offsets, not manufacturer-specific disassembly paths.
            let topLevelNames = asset?.metadata.components.map(\.entityName) ?? []
            explodedTransforms = []
            for (index, name) in topLevelNames.enumerated() {
                guard let entity = root.findEntity(named: name) else { continue }
                explodedTransforms.append((entity, entity.transform))
                entity.position += SIMD3<Float>(Float((index % 3) - 1) * 0.10,
                                                 Float(index / 3) * 0.07,
                                                 Float(index % 2) * 0.065)
            }
        } else {
            for (entity, previous) in explodedTransforms { entity.transform = previous }
            explodedTransforms.removeAll()
            motion?.apply(angle: angle)
        }
        exploded.toggle()
        updateAnnotation()
    }

    public func reset() {
        stop()
        if exploded { toggleExploded() }
        setAngle(degrees: 0)
    }

    deinit { displayLink?.invalidate() }
}

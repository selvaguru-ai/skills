import Foundation
import RealityKit
import simd

/// Common animation abstraction; a machine is not assumed to contain a crankshaft.
@MainActor
public protocol MachineMotionController: AnyObject {
    func apply(angle: Float)
}

/// Interprets schema-v2 generic rotation, translation and oscillation joints.
/// v2 axis values are Blender Z-up coordinates; USD export maps Z->Y and Y->-Z.
@MainActor
public final class GenericJointController: MachineMotionController {
    private struct BoundJoint {
        let entity: Entity
        let spec: MachineJointSpec
        let axis: SIMD3<Float>
        let original: Transform
    }
    private let joints: [BoundJoint]

    public init(root: Entity, spec: MachineAnimationSpec) throws {
        var bound: [BoundJoint] = []
        for joint in spec.joints ?? [] {
            guard let entity = root.findEntity(named: joint.entity) else {
                throw MachineAssetError.missingEntity(joint.entity)
            }
            // The USD exporter should map Blender (x,y,z) to RealityKit (x,z,-y).
            let axis = SIMD3<Float>(joint.axis[0], joint.axis[2], -joint.axis[1])
            let magnitude = simd_length(axis)
            guard magnitude > 0 else { throw MachineAssetError.invalidContract }
            bound.append(BoundJoint(entity: entity, spec: joint,
                                    axis: axis / magnitude, original: entity.transform))
        }
        self.joints = bound
    }

    public func apply(angle: Float) {
        for bound in joints {
            let j = bound.spec
            let phase = (j.ratio ?? 1) * angle + (j.phase ?? 0)
            var transform = bound.original
            let initialPhase = j.phase ?? 0
            // The exported USDZ rest pose is Blender frame 1 (cycle angle 0),
            // so apply motion DELTA relative to that pose to avoid double phases.
            switch j.type {
            case "rotate":
                let delta = (j.ratio ?? 1) * angle
                transform.rotation = transform.rotation * simd_quatf(angle: delta, axis: bound.axis)
            case "oscillate":
                let delta = (j.amplitude ?? 0) * (sin(phase) - sin(initialPhase))
                transform.rotation = transform.rotation * simd_quatf(angle: delta, axis: bound.axis)
            case "slide":
                let delta = (j.amplitude ?? 0) * (sin(phase) - sin(initialPhase))
                transform.translation += bound.axis * delta
            default: break
            }
            bound.entity.transform = transform
        }
    }
}

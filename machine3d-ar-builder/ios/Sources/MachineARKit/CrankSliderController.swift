import Foundation
import RealityKit
import simd

/// Matches Blender's analytical mechanism after Z-up -> Y-up USD export.
/// NOTE: verify pivots and local axes on a real iOS device when changing exporter settings.
@MainActor
public final class CrankSliderController: MachineMotionController {
    private let piston: Entity
    private let crankshaft: Entity
    private let rod: Entity
    private let radius: Float
    private let length: Float

    public init(root: Entity, spec: MachineAnimationSpec) throws {
        guard let targets = spec.entities,
              let radiusValue = spec.crankRadius, let lengthValue = spec.connectingRodLength else {
            throw MachineAssetError.invalidContract
        }
        guard let p = root.findEntity(named: targets.piston) else {
            throw MachineAssetError.missingEntity(targets.piston)
        }
        guard let c = root.findEntity(named: targets.crankshaft) else {
            throw MachineAssetError.missingEntity(targets.crankshaft)
        }
        guard let r = root.findEntity(named: targets.connectingRod) else {
            throw MachineAssetError.missingEntity(targets.connectingRod)
        }
        piston = p
        crankshaft = c
        rod = r
        radius = Float(radiusValue)
        length = Float(lengthValue)
    }

    /// theta=0 is top dead center; one revolution completes one 2-stroke cycle.
    public func apply(angle theta: Float) {
        let sx = radius * sin(theta)
        let cz = radius * cos(theta)
        let vertical = sqrt(max(0, length * length - sx * sx))
        let wristY = cz + vertical
        let axis = SIMD3<Float>(0, 0, -1)

        crankshaft.orientation = simd_quatf(angle: theta, axis: axis)
        piston.position = SIMD3<Float>(0, wristY, 0)
        rod.position = SIMD3<Float>(sx / 2, (cz + wristY) / 2, 0)
        rod.orientation = simd_quatf(angle: atan2(-sx, vertical), axis: axis)
    }
}

import Foundation

/// Schema v1 is the detailed two-stroke reference implementation.
/// Schema v2 is a generic machine blueprint with independently animatable components.
public struct MachineComponent: Codable, Identifiable, Equatable {
    public let id: String
    public let name: String
    public let description: String
    public let movable: Bool
    public let entityName: String
}

public struct MachineMetadata: Codable {
    public let schemaVersion: Int
    public let id: String
    public let displayName: String
    public let machineType: String
    public let accuracy: String
    public let components: [MachineComponent]
}

public struct MachineJointSpec: Codable {
    public let entity: String
    public let type: String
    public let axis: [Float]
    public let ratio: Float?
    public let phase: Float?
    public let amplitude: Float?
    public let offset: Float?
}

public struct MachineAnimationSpec: Codable {
    public struct Entities: Codable {
        public let piston: String
        public let crankshaft: String
        public let connectingRod: String
    }

    public let schemaVersion: Int
    public let machineId: String
    public let mechanism: String
    public let crankRadius: Double?
    public let connectingRodLength: Double?
    public let wristToCrown: Double?
    public let defaultRPM: Double
    public let maxRPM: Double
    public let entities: Entities?
    public let joints: [MachineJointSpec]?
}

public struct MachineAsset {
    public let modelURL: URL
    public let metadata: MachineMetadata
    public let animation: MachineAnimationSpec

    public init(modelURL: URL, metadataURL: URL, animationURL: URL) throws {
        self.modelURL = modelURL
        self.metadata = try JSONDecoder().decode(MachineMetadata.self, from: Data(contentsOf: metadataURL))
        self.animation = try JSONDecoder().decode(MachineAnimationSpec.self, from: Data(contentsOf: animationURL))
        guard (metadata.schemaVersion == 1 || metadata.schemaVersion == 2),
              metadata.schemaVersion == animation.schemaVersion,
              metadata.id == animation.machineId,
              !metadata.components.isEmpty,
              animation.maxRPM > 0,
              animation.defaultRPM >= 0,
              animation.defaultRPM <= animation.maxRPM else {
            throw MachineAssetError.invalidContract
        }
        if animation.schemaVersion == 1 {
            guard animation.mechanism == "crank_slider",
                  let radius = animation.crankRadius,
                  let length = animation.connectingRodLength,
                  radius > 0, length > radius,
                  animation.entities != nil else {
                throw MachineAssetError.invalidContract
            }
        } else {
            guard animation.mechanism == "generic_joints",
                  let joints = animation.joints else {
                throw MachineAssetError.invalidContract
            }
            let ids = Set(metadata.components.map(\.entityName))
            for joint in joints {
                guard ids.contains(joint.entity),
                      ["rotate", "slide", "oscillate"].contains(joint.type),
                      joint.axis.count == 3,
                      joint.axis.allSatisfy({ $0.isFinite }),
                      joint.axis.reduce(0) { $0 + $1 * $1 } > 0 else {
                    throw MachineAssetError.invalidContract
                }
            }
        }
    }
}

public enum MachineAssetError: LocalizedError {
    case invalidContract
    case missingEntity(String)

    public var errorDescription: String? {
        switch self {
        case .invalidContract: return "Unsupported or invalid machine asset contract"
        case .missingEntity(let name): return "USDZ is missing required entity: \(name)"
        }
    }
}

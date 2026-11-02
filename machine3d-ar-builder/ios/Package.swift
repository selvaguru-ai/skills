// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "MachineARKit",
    platforms: [.iOS(.v17)],
    products: [.library(name: "MachineARKit", targets: ["MachineARKit"])],
    targets: [.target(name: "MachineARKit", path: "Sources/MachineARKit")]
)

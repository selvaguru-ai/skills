# MachineARKit — universal SwiftUI / RealityKit starter

This is a reusable iOS 17+ Swift package for multiple machine families, not a two-stroke-only viewer.

Supports:
- Schema v1 dedicated crank-slider animation (two-stroke engine).
- Schema v2 generic joint animation (rotation, oscillation, sliding).
- Named component hit-testing, selection/labels, play/pause/RPM/cycle slider and exploded display.

Copy `ios/Examples/UniversalMachineDemoView.swift` into your app and package `machine.usdz`, `machine.json`, `animation_spec.json`. To ship multiple machines at once, assign per-machine bundle directories or asset names and construct `MachineAsset` with appropriate URLs.

**Not yet verified on iPhone:** Exported USD naming/pivots, AR placement and full RealityKit compilation. Run Xcode tests on an actual device; don't assume `swiftc -frontend -parse` checks framework semantics.

# Integrate any generated machine into an iOS AR application

Requirements: macOS Xcode, iOS 17+, RealityKit, ARKit, and an AR-capable iPhone for tracked tabletop placement.

1. Build a model with `python3 -m machine3d build --prompt "electric motor" --out output/electric_motor` or `--spec /path/blueprint.json`.
2. Add `ios/` as a local Swift package (`File > Add Package Dependencies > Add Local...`).
3. Add the generated `machine.usdz`, `machine.json` and `animation_spec.json` to the iOS target. Give the imported files unique bundle paths if you ship several models; the demo's fixed names target one sample at a time.
4. Add `NSCameraUsageDescription` explaining that the camera places 3D machines in AR.
5. Copy `ios/Examples/UniversalMachineDemoView.swift` into the app for sample playback, RPM and component selection.
6. On a real iPhone verify USDZ imports as separate named entities, animations use the correct axes and pivots, taps hit the intended parts, and anchors stabilize. Studio fallback is available on non-AR/simulator devices.

## Animation selection

- **Two-stroke engine v1** → `CrankSliderController` (analytical kinematics).
- **Any v2 machine blueprint** → `GenericJointController` (rotation, slide, oscillation).
- **Advanced new mechanism** → implement and test a new controller in the Swift package, version its animation spec, and match Blender preview behavior.

The exported USDZ is **nonanimated rest pose**; RealityKit executes motions at runtime. ARKit is responsible for environment tracking, not moving pistons/rotors. Current animated components use simple local rotations/displacements; avoid assuming realistic force dynamics, valve timing or collision.

## Known integration risks

Blender's USD export may change entity hierarchy or coordinate basis across versions. Validate that object pivots survive on a physical iPhone. `GenericJointController` maps Blender `(x,y,z)` axes to RealityKit `(x,z,-y)` under expected USD Y-up orientation. Confirm signs/handedness before release. Both Swift syntax parsing and Python tests can run outside Xcode, but full Apple framework typechecking and on-device runtime tests must occur on your Mac.

The built-in ARView currently plane-anchors automatically when a plane is detected; a production app should add explicit user placement, reticles and success/failure feedback, especially when integrating with an existing AR app.

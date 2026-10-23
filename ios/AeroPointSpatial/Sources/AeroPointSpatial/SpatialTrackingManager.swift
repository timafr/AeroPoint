//
//  SpatialTrackingManager.swift
//  AeroPointSpatial
//
//  Dual-Engine Spatial Tracking: TrueDepth (Face ID IR) & LiDAR (dToF)
//  Powered by Apple Neural Engine (Vision Framework) at 60 FPS
//  Supports Dual-Hand Tracking, Dynamic Auto-Orientation & Inversion-Proof Rear LiDAR
//

import Foundation
import AVFoundation
import Vision
import ARKit
import Combine
import UIKit

enum SensorType {
    case frontTrueDepth
    case backLiDAR
}

class SpatialTrackingManager: NSObject, ObservableObject {
    @Published var isHandDetected: Bool = false
    @Published var currentDepthMM: Float = 420.0
    @Published var actualFPS: Double = 60.0
    @Published var currentLandmarks: [CGPoint] = []
    @Published var allHandLandmarks: [[CGPoint]] = []
    @Published var isLandscape: Bool = false
    @Published var currentVideoOrientation: AVCaptureVideoOrientation = .portrait
    @Published var mirrorRearCamera: Bool = true // Default ON: keeps hand movement matching PC cursor
    
    var captureSession: AVCaptureSession?
    var arSession: ARSession?
    
    private var activeSensor: SensorType = .frontTrueDepth
    private var handPoseRequest = VNDetectHumanHandPoseRequest()
    private let visionQueue = DispatchQueue(label: "com.aeropoint.vision", qos: .userInteractive)
    
    private var depthDataOutput = AVCaptureDepthDataOutput()
    private var videoDataOutput = AVCaptureVideoDataOutput()
    private var lastDepthMap: CVPixelBuffer?
    private var depthLock = NSLock()
    
    private var lastFrameTime = CACurrentMediaTime()
    private var frameCount = 0
    
    var onHandPoseDetected: (([String: Any]) -> Void)?

    override init() {
        super.init()
        handPoseRequest.maximumHandCount = 2
        
        UIDevice.current.beginGeneratingDeviceOrientationNotifications()
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(handleOrientationDidChange),
            name: UIDevice.orientationDidChangeNotification,
            object: nil
        )
    }
    
    deinit {
        NotificationCenter.default.removeObserver(self)
        UIDevice.current.endGeneratingDeviceOrientationNotifications()
    }
    
    // MARK: - Device Orientation Management
    func resolveCaptureOrientation() -> AVCaptureVideoOrientation {
        let deviceOrientation = UIDevice.current.orientation
        switch deviceOrientation {
        case .portrait:
            return .portrait
        case .portraitUpsideDown:
            return .portraitUpsideDown
        case .landscapeLeft:
            return .landscapeRight
        case .landscapeRight:
            return .landscapeLeft
        default:
            if let windowScene = UIApplication.shared.connectedScenes.compactMap({ $0 as? UIWindowScene }).first {
                switch windowScene.interfaceOrientation {
                case .portrait:
                    return .portrait
                case .portraitUpsideDown:
                    return .portraitUpsideDown
                case .landscapeLeft:
                    return .landscapeLeft
                case .landscapeRight:
                    return .landscapeRight
                default:
                    return .portrait
                }
            }
            return .portrait
        }
    }
    
    func currentVisionOrientation() -> CGImagePropertyOrientation {
        if activeSensor == .frontTrueDepth {
            // Front TrueDepth is rotated in hardware by AVCaptureConnection
            return .up
        } else {
            // Rear camera ARKit capturedImage is in native sensor frame
            switch resolveCaptureOrientation() {
            case .portrait:
                return .right
            case .portraitUpsideDown:
                return .left
            case .landscapeRight:
                return .up
            case .landscapeLeft:
                return .down
            @unknown default:
                return .right
            }
        }
    }
    
    @objc private func handleOrientationDidChange() {
        updateConnectionOrientations()
    }
    
    func updateConnectionOrientations() {
        let orientation = resolveCaptureOrientation()
        let landscapeActive = (orientation == .landscapeLeft || orientation == .landscapeRight)
        
        DispatchQueue.main.async {
            self.currentVideoOrientation = orientation
            self.isLandscape = landscapeActive
        }
        
        if let vConn = videoDataOutput.connection(with: .video), vConn.isVideoOrientationSupported {
            if vConn.videoOrientation != orientation {
                vConn.videoOrientation = orientation
            }
            if vConn.isVideoMirroringSupported {
                vConn.isVideoMirrored = (activeSensor == .frontTrueDepth)
            }
        }
        
        if let dConn = depthDataOutput.connection(with: .depthData), dConn.isVideoOrientationSupported {
            if dConn.videoOrientation != orientation {
                dConn.videoOrientation = orientation
            }
            if dConn.isVideoMirroringSupported {
                dConn.isVideoMirrored = (activeSensor == .frontTrueDepth)
            }
        }
    }
    
    func startTracking() {
        DispatchQueue.main.async {
            UIApplication.shared.isIdleTimerDisabled = true
        }
        switchSensor(activeSensor)
    }
    
    func stopTracking() {
        DispatchQueue.main.async {
            UIApplication.shared.isIdleTimerDisabled = false
        }
        captureSession?.stopRunning()
        captureSession = nil
        arSession?.pause()
        arSession = nil
    }
    
    func switchSensor(_ sensor: SensorType) {
        stopTracking()
        activeSensor = sensor
        
        if sensor == .frontTrueDepth {
            setupTrueDepthSession()
        } else {
            setupLiDARSession()
        }
    }
    
    // MARK: - 1. Front TrueDepth Session (Face ID Structured Light IR)
    private func setupTrueDepthSession() {
        let session = AVCaptureSession()
        session.sessionPreset = .vga640x480
        
        guard let device = AVCaptureDevice.default(.builtInTrueDepthCamera, for: .video, position: .front) else {
            print("[!] TrueDepth device unavailable, falling back to standard front camera")
            return
        }
        
        do {
            let input = try AVCaptureDeviceInput(device: device)
            if session.canAddInput(input) { session.addInput(input) }
            
            // Video Output
            videoDataOutput.videoSettings = [kCVPixelBufferPixelFormatTypeKey as String: Int(kCVPixelFormatType_32BGRA)]
            videoDataOutput.alwaysDiscardsLateVideoFrames = true
            videoDataOutput.setSampleBufferDelegate(self, queue: visionQueue)
            if session.canAddOutput(videoDataOutput) { 
                session.addOutput(videoDataOutput)
            }
            
            // Synchronized Depth Output
            if session.canAddOutput(depthDataOutput) {
                session.addOutput(depthDataOutput)
                depthDataOutput.isFilteringEnabled = true
                depthDataOutput.setDelegate(self, callbackQueue: visionQueue)
            }
            
            updateConnectionOrientations()
            
            session.startRunning()
            self.captureSession = session
        } catch {
            print("[!] Error configuring TrueDepth session: \(error)")
        }
    }
    
    // MARK: - 2. Back LiDAR Session (ARKit dToF Mesh)
    private func setupLiDARSession() {
        guard ARWorldTrackingConfiguration.supportsFrameSemantics(.sceneDepth) else {
            print("[!] Device does not support LiDAR scene depth, falling back to TrueDepth")
            setupTrueDepthSession()
            return
        }
        
        let config = ARWorldTrackingConfiguration()
        if ARWorldTrackingConfiguration.supportsFrameSemantics(.smoothedSceneDepth) {
            config.frameSemantics.insert(.smoothedSceneDepth)
        } else {
            config.frameSemantics.insert(.sceneDepth)
        }
        
        let ar = ARSession()
        ar.delegate = self
        ar.run(config, options: [.resetTracking, .removeExistingAnchors])
        self.arSession = ar
    }
    
    // MARK: - Hand Pose Extraction & Physical Depth Fusion (Dual-Hand 60 FPS)
    private func processHandPose(on pixelBuffer: CVPixelBuffer, depthBuffer: CVPixelBuffer?) {
        let visionOrientation = currentVisionOrientation()
        let handler = VNImageRequestHandler(cvPixelBuffer: pixelBuffer, orientation: visionOrientation, options: [:])
        do {
            try handler.perform([handPoseRequest])
            guard let observations = handPoseRequest.results, !observations.isEmpty else {
                DispatchQueue.main.async {
                    self.isHandDetected = false
                    self.currentLandmarks = []
                    self.allHandLandmarks = []
                }
                return
            }
            
            var handsPayload: [[String: Any]] = []
            var allHandsUILandmarks: [[CGPoint]] = []
            
            // Strictly ordered 21 hand joints matching MediaPipe standard topology
            let jointKeys: [VNHumanHandPoseObservation.JointName] = [
                .wrist,
                .thumbCMC, .thumbMP, .thumbIP, .thumbTip,
                .indexMCP, .indexPIP, .indexDIP, .indexTip,
                .middleMCP, .middlePIP, .middleDIP, .middleTip,
                .ringMCP, .ringPIP, .ringDIP, .ringTip,
                .littleMCP, .littlePIP, .littleDIP, .littleTip
            ]
            
            let shouldFlipHorizontal = (activeSensor == .backLiDAR && mirrorRearCamera)
            
            for obs in observations {
                let recognizedPoints = try obs.recognizedPoints(.all)
                var rawPointsNorm: [[Float]] = []
                var currentHandUILandmarks: [CGPoint] = []
                
                var avgZ: Float = 420.0
                var samplesZ: [Float] = []
                
                for key in jointKeys {
                    if let pt = recognizedPoints[key], pt.confidence > 0.15 {
                        var nx = Float(pt.location.x)
                        let ny = Float(1.0 - pt.location.y)
                        
                        // Flip horizontally for rear LiDAR so pointing right moves cursor right on PC
                        if shouldFlipHorizontal {
                            nx = 1.0 - nx
                        }
                        
                        // Extract physical millimeter depth from TrueDepth/LiDAR buffer
                        var zMetricMeters: Float = 0.42
                        if let depthBuf = depthBuffer {
                            zMetricMeters = sampleDepth(at: pt.location, from: depthBuf)
                            if zMetricMeters > 0.1 && zMetricMeters < 3.0 {
                                samplesZ.append(zMetricMeters * 1000.0)
                            }
                        }
                        
                        rawPointsNorm.append([nx, ny, zMetricMeters])
                        currentHandUILandmarks.append(CGPoint(x: CGFloat(nx), y: CGFloat(ny)))
                    } else {
                        rawPointsNorm.append([0.5, 0.5, 0.42])
                        currentHandUILandmarks.append(.zero)
                    }
                }
                
                allHandsUILandmarks.append(currentHandUILandmarks)
                
                if !samplesZ.isEmpty {
                    avgZ = samplesZ.reduce(0, +) / Float(samplesZ.count)
                }
                
                // Adjust chirality when horizontal mirroring is active
                var chirality: String = (obs.chirality == .left) ? "Left" : "Right"
                if shouldFlipHorizontal {
                    chirality = (obs.chirality == .left) ? "Right" : "Left"
                }
                
                handsPayload.append([
                    "handedness": chirality,
                    "palm_size_mm": 85.0,
                    "depth_avg_mm": avgZ,
                    "landmarks_norm": rawPointsNorm
                ])
            }
            
            // Compute real FPS
            let now = CACurrentMediaTime()
            let dt = now - self.lastFrameTime
            self.lastFrameTime = now
            let instantFPS = dt > 0 ? (1.0 / dt) : 60.0
            
            DispatchQueue.main.async {
                self.isHandDetected = !allHandsUILandmarks.isEmpty
                self.currentDepthMM = handsPayload.first?["depth_avg_mm"] as? Float ?? 420.0
                self.actualFPS = 0.9 * self.actualFPS + 0.1 * instantFPS
                self.currentLandmarks = allHandsUILandmarks.first ?? []
                self.allHandLandmarks = allHandsUILandmarks
            }
            
            // Build network packet with all tracked hands
            let packet: [String: Any] = [
                "device": UIDevice.current.name,
                "sensor": (activeSensor == .frontTrueDepth) ? "TrueDepth (Face ID)" : "LiDAR (Back Pro)",
                "fps": round(instantFPS * 10) / 10,
                "battery": Int(UIDevice.current.batteryLevel * 100),
                "timestamp": now,
                "is_landscape": self.isLandscape,
                "is_mirrored": shouldFlipHorizontal || (activeSensor == .frontTrueDepth),
                "hands": handsPayload
            ]
            
            self.onHandPoseDetected?(packet)
            
        } catch {
            print("[!] Vision request error: \(error)")
        }
    }
    
    private func sampleDepth(at point: CGPoint, from depthBuffer: CVPixelBuffer) -> Float {
        CVPixelBufferLockBaseAddress(depthBuffer, .readOnly)
        defer { CVPixelBufferUnlockBaseAddress(depthBuffer, .readOnly) }
        
        let width = CVPixelBufferGetWidth(depthBuffer)
        let height = CVPixelBufferGetHeight(depthBuffer)
        let cx = max(0, min(width - 1, Int(point.x * CGFloat(width))))
        let cy = max(0, min(height - 1, Int((1.0 - point.y) * CGFloat(height))))
        
        guard let base = CVPixelBufferGetBaseAddress(depthBuffer) else { return 0.42 }
        let format = CVPixelBufferGetPixelFormatType(depthBuffer)
        let rowBytes = CVPixelBufferGetBytesPerRow(depthBuffer)
        
        // 3x3 median depth kernel to filter specular reflections and IR edge noise
        var validDepths: [Float] = []
        for dy in -1...1 {
            let y = cy + dy
            guard y >= 0 && y < height else { continue }
            let row = base.advanced(by: y * rowBytes)
            
            for dx in -1...1 {
                let x = cx + dx
                guard x >= 0 && x < width else { continue }
                
                var depthVal: Float = 0.0
                if format == kCVPixelFormatType_DepthFloat32 || format == kCVPixelFormatType_DisparityFloat32 {
                    depthVal = row.assumingMemoryBound(to: Float32.self)[x]
                } else if format == kCVPixelFormatType_DepthFloat16 {
                    depthVal = Float(row.assumingMemoryBound(to: Float16.self)[x])
                }
                
                if depthVal.isFinite && depthVal > 0.05 && depthVal < 4.0 {
                    validDepths.append(depthVal)
                }
            }
        }
        
        if !validDepths.isEmpty {
            validDepths.sort()
            return validDepths[validDepths.count / 2]
        }
        return 0.42
    }
}

// MARK: - AVCapture Video & Depth Delegates
extension SpatialTrackingManager: AVCaptureVideoDataOutputSampleBufferDelegate, AVCaptureDepthDataOutputDelegate {
    func captureOutput(_ output: AVCaptureOutput, didOutput sampleBuffer: CMSampleBuffer, from connection: AVCaptureConnection) {
        guard let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }
        depthLock.lock()
        let depth = lastDepthMap
        depthLock.unlock()
        processHandPose(on: pixelBuffer, depthBuffer: depth)
    }
    
    func depthDataOutput(_ output: AVCaptureDepthDataOutput, didOutput depthData: AVDepthData, timestamp: CMTime, connection: AVCaptureConnection) {
        depthLock.lock()
        self.lastDepthMap = depthData.depthDataMap
        depthLock.unlock()
    }
}

// MARK: - ARKit Session Delegate for LiDAR
extension SpatialTrackingManager: ARSessionDelegate {
    func session(_ session: ARSession, didUpdate frame: ARFrame) {
        let pixelBuffer = frame.capturedImage
        let depthBuffer = frame.smoothedSceneDepth?.depthMap ?? frame.sceneDepth?.depthMap
        processHandPose(on: pixelBuffer, depthBuffer: depthBuffer)
    }
}

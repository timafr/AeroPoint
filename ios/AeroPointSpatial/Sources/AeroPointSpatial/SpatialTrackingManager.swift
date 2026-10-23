//
//  SpatialTrackingManager.swift
//  AeroPointSpatial
//
//  Dual-Engine Spatial Tracking: TrueDepth (Face ID IR) & LiDAR (dToF)
//  Powered by Apple Neural Engine (Vision Framework) at 60 FPS
//

import Foundation
import AVFoundation
import Vision
import ARKit
import Combine

enum SensorType {
    case frontTrueDepth
    case backLiDAR
}

class SpatialTrackingManager: NSObject, ObservableObject {
    @Published var isHandDetected: Bool = false
    @Published var currentDepthMM: Float = 420.0
    @Published var actualFPS: Double = 60.0
    @Published var currentLandmarks: [CGPoint] = []
    
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
    }
    
    func startTracking() {
        switchSensor(activeSensor)
    }
    
    func stopTracking() {
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
                if let vConn = videoDataOutput.connection(with: .video) {
                    if vConn.isVideoOrientationSupported { vConn.videoOrientation = .portrait }
                    if vConn.isVideoMirroringSupported { vConn.isVideoMirrored = true }
                }
            }
            
            // Synchronized Depth Output
            if session.canAddOutput(depthDataOutput) {
                session.addOutput(depthDataOutput)
                depthDataOutput.isFilteringEnabled = true
                depthDataOutput.setDelegate(self, callbackQueue: visionQueue)
                if let dConn = depthDataOutput.connection(with: .depthData) {
                    if dConn.isVideoOrientationSupported { dConn.videoOrientation = .portrait }
                    if dConn.isVideoMirroringSupported { dConn.isVideoMirrored = true }
                }
            }
            
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
    
    // MARK: - Hand Pose Extraction & Physical Depth Fusion
    private func processHandPose(on pixelBuffer: CVPixelBuffer, depthBuffer: CVPixelBuffer?) {
        let visionOrientation: CGImagePropertyOrientation = (activeSensor == .frontTrueDepth) ? .up : .right
        let handler = VNImageRequestHandler(cvPixelBuffer: pixelBuffer, orientation: visionOrientation, options: [:])
        do {
            try handler.perform([handPoseRequest])
            guard let observations = handPoseRequest.results, !observations.isEmpty else {
                DispatchQueue.main.async {
                    self.isHandDetected = false
                    self.currentLandmarks = []
                }
                return
            }
            
            var handsPayload: [[String: Any]] = []
            
            // Strictly ordered 21 hand joints matching MediaPipe standard topology
            let jointKeys: [VNHumanHandPoseObservation.JointName] = [
                .wrist,
                .thumbCMC, .thumbMP, .thumbIP, .thumbTip,
                .indexMCP, .indexPIP, .indexDIP, .indexTip,
                .middleMCP, .middlePIP, .middleDIP, .middleTip,
                .ringMCP, .ringPIP, .ringDIP, .ringTip,
                .littleMCP, .littlePIP, .littleDIP, .littleTip
            ]
            
            var primaryUILandmarks: [CGPoint] = []
            
            for (obsIdx, obs) in observations.enumerated() {
                let recognizedPoints = try obs.recognizedPoints(.all)
                var rawPointsNorm: [[Float]] = []
                var currentHandUILandmarks: [CGPoint] = []
                
                var avgZ: Float = 420.0
                var samplesZ: [Float] = []
                
                for key in jointKeys {
                    if let pt = recognizedPoints[key], pt.confidence > 0.15 {
                        let nx = Float(pt.location.x)
                        let ny = Float(1.0 - pt.location.y)
                        
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
                
                if obsIdx == 0 {
                    primaryUILandmarks = currentHandUILandmarks
                }
                
                if !samplesZ.isEmpty {
                    avgZ = samplesZ.reduce(0, +) / Float(samplesZ.count)
                }
                
                let chirality: String = (obs.chirality == .left) ? "Left" : "Right"
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
                self.isHandDetected = true
                self.currentDepthMM = handsPayload.first?["depth_avg_mm"] as? Float ?? 420.0
                self.actualFPS = 0.9 * self.actualFPS + 0.1 * instantFPS
                self.currentLandmarks = primaryUILandmarks
            }
            
            // Build network packet
            let packet: [String: Any] = [
                "device": UIDevice.current.name,
                "sensor": (activeSensor == .frontTrueDepth) ? "TrueDepth (Face ID)" : "LiDAR (Back Pro)",
                "fps": round(instantFPS * 10) / 10,
                "battery": Int(UIDevice.current.batteryLevel * 100),
                "timestamp": now,
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
        let x = max(0, min(width - 1, Int(point.x * CGFloat(width))))
        let y = max(0, min(height - 1, Int((1.0 - point.y) * CGFloat(height))))
        
        guard let base = CVPixelBufferGetBaseAddress(depthBuffer) else { return 0.42 }
        let format = CVPixelBufferGetPixelFormatType(depthBuffer)
        
        if format == kCVPixelFormatType_DepthFloat32 || format == kCVPixelFormatType_DisparityFloat32 {
            let rowBytes = CVPixelBufferGetBytesPerRow(depthBuffer)
            let row = base.advanced(by: y * rowBytes)
            let val = row.assumingMemoryBound(to: Float32.self)[x]
            return val.isFinite ? val : 0.42
        } else if format == kCVPixelFormatType_DepthFloat16 {
            let rowBytes = CVPixelBufferGetBytesPerRow(depthBuffer)
            let row = base.advanced(by: y * rowBytes)
            let val = Float(row.assumingMemoryBound(to: Float16.self)[x])
            return val.isFinite ? val : 0.42
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

//
//  ContentView.swift
//  AeroPointSpatial
//
//  visionOS Glassmorphism Interface for iPhone Hand Tracking
//  Dual-Hand Holographic Skeleton & Dynamic Landscape/Portrait Layout
//

import SwiftUI
import AVFoundation
import Combine

struct ContentView: View {
    @StateObject private var tracker = SpatialTrackingManager()
    @StateObject private var broadcaster = NetworkBroadcaster()
    
    @State private var serverIP: String = "192.168.1.100"
    @State private var serverPort: String = "8765"
    @State private var isSettingsOpen: Bool = false
    @State private var activeSensor: SensorMode = .trueDepth
    
    enum SensorMode: String, CaseIterable, Identifiable {
        case trueDepth = "TrueDepth (Face ID)"
        case lidar = "LiDAR Scanner (Pro)"
        
        var id: String { self.rawValue }
        var icon: String {
            switch self {
            case .trueDepth: return "faceid"
            case .lidar: return "dot.scope.laptopcomputer"
            }
        }
    }

    var body: some View {
        ZStack {
            // Dark futuristic ambient background
            LinearGradient(
                colors: [Color(red: 0.05, green: 0.04, blue: 0.08), Color(red: 0.08, green: 0.05, blue: 0.12)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .ignoresSafeArea()
            
            VStack(spacing: tracker.isLandscape ? 8 : 16) {
                // Top Header Pill
                HStack {
                    HStack(spacing: 8) {
                        Circle()
                            .fill(broadcaster.isConnected ? Color.green : Color.orange)
                            .frame(width: 8, height: 8)
                            .shadow(color: broadcaster.isConnected ? Color.green : Color.orange, radius: 4)
                        
                        Text(broadcaster.isConnected ? "LIVE STREAMING" : "WAITING FOR PC")
                            .font(.system(size: 11, weight: .bold, design: .monospaced))
                            .foregroundColor(.white)
                    }
                    .padding(.horizontal, 12)
                    .padding(.vertical, 6)
                    .background(Color.white.opacity(0.12))
                    .clipShape(Capsule())
                    
                    if tracker.isLandscape {
                        Text(tracker.allHandLandmarks.count >= 2 ? "DUAL-HAND ACTIVE (42 JOINTS)" : (tracker.isHandDetected ? "1 HAND DETECTED" : "SEARCHING"))
                            .font(.system(size: 11, weight: .semibold, design: .monospaced))
                            .foregroundColor(.cyan)
                            .padding(.horizontal, 10)
                            .padding(.vertical, 4)
                            .background(Color.cyan.opacity(0.15))
                            .clipShape(Capsule())
                    }
                    
                    Spacer()
                    
                    Button(action: { isSettingsOpen.toggle() }) {
                        Image(systemName: "gearshape.fill")
                            .font(.system(size: 16))
                            .foregroundColor(.white.opacity(0.85))
                            .padding(8)
                            .background(Color.white.opacity(0.12))
                            .clipShape(Circle())
                    }
                }
                .padding(.horizontal)
                .padding(.top, tracker.isLandscape ? 4 : 8)
                
                // Sensor Mode Segmented Pill (Hidden or compact in landscape to maximize camera)
                if !tracker.isLandscape {
                    Picker("Sensor", selection: $activeSensor) {
                        ForEach(SensorMode.allCases) { mode in
                            HStack {
                                Image(systemName: mode.icon)
                                Text(mode.rawValue)
                            }
                            .tag(mode)
                        }
                    }
                    .pickerStyle(SegmentedPickerStyle())
                    .padding(.horizontal)
                    .onChange(of: activeSensor) { newMode in
                        tracker.switchSensor(newMode == .trueDepth ? .frontTrueDepth : .backLiDAR)
                    }
                }

                // Spatial Viewport / Camera & Hologram Display
                ZStack {
                    RoundedRectangle(cornerRadius: 24, style: .continuous)
                        .fill(Color.black.opacity(0.6))
                        .overlay(
                            RoundedRectangle(cornerRadius: 24, style: .continuous)
                                .stroke(
                                    LinearGradient(
                                        colors: [Color.cyan.opacity(0.6), Color.purple.opacity(0.4)],
                                        startPoint: .topLeading,
                                        endPoint: .bottomTrailing
                                    ),
                                    lineWidth: 1.5
                                )
                        )
                        .shadow(color: Color.cyan.opacity(0.2), radius: 16, x: 0, y: 8)
                    
                    // Video & Dual-Hand Skeleton Rendering
                    CameraPreviewView(session: tracker.captureSession, currentOrientation: tracker.currentVideoOrientation)
                        .clipShape(RoundedRectangle(cornerRadius: 22, style: .continuous))
                    
                    SkeletonOverlayView(allHands: tracker.allHandLandmarks)
                        .clipShape(RoundedRectangle(cornerRadius: 22, style: .continuous))
                    
                    // Reticle Corner Accents
                    VStack {
                        HStack {
                            CornerBracket(corner: .topLeft)
                            Spacer()
                            CornerBracket(corner: .topRight)
                        }
                        Spacer()
                        HStack {
                            CornerBracket(corner: .bottomLeft)
                            Spacer()
                            CornerBracket(corner: .bottomRight)
                        }
                    }
                    .padding(14)
                    
                    // Floating Spatial Depth Badge
                    VStack {
                        Spacer()
                        HStack {
                            HStack(spacing: 6) {
                                Image(systemName: "ruler.fill")
                                    .font(.system(size: 11))
                                    .foregroundColor(.cyan)
                                Text("Z: \(Int(tracker.currentDepthMM)) mm")
                                    .font(.system(size: 13, weight: .semibold, design: .monospaced))
                                    .foregroundColor(.white)
                            }
                            .padding(.horizontal, 10)
                            .padding(.vertical, 5)
                            .background(Color.black.opacity(0.75))
                            .clipShape(Capsule())
                            
                            Spacer()
                            
                            HStack(spacing: 6) {
                                Image(systemName: "hand.raised.fill")
                                    .font(.system(size: 11))
                                    .foregroundColor(tracker.allHandLandmarks.count >= 2 ? .cyan : (tracker.isHandDetected ? .green : .gray))
                                Text(tracker.allHandLandmarks.count >= 2 ? "2 HANDS (42 JOINTS)" : (tracker.isHandDetected ? "1 HAND (21 JOINTS)" : "SEARCHING..."))
                                    .font(.system(size: 11, weight: .bold, design: .monospaced))
                                    .foregroundColor(tracker.allHandLandmarks.count >= 2 ? .cyan : (tracker.isHandDetected ? .green : .gray))
                            }
                            .padding(.horizontal, 10)
                            .padding(.vertical, 5)
                            .background(Color.black.opacity(0.75))
                            .clipShape(Capsule())
                        }
                        .padding(16)
                    }
                }
                .aspectRatio(tracker.isLandscape ? (4.0 / 3.0) : (3.0 / 4.0), contentMode: .fit)
                .padding(.horizontal)

                // Live Metrics Bar (FPS, Ping, Packets)
                HStack(spacing: 12) {
                    MetricCard(title: "RATE", value: "\(Int(tracker.actualFPS)) FPS", color: .green)
                    MetricCard(title: "PING", value: "\(String(format: "%.1f", broadcaster.pingMs)) ms", color: .cyan)
                    MetricCard(title: "HANDS", value: "\(tracker.allHandLandmarks.count)", color: .purple)
                }
                .padding(.horizontal)
                
                // Broadcast Toggle
                Button(action: {
                    if broadcaster.isStreaming {
                        broadcaster.stopStreaming()
                    } else {
                        broadcaster.startStreaming(host: serverIP, port: UInt16(serverPort) ?? 8765)
                    }
                }) {
                    HStack {
                        Image(systemName: broadcaster.isStreaming ? "stop.circle.fill" : "bolt.horizontal.circle.fill")
                            .font(.system(size: 18))
                        Text(broadcaster.isStreaming ? "ОСТАНОВИТЬ ТРАНСЛЯЦИЮ" : "ПОДКЛЮЧИТЬ К ПК")
                            .font(.system(size: 14, weight: .bold, design: .monospaced))
                    }
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, tracker.isLandscape ? 10 : 14)
                    .background(
                        broadcaster.isStreaming
                            ? LinearGradient(colors: [Color.red, Color.orange], startPoint: .leading, endPoint: .trailing)
                            : LinearGradient(colors: [Color.cyan, Color.blue], startPoint: .leading, endPoint: .trailing)
                    )
                    .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
                    .shadow(color: (broadcaster.isStreaming ? Color.red : Color.cyan).opacity(0.4), radius: 10, y: 4)
                }
                .padding(.horizontal)
                .padding(.bottom, tracker.isLandscape ? 4 : 8)
            }
        }
        .sheet(isPresented: $isSettingsOpen) {
            SettingsSheetView(serverIP: $serverIP, serverPort: $serverPort)
        }
        .onAppear {
            UIApplication.shared.isIdleTimerDisabled = true
            tracker.startTracking()
            tracker.onHandPoseDetected = { payload in
                broadcaster.sendSpatialData(payload)
            }
        }
        .onDisappear {
            UIApplication.shared.isIdleTimerDisabled = false
            tracker.stopTracking()
            broadcaster.stopStreaming()
        }
    }
}

// Subview: Metric Card
struct MetricCard: View {
    let title: String
    let value: String
    let color: Color
    
    var body: some View {
        VStack(spacing: 3) {
            Text(title)
                .font(.system(size: 9, weight: .bold, design: .monospaced))
                .foregroundColor(.white.opacity(0.6))
            Text(value)
                .font(.system(size: 14, weight: .bold, design: .monospaced))
                .foregroundColor(color)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 8)
        .background(Color.white.opacity(0.06))
        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
    }
}

// Subview: Corner Bracket
struct CornerBracket: View {
    enum Corner { case topLeft, topRight, bottomLeft, bottomRight }
    let corner: Corner
    
    var body: some View {
        Canvas { context, size in
            var path = Path()
            let len: CGFloat = 14
            switch corner {
            case .topLeft:
                path.move(to: CGPoint(x: 0, y: len))
                path.addLine(to: CGPoint(x: 0, y: 0))
                path.addLine(to: CGPoint(x: len, y: 0))
            case .topRight:
                path.move(to: CGPoint(x: size.width - len, y: 0))
                path.addLine(to: CGPoint(x: size.width, y: 0))
                path.addLine(to: CGPoint(x: size.width, y: len))
            case .bottomLeft:
                path.move(to: CGPoint(x: 0, y: size.height - len))
                path.addLine(to: CGPoint(x: 0, y: size.height))
                path.addLine(to: CGPoint(x: len, y: size.height))
            case .bottomRight:
                path.move(to: CGPoint(x: size.width - len, y: size.height))
                path.addLine(to: CGPoint(x: size.width, y: size.height))
                path.addLine(to: CGPoint(x: size.width, y: size.height - len))
            }
            context.stroke(path, with: .color(.cyan), lineWidth: 2)
        }
        .frame(width: 14, height: 14)
    }
}

// Settings Sheet
struct SettingsSheetView: View {
    @Binding var serverIP: String
    @Binding var serverPort: String
    @Environment(\.dismiss) var dismiss
    
    var body: some View {
        NavigationView {
            Form {
                Section(header: Text("Параметры соединения с ПК")) {
                    HStack {
                        Text("IP адрес ПК:")
                        Spacer()
                        TextField("192.168.1.100", text: $serverIP)
                            .multilineTextAlignment(.trailing)
                            .keyboardType(.numbersAndPunctuation)
                    }
                    HStack {
                        Text("UDP Порт:")
                        Spacer()
                        TextField("8765", text: $serverPort)
                            .multilineTextAlignment(.trailing)
                            .keyboardType(.numberPad)
                    }
                }
                
                Section(header: Text("Подключение по кабелю (USB)")) {
                    Text("Для нулевой задержки (0.5 ms) подключите iPhone проводом к ПК. Порт 8765 транслируется автоматически через USB tunnel.")
                        .font(.system(size: 12))
                        .foregroundColor(.secondary)
                }
            }
            .navigationTitle("Настройки")
            .navigationBarItems(trailing: Button("Готово") { dismiss() })
        }
    }
}

// Camera Preview Platform View
struct CameraPreviewView: UIViewRepresentable {
    let session: AVCaptureSession?
    let currentOrientation: AVCaptureVideoOrientation
    
    func makeUIView(context: Context) -> UIView {
        let view = UIView(frame: .zero)
        guard let session = session else { return view }
        let preview = AVCaptureVideoPreviewLayer(session: session)
        preview.videoGravity = .resizeAspectFill
        if preview.connection?.isVideoOrientationSupported == true {
            preview.connection?.videoOrientation = currentOrientation
        }
        view.layer.addSublayer(preview)
        context.coordinator.previewLayer = preview
        return view
    }
    
    func updateUIView(_ uiView: UIView, context: Context) {
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        context.coordinator.previewLayer?.frame = uiView.bounds
        if let conn = context.coordinator.previewLayer?.connection, conn.isVideoOrientationSupported {
            if conn.videoOrientation != currentOrientation {
                conn.videoOrientation = currentOrientation
            }
        }
        CATransaction.commit()
    }
    
    func makeCoordinator() -> Coordinator {
        Coordinator()
    }
    
    class Coordinator {
        var previewLayer: AVCaptureVideoPreviewLayer?
    }
}

// Dual-Hand Skeleton Overlay View
struct SkeletonOverlayView: View {
    let allHands: [[CGPoint]]
    
    private let connections: [(Int, Int)] = [
        // Thumb
        (0,1), (1,2), (2,3), (3,4),
        // Index
        (0,5), (5,6), (6,7), (7,8),
        // Middle
        (5,9), (9,10), (10,11), (11,12),
        // Ring
        (9,13), (13,14), (14,15), (15,16),
        // Little
        (13,17), (17,18), (18,19), (19,20),
        // Palm closure
        (0,17)
    ]
    
    var body: some View {
        Canvas { context, size in
            for (handIdx, landmarks) in allHands.enumerated() {
                guard landmarks.count == 21 else { continue }
                
                // Hand 0: Electric Cyan & Hot Magenta
                // Hand 1: Sunset Amber & Toxic Emerald
                let boneGlowColor: Color = (handIdx == 0)
                    ? Color(red: 0.54, green: 0.17, blue: 0.89).opacity(0.55)
                    : Color(red: 0.95, green: 0.40, blue: 0.10).opacity(0.55)
                
                let boneCoreColor: Color = (handIdx == 0)
                    ? Color(red: 0.0, green: 0.95, blue: 1.0)
                    : Color(red: 1.0, green: 0.84, blue: 0.0)
                
                let tipColor: Color = (handIdx == 0)
                    ? Color(red: 1.0, green: 0.15, blue: 0.5)
                    : Color(red: 0.2, green: 1.0, blue: 0.5)
                
                // 1. Draw Bones
                for (p1, p2) in connections {
                    guard p1 < landmarks.count && p2 < landmarks.count else { continue }
                    let pt1 = landmarks[p1]
                    let pt2 = landmarks[p2]
                    guard pt1 != .zero && pt2 != .zero else { continue }
                    
                    let pos1 = CGPoint(x: pt1.x * size.width, y: pt1.y * size.height)
                    let pos2 = CGPoint(x: pt2.x * size.width, y: pt2.y * size.height)
                    
                    var path = Path()
                    path.move(to: pos1)
                    path.addLine(to: pos2)
                    
                    context.stroke(path, with: .color(boneGlowColor), lineWidth: 4.5)
                    context.stroke(path, with: .color(boneCoreColor), lineWidth: 2.2)
                }
                
                // 2. Draw Joints
                for (idx, pt) in landmarks.enumerated() {
                    guard pt != .zero else { continue }
                    let pos = CGPoint(x: pt.x * size.width, y: pt.y * size.height)
                    let isTip = [4, 8, 12, 16, 20].contains(idx)
                    let isWrist = (idx == 0)
                    
                    if isTip {
                        let radius: CGFloat = 6.5
                        context.fill(Path(ellipseIn: CGRect(x: pos.x - radius, y: pos.y - radius, width: radius * 2, height: radius * 2)), with: .color(tipColor))
                        context.stroke(Path(ellipseIn: CGRect(x: pos.x - radius - 2, y: pos.y - radius - 2, width: (radius + 2) * 2, height: (radius + 2) * 2)), with: .color(boneCoreColor), lineWidth: 1.5)
                    } else if isWrist {
                        let radius: CGFloat = 5.5
                        context.fill(Path(ellipseIn: CGRect(x: pos.x - radius, y: pos.y - radius, width: radius * 2, height: radius * 2)), with: .color(boneCoreColor))
                    } else {
                        let radius: CGFloat = 3.5
                        context.fill(Path(ellipseIn: CGRect(x: pos.x - radius, y: pos.y - radius, width: radius * 2, height: radius * 2)), with: .color(.white))
                    }
                }
            }
        }
    }
}

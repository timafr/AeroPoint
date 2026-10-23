// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "AeroPointSpatial",
    platforms: [
        .iOS(.v16)
    ],
    products: [
        .library(
            name: "AeroPointSpatial",
            targets: ["AeroPointSpatial"]
        ),
    ],
    targets: [
        .target(
            name: "AeroPointSpatial",
            dependencies: [],
            path: "Sources"
        )
    ]
)

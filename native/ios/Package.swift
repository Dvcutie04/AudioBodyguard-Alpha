// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "AQSSNativeFeedback",
    platforms: [.iOS(.v15)],
    products: [
        .library(
            name: "AQSSNativeFeedback",
            targets: ["AQSSNativeFeedback"]
        )
    ],
    targets: [
        .target(
            name: "AQSSNativeFeedback",
            path: "Sources/AQSSNativeFeedback"
        ),
        .testTarget(
            name: "AQSSNativeFeedbackTests",
            dependencies: ["AQSSNativeFeedback"],
            path: "Tests/AQSSNativeFeedbackTests"
        )
    ]
)

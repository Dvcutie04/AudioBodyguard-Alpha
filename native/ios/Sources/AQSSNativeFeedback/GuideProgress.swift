/// Local learning state only. It has no device, account, permission or adapter API.
public struct AQSSGuideProgress: Equatable, Sendable {
    public private(set) var topicID: String?
    public private(set) var index = 0
    public private(set) var selections: [String: String] = [:]
    public init() {}
    public var topic: AQSSTutorialTopic? { AQSSTutorialContent.topics.first { $0.id == topicID } }
    public var step: AQSSTutorialStep? { guard let topic, topic.steps.indices.contains(index) else { return nil }; return topic.steps[index] }
    public var choices: [AQSSTutorialChoice] { AQSSTutorialContent.choices[step?.target ?? ""] ?? [] }
    public var canContinue: Bool { step != nil && (choices.isEmpty || choices.contains { $0.id == selections[step!.target] }) }
    public var isLast: Bool { guard let topic else { return false }; return index == topic.steps.count - 1 }
    public func selected(_ target: String) -> AQSSTutorialChoice? { AQSSTutorialContent.choices[target]?.first { $0.id == selections[target] } }
    @discardableResult public mutating func start(_ id: String) -> Bool {
        guard AQSSTutorialContent.topics.contains(where: { $0.id == id }) else { return false }
        topicID = id; index = 0; selections = [:]; return true
    }
    @discardableResult public mutating func select(_ id: String) -> Bool {
        guard let step, choices.contains(where: { $0.id == id }) else { return false }
        selections[step.target] = id; return true
    }
    @discardableResult public mutating func next() -> Bool {
        guard canContinue, !isLast else { return false }; index += 1; return true
    }
    public mutating func back() { if index > 0 { index -= 1 } }
    public mutating func close() { topicID = nil; index = 0; selections = [:] }
    /// Restored state can never bypass an unanswered earlier question.
    public mutating func restore(_ id: String, index requested: Int, selections saved: [String: String]) {
        guard start(id), let topic else { return }
        for (target, id) in saved where AQSSTutorialContent.choices[target]?.contains(where: { $0.id == id }) == true { selections[target] = id }
        let destination = max(0, min(requested, topic.steps.count - 1))
        while index < destination && next() {}
    }
}

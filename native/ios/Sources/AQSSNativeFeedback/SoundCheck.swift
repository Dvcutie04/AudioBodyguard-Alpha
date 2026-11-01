import Foundation

/// A digital input summary; never acoustic calibration, coverage or output evidence.
public struct SoundInputLevel: Equatable {
    public let sampleCount: Int
    public let rmsDbfs: Double?
    public let peakFraction: Double
    public let fullScaleSamples: Int

    public enum InvalidInput: Error { case format }

    /// Borrow only this mono Float32 prefix. No raw samples escape this call.
    public static func measure(_ samples: UnsafeBufferPointer<Float>) throws -> Self {
        guard (1...65_536).contains(samples.count) else { throw InvalidInput.format }
        var energy = 0.0, peak = 0.0
        var fullScale = 0
        for sample in samples {
            guard sample.isFinite else { throw InvalidInput.format }
            let value = Double(sample)
            energy += value * value
            peak = max(peak, abs(value))
            if abs(value) >= 1 { fullScale += 1 }
        }
        let rms = sqrt(energy / Double(samples.count))
        return Self(sampleCount: samples.count, rmsDbfs: rms == 0 ? nil : 20 * log10(rms),
                    peakFraction: peak, fullScaleSamples: fullScale)
    }
}

/// Main-thread freshness policy. Clock discontinuity and expiry latch this run off.
public struct SoundInputWindow {
    public enum EndReason { case stopped, clockInvalid, timeLimit }
    public private(set) var active = false
    public private(set) var endReason: EndReason = .stopped
    private var generation: UInt64 = 0
    private var startedAt = 0.0, checkedAt = 0.0
    private var receivedAt: Double?
    private var latest: SoundInputLevel?
    public init() {}

    public mutating func start(at now: Double) -> UInt64? {
        stop()
        guard now.isFinite, now >= 0, generation < UInt64.max else { return nil }
        generation += 1; active = true; startedAt = now; checkedAt = now
        receivedAt = nil
        return generation
    }
    private mutating func eligible(_ now: Double) -> Bool {
        guard active else { return false }
        guard now.isFinite, now >= checkedAt else {
            stop(); endReason = .clockInvalid; return false
        }
        guard now - startedAt < 30 else { stop(); endReason = .timeLimit; return false }
        checkedAt = now
        return true
    }
    public mutating func offer(run: UInt64, receivedAt time: Double, now: Double, value: SoundInputLevel) -> Bool {
        guard run == generation, eligible(now), time.isFinite, time >= startedAt,
              time <= now, now - time < 0.75, time > (receivedAt ?? -1) else { return false }
        latest = value; receivedAt = time
        return true
    }
    public mutating func current(at now: Double) -> SoundInputLevel? {
        guard eligible(now), let time = receivedAt, now - time < 0.75 else {
            latest = nil; return nil
        }
        return latest
    }
    public mutating func stop() { active = false; latest = nil; endReason = .stopped }
}

/// One summary slot per run. Audio callbacks never wait on the consumer's lock.
/// Contended publications are discarded; the freshness gate handles missing input.
public final class SoundInputMailbox {
    public struct Frame {
        public let receivedAt: Double
        public let level: SoundInputLevel
    }
    private let lock = NSLock()
    private var closed = false
    private var latest: Frame?
    private var invalid = false
    public init() {}
    public func publish(_ level: SoundInputLevel, at time: Double) {
        guard lock.try() else { return }
        defer { lock.unlock() }
        guard !closed, !invalid else { return }
        latest = Frame(receivedAt: time, level: level)
    }
    public func rejectInput() {
        guard lock.try() else { return }
        defer { lock.unlock() }
        guard !closed else { return }
        invalid = true; latest = nil
    }
    public var invalidInput: Bool {
        lock.lock(); defer { lock.unlock() }; return invalid
    }
    public func take() -> Frame? {
        lock.lock(); defer { lock.unlock() }
        let result = latest; latest = nil; return result
    }
    public func close() {
        lock.lock(); defer { lock.unlock() }; closed = true; latest = nil
    }
}

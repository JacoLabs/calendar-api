import Foundation

struct ParsedEvent: Codable {
    let title: String?
    let startDatetime: String?
    let endDatetime: String?
    let location: String?
    let description: String?
    let confidenceScore: Double
    let allDay: Bool?
    let timezone: String?
    // Enhanced fields
    let fieldResults: [String: FieldResult]?
    let parsingPath: String?
    let processingTimeMs: Int?
    let cacheHit: Bool?
    let warnings: [String]?
    let needsConfirmation: Bool?

    enum CodingKeys: String, CodingKey {
        case title
        case startDatetime = "start_datetime"
        case endDatetime   = "end_datetime"
        case location
        case description
        case confidenceScore = "confidence_score"
        case allDay = "all_day"
        case timezone
        case fieldResults = "field_results"
        case parsingPath  = "parsing_path"
        case processingTimeMs = "processing_time_ms"
        case cacheHit = "cache_hit"
        case warnings
        case needsConfirmation = "needs_confirmation"
    }
}

// Keep FieldResult as-is
struct FieldResult: Codable {
    let value: AnyCodable?
    let source: String
    let confidence: Double
    let span: [Int]?
    let processingTimeMs: Int?

    enum CodingKeys: String, CodingKey {
        case value, source, confidence, span
        case processingTimeMs = "processing_time_ms"
    }
}

// Tiny wrapper for heterogenous JSON values (String/Int/Double/Bool)
struct AnyCodable: Codable {
    let value: Any

    init(_ value: Any) { self.value = value }

    init(from decoder: Decoder) throws {
        let c = try decoder.singleValueContainer()
        if let s = try? c.decode(String.self) { value = s }
        else if let i = try? c.decode(Int.self) { value = i }
        else if let d = try? c.decode(Double.self) { value = d }
        else if let b = try? c.decode(Bool.self) { value = b }
        else { value = NSNull() }
    }

    func encode(to encoder: Encoder) throws {
        var c = encoder.singleValueContainer()
        switch value {
        case let s as String: try c.encode(s)
        case let i as Int:    try c.encode(i)
        case let d as Double: try c.encode(d)
        case let b as Bool:   try c.encode(b)
        default: try c.encodeNil()
        }
    }
}

// MARK: - Convenience accessors belong to ParsedEvent
extension ParsedEvent {

    var isAllDay: Bool { allDay ?? false }

    var eventTimezone: String { timezone ?? TimeZone.current.identifier }

    var displayTitle: String { title ?? "Untitled Event" }

    var displayLocation: String { location ?? "No location specified" }

    var displayDescription: String { description ?? "No description" }

    var formattedStartDate: String {
        guard let s = startDatetime else { return "No date specified" }
        let iso = ISO8601DateFormatter()
        iso.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let date = iso.date(from: s) {
            let out = DateFormatter()
            out.dateStyle = .medium
            out.timeStyle = isAllDay ? .none : .short
            out.timeZone  = TimeZone(identifier: eventTimezone)
            return out.string(from: date)
        }
        return s
    }

    var formattedEndDate: String {
        guard let e = endDatetime else { return "No end time" }
        let iso = ISO8601DateFormatter()
        iso.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let date = iso.date(from: e) {
            let out = DateFormatter()
            out.dateStyle = isAllDay ? .none : .none
            out.timeStyle = .short
            out.timeZone  = TimeZone(identifier: eventTimezone)
            return out.string(from: date)
        }
        return e
    }
}

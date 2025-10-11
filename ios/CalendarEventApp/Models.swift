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
        case endDatetime = "end_datetime"
        case location
        case description
        case confidenceScore = "confidence_score"
        case allDay = "all_day"
        case timezone
        case fieldResults = "field_results"
        case parsingPath = "parsing_path"
        case processingTimeMs = "processing_time_ms"
        case cacheHit = "cache_hit"
        case warnings
        case needsConfirmation = "needs_confirmation"
    }
}

struct FieldResult: Codable {
    let value: AnyCodable?
    let source: String
    let confidence: Double
    let span: [Int]?
    let processingTimeMs: Int?
    
    enum CodingKeys: String, CodingKey {
        case value
        case source
        case confidence
        case span
        case processingTimeMs = "processing_time_ms"
    }
}

// Helper struct to handle Any type in Codable
struct AnyCodable: Codable {
    let value: Any
    
    init(_ value: Any) {
        self.value = value
    }
    
    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        
        if let string = try? container.decode(String.self) {
            value = string
        } else if let int = try? container.decode(Int.self) {
            value = int
        } else if let double = try? container.decode(Double.self) {
            value = double
        } else if let bool = try? container.decode(Bool.self) {
            value = bool
        } else {
            value = ""
        }
    }
    
    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        
        if let string = value as? String {
            try container.encode(string)
        } else if let int = value as? Int {
            try container.encode(int)
        } else if let double = value as? Double {
            try container.encode(double)
        } else if let bool = value as? Bool {
            try container.encode(bool)
        }
    }
    
    // Default values for optional properties
    var isAllDay: Bool {
        return allDay ?? false
    }
    
    var eventTimezone: String {
        return timezone ?? TimeZone.current.identifier
    }
    
    var displayTitle: String {
        return title ?? "Untitled Event"
    }
    
    var displayLocation: String {
        return location ?? "No location specified"
    }
    
    var displayDescription: String {
        return description ?? "No description"
    }
    
    var formattedStartDate: String {
        guard let startDatetime = startDatetime else { return "No date specified" }
        
        let formatter = ISO8601DateFormatter()
        
        if let date = formatter.date(from: startDatetime) {
            let displayFormatter = DateFormatter()
            displayFormatter.dateStyle = .medium
            displayFormatter.timeStyle = .short
            return displayFormatter.string(from: date)
        }
        
        return startDatetime
    }
    
    var formattedEndDate: String {
        guard let endDatetime = endDatetime else { return "No end time" }
        
        let formatter = ISO8601DateFormatter()
        
        if let date = formatter.date(from: endDatetime) {
            let displayFormatter = DateFormatter()
            displayFormatter.timeStyle = .short
            return displayFormatter.string(from: date)
        }
        
        return endDatetime
    }
}


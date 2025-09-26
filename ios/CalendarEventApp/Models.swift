import Foundation

struct ParsedEvent: Codable {
    let title: String?
    let startDatetime: String?
    let endDatetime: String?
    let location: String?
    let description: String?
    let confidenceScore: Double
    let allDay: Bool
    let timezone: String
    
    enum CodingKeys: String, CodingKey {
        case title
        case startDatetime = "start_datetime"
        case endDatetime = "end_datetime"
        case location
        case description
        case confidenceScore = "confidence_score"
        case allDay = "all_day"
        case timezone
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


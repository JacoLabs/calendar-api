import Foundation

/**
 * Service for calling the text-to-calendar API from iOS.
 */
class ApiService {
    
    private let baseURL = "https://calendar-api-wrxz.onrender.com"
    private let session = URLSession.shared
    
    struct ParseResult {
        let title: String?
        let startDateTime: String?
        let endDateTime: String?
        let location: String?
        let description: String?
        let confidenceScore: Double
        let allDay: Bool
        let timezone: String
    }
    
    enum ApiError: Error {
        case invalidURL
        case noData
        case decodingError
        case networkError(String)
    }
    
    /**
     * Parse text using the remote API.
     */
    func parseText(text: String, timezone: String, locale: String, now: Date) async throws -> ParseResult {
        guard let url = URL(string: "\(baseURL)/parse") else {
            throw ApiError.invalidURL
        }
        
        // Create request
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.setValue("CalendarEventApp-iOS/1.0", forHTTPHeaderField: "User-Agent")
        request.timeoutInterval = 10.0
        
        // Create request body
        let requestBody: [String: Any] = [
            "text": text,
            "timezone": timezone,
            "locale": locale,
            "now": formatDateForAPI(now)
        ]
        
        do {
            request.httpBody = try JSONSerialization.data(withJSONObject: requestBody)
        } catch {
            throw ApiError.networkError("Failed to encode request: \(error.localizedDescription)")
        }
        
        // Make request
        do {
            let (data, response) = try await session.data(for: request)
            
            // Check response status
            if let httpResponse = response as? HTTPURLResponse {
                guard httpResponse.statusCode == 200 else {
                    let errorMessage = String(data: data, encoding: .utf8) ?? "Unknown error"
                    throw ApiError.networkError("API request failed with status \(httpResponse.statusCode): \(errorMessage)")
                }
            }
            
            // Parse response
            return try parseAPIResponse(data)
            
        } catch {
            if error is ApiError {
                throw error
            } else {
                throw ApiError.networkError("Network request failed: \(error.localizedDescription)")
            }
        }
    }
    
    private func parseAPIResponse(_ data: Data) throws -> ParseResult {
        do {
            guard let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
                throw ApiError.decodingError
            }
            
            return ParseResult(
                title: json["title"] as? String,
                startDateTime: json["start_datetime"] as? String,
                endDateTime: json["end_datetime"] as? String,
                location: json["location"] as? String,
                description: json["description"] as? String,
                confidenceScore: json["confidence_score"] as? Double ?? 0.0,
                allDay: json["all_day"] as? Bool ?? false,
                timezone: json["timezone"] as? String ?? "UTC"
            )
            
        } catch {
            throw ApiError.decodingError
        }
    }
    
    private func formatDateForAPI(_ date: Date) -> String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        return formatter.string(from: date)
    }
}
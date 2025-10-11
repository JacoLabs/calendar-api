import Foundation

class ApiService {
    static let shared = ApiService()
    private let baseURL = "https://calendar-api-wrxz.onrender.com"
    
    private init() {}
    
    func parseText(_ text: String, mode: String? = nil, fields: [String]? = nil, completion: @escaping (Result<ParsedEvent, Error>) -> Void) {
        // Validate input
        guard !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            completion(.failure(ApiError.validationError("Please provide text containing event information.")))
            return
        }
        
        guard text.count <= 10000 else {
            completion(.failure(ApiError.validationError("Text is too long. Please limit to 10,000 characters.")))
            return
        }
        
        // Build URL with query parameters for enhanced features
        var urlComponents = URLComponents(string: "\(baseURL)/parse")!
        var queryItems: [URLQueryItem] = []
        
        if let mode = mode {
            queryItems.append(URLQueryItem(name: "mode", value: mode))
        }
        
        if let fields = fields, !fields.isEmpty {
            queryItems.append(URLQueryItem(name: "fields", value: fields.joined(separator: ",")))
        }
        
        if !queryItems.isEmpty {
            urlComponents.queryItems = queryItems
        }
        
        guard let url = urlComponents.url else {
            completion(.failure(ApiError.invalidURL))
            return
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.setValue("CalendarEventApp-iOS/2.0", forHTTPHeaderField: "User-Agent")
        request.timeoutInterval = 30.0
        
        // Enhanced request body with timezone and locale
        let requestBody: [String: Any] = [
            "text": text,
            "timezone": TimeZone.current.identifier,
            "locale": Locale.current.identifier,
            "now": ISO8601DateFormatter().string(from: Date()),
            "use_llm_enhancement": true
        ]
        
        do {
            request.httpBody = try JSONSerialization.data(withJSONObject: requestBody)
        } catch {
            completion(.failure(ApiError.encodingError))
            return
        }
        
        // Perform request with retry logic
        performRequestWithRetry(request: request, retryCount: 0, completion: completion)
    }
    
    private func performRequestWithRetry(request: URLRequest, retryCount: Int, completion: @escaping (Result<ParsedEvent, Error>) -> Void) {
        let maxRetries = 3
        
        URLSession.shared.dataTask(with: request) { [weak self] data, response, error in
            // Handle network errors
            if let error = error {
                let nsError = error as NSError
                
                switch nsError.code {
                case NSURLErrorTimedOut:
                    if retryCount < maxRetries {
                        DispatchQueue.global().asyncAfter(deadline: .now() + Double(retryCount + 1)) {
                            self?.performRequestWithRetry(request: request, retryCount: retryCount + 1, completion: completion)
                        }
                        return
                    } else {
                        completion(.failure(ApiError.timeoutError("Request timed out after multiple attempts. Please check your internet connection.")))
                        return
                    }
                case NSURLErrorNotConnectedToInternet, NSURLErrorNetworkConnectionLost:
                    completion(.failure(ApiError.networkError("No internet connection. Please check your network settings and try again.")))
                    return
                case NSURLErrorCannotConnectToHost, NSURLErrorCannotFindHost:
                    if retryCount < maxRetries {
                        DispatchQueue.global().asyncAfter(deadline: .now() + Double((retryCount + 1) * 2)) {
                            self?.performRequestWithRetry(request: request, retryCount: retryCount + 1, completion: completion)
                        }
                        return
                    } else {
                        completion(.failure(ApiError.networkError("Unable to connect to the server. Please try again later.")))
                        return
                    }
                default:
                    completion(.failure(ApiError.networkError("Network error: \(error.localizedDescription)")))
                    return
                }
            }
            
            guard let httpResponse = response as? HTTPURLResponse else {
                completion(.failure(ApiError.invalidResponse))
                return
            }
            
            guard let data = data else {
                completion(.failure(ApiError.noData))
                return
            }
            
            // Handle different HTTP status codes
            switch httpResponse.statusCode {
            case 200:
                do {
                    // First try to parse as JSON to check structure
                    if let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] {
                        // Handle nested response format
                        if let parsedEventData = json["parsed_event"] as? [String: Any] {
                            let parsedEventJson = try JSONSerialization.data(withJSONObject: parsedEventData)
                            let event = try JSONDecoder().decode(ParsedEvent.self, from: parsedEventJson)
                            
                            // Validate the parsed result
                            if let validationError = self?.validateParseResult(event, originalText: request.httpBody.flatMap { String(data: $0, encoding: .utf8) } ?? "") {
                                completion(.failure(validationError))
                                return
                            }
                            
                            completion(.success(event))
                        } else {
                            // Try direct parsing
                            let event = try JSONDecoder().decode(ParsedEvent.self, from: data)
                            
                            // Handle enhanced API response format
                            if let fieldResults = json["field_results"] as? [String: Any] {
                                print("Field confidence scores: \(fieldResults)")
                            }
                            
                            if let parsingPath = json["parsing_path"] as? String {
                                print("Parsing method used: \(parsingPath)")
                            }
                            
                            if let cacheHit = json["cache_hit"] as? Bool, cacheHit {
                                print("Result served from cache")
                            }
                            
                            if let warnings = json["warnings"] as? [String], !warnings.isEmpty {
                                print("Parsing warnings: \(warnings)")
                            }
                            
                            // Validate the parsed result
                            if let validationError = self?.validateParseResult(event, originalText: request.httpBody.flatMap { String(data: $0, encoding: .utf8) } ?? "") {
                                completion(.failure(validationError))
                                return
                            }
                            
                            completion(.success(event))
                        }
                    } else {
                        completion(.failure(ApiError.decodingError("Invalid JSON response format")))
                    }
                } catch {
                    completion(.failure(ApiError.decodingError("Failed to parse server response: \(error.localizedDescription)")))
                }
                
            case 400:
                let errorDetails = self?.parseErrorResponse(data: data)
                completion(.failure(ApiError.badRequest(errorDetails?.userMessage ?? "Invalid request format")))
                
            case 422:
                let errorDetails = self?.parseErrorResponse(data: data)
                completion(.failure(ApiError.validationError(errorDetails?.userMessage ?? "The text does not contain valid event information. Please try rephrasing with clearer date, time, and event details.")))
                
            case 429:
                let errorDetails = self?.parseErrorResponse(data: data)
                let retryAfter = httpResponse.value(forHTTPHeaderField: "Retry-After") ?? "60"
                completion(.failure(ApiError.rateLimitError("Too many requests. Please wait \(retryAfter) seconds before trying again.")))
                
            case 500, 502, 503, 504:
                if retryCount < maxRetries {
                    DispatchQueue.global().asyncAfter(deadline: .now() + Double(retryCount + 1)) {
                        self?.performRequestWithRetry(request: request, retryCount: retryCount + 1, completion: completion)
                    }
                    return
                } else {
                    completion(.failure(ApiError.serverError("Server is temporarily unavailable. Please try again in a few minutes.")))
                }
                
            default:
                let errorDetails = self?.parseErrorResponse(data: data)
                completion(.failure(ApiError.httpError(httpResponse.statusCode, errorDetails?.userMessage ?? "Request failed with code \(httpResponse.statusCode)")))
            }
        }.resume()
    }
    
    private func parseErrorResponse(data: Data) -> ErrorDetails? {
        do {
            if let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
               let errorObj = json["error"] as? [String: Any] {
                
                let code = errorObj["code"] as? String ?? "UNKNOWN_ERROR"
                let message = errorObj["message"] as? String ?? "An error occurred"
                let suggestion = errorObj["suggestion"] as? String
                
                let userMessage: String
                switch code {
                case "VALIDATION_ERROR":
                    userMessage = "Invalid input: \(message)"
                case "PARSING_ERROR":
                    userMessage = message + (suggestion != nil ? ". \(suggestion!)" : "")
                case "TEXT_EMPTY":
                    userMessage = "Please provide text containing event information."
                case "TEXT_TOO_LONG":
                    userMessage = "Text is too long. Please limit to 10,000 characters."
                case "INVALID_TIMEZONE":
                    userMessage = "Invalid timezone. Please check your device settings."
                case "LLM_UNAVAILABLE":
                    userMessage = "Enhanced parsing is temporarily unavailable. Your request will be processed with basic parsing."
                case "RATE_LIMIT_ERROR":
                    userMessage = message + (suggestion != nil ? ". \(suggestion!)" : "")
                case "SERVICE_UNAVAILABLE":
                    userMessage = "Service is temporarily unavailable. Please try again later."
                default:
                    userMessage = message
                }
                
                return ErrorDetails(code: code, message: message, userMessage: userMessage, suggestion: suggestion)
            }
        } catch {
            // Fallback parsing
        }
        
        return nil
    }
    
    private func validateParseResult(_ event: ParsedEvent, originalText: String) -> ApiError? {
        // Check if we got meaningful results
        if (event.title?.isEmpty ?? true) && (event.startDatetime?.isEmpty ?? true) {
            return ApiError.parsingError("Could not extract event information from the text. Please try rephrasing with clearer date, time, and event details.")
        }
        
        // Warn about low confidence
        if event.confidenceScore < 0.3 {
            return ApiError.parsingError("The text is unclear and may not contain valid event information. Please try rephrasing with specific date, time, and event details.")
        }
        
        return nil
    }
}

struct ErrorDetails {
    let code: String
    let message: String
    let userMessage: String
    let suggestion: String?
}
}

enum ApiError: LocalizedError {
    case invalidURL
    case encodingError
    case networkError(String)
    case invalidResponse
    case noData
    case decodingError(String)
    case parsingError(String)
    case badRequest(String)
    case serverError(String)
    case httpError(Int, String)
    case validationError(String)
    case timeoutError(String)
    case rateLimitError(String)
    
    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid API URL"
        case .encodingError:
            return "Failed to encode request"
        case .networkError(let message):
            return message
        case .invalidResponse:
            return "Invalid server response"
        case .noData:
            return "No data received from server"
        case .decodingError(let message):
            return message
        case .parsingError(let message):
            return message
        case .badRequest(let message):
            return message
        case .serverError(let message):
            return message
        case .httpError(_, let message):
            return message
        case .validationError(let message):
            return message
        case .timeoutError(let message):
            return message
        case .rateLimitError(let message):
            return message
        }
    }
}
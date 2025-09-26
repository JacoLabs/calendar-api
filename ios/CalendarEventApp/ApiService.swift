import Foundation

class ApiService {
    static let shared = ApiService()
    private let baseURL = "https://calendar-api-wrxz.onrender.com"
    
    private init() {}
    
    func parseText(_ text: String, completion: @escaping (Result<ParsedEvent, Error>) -> Void) {
        guard let url = URL(string: "\(baseURL)/parse") else {
            completion(.failure(ApiError.invalidURL))
            return
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let requestBody = ["text": text]
        
        do {
            request.httpBody = try JSONSerialization.data(withJSONObject: requestBody)
        } catch {
            completion(.failure(ApiError.encodingError))
            return
        }
        
        URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                completion(.failure(ApiError.networkError(error.localizedDescription)))
                return
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
                    let event = try JSONDecoder().decode(ParsedEvent.self, from: data)
                    completion(.success(event))
                } catch {
                    completion(.failure(ApiError.decodingError(error.localizedDescription)))
                }
            case 400:
                completion(.failure(ApiError.badRequest("Invalid request format")))
            case 500:
                completion(.failure(ApiError.serverError("Server error occurred")))
            default:
                completion(.failure(ApiError.httpError(httpResponse.statusCode)))
            }
        }.resume()
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
    case httpError(Int)
    
    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid API URL"
        case .encodingError:
            return "Failed to encode request"
        case .networkError(let message):
            return "Network error: \(message)"
        case .invalidResponse:
            return "Invalid server response"
        case .noData:
            return "No data received from server"
        case .decodingError(let message):
            return "Failed to decode response: \(message)"
        case .parsingError(let message):
            return "Parsing failed: \(message)"
        case .badRequest(let message):
            return "Bad request: \(message)"
        case .serverError(let message):
            return "Server error: \(message)"
        case .httpError(let code):
            return "HTTP error: \(code)"
        }
    }
}
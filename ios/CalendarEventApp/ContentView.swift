import SwiftUI

struct ContentView: View {
    @State private var inputText: String = ""
    @State private var isLoading: Bool = false
    @State private var parsedEvent: ParsedEvent?
    @State private var errorMessage: String?
    @State private var showingResult: Bool = false
    
    var body: some View {
        NavigationView {
            VStack(spacing: 24) {
                Image(systemName: "calendar.badge.plus")
                    .font(.system(size: 64))
                    .foregroundColor(.blue)
                
                Text("Calendar Event Creator")
                    .font(.largeTitle)
                    .fontWeight(.bold)
                    .multilineTextAlignment(.center)
                
                Text("Enter text containing event information to create a calendar event.")
                    .font(.body)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal)
                
                VStack(alignment: .leading, spacing: 12) {
                    Text("Enter Event Text:")
                        .font(.headline)
                    
                    TextEditor(text: $inputText)
                        .frame(minHeight: 100)
                        .padding(8)
                        .background(Color(.systemGray6))
                        .cornerRadius(8)
                        .overlay(
                            RoundedRectangle(cornerRadius: 8)
                                .stroke(Color(.systemGray4), lineWidth: 1)
                        )
                    
                    if inputText.isEmpty {
                        Text("Example: \"Meeting with John tomorrow at 2pm at Starbucks\"")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }
                
                Button(action: parseEvent) {
                    HStack {
                        if isLoading {
                            ProgressView()
                                .scaleEffect(0.8)
                        } else {
                            Image(systemName: "calendar.badge.plus")
                        }
                        Text(isLoading ? "Parsing..." : "Create Event")
                    }
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(inputText.isEmpty ? Color(.systemGray4) : Color.blue)
                    .foregroundColor(.white)
                    .cornerRadius(10)
                }
                .disabled(inputText.isEmpty || isLoading)
                
                if let errorMessage = errorMessage {
                    Text(errorMessage)
                        .foregroundColor(.red)
                        .font(.caption)
                        .multilineTextAlignment(.center)
                }
                
                Spacer()
            }
            .padding()
            .navigationTitle("Event Creator")
            .navigationBarTitleDisplayMode(.inline)
        }
        .sheet(isPresented: $showingResult) {
            if let event = parsedEvent {
                EventResultView(event: event) {
                    showingResult = false
                    inputText = ""
                    parsedEvent = nil
                }
            }
        }
    }
    
    private func parseEvent() {
        guard !inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }
        
        isLoading = true
        errorMessage = nil
        
        ApiService.shared.parseText(inputText) { result in
            DispatchQueue.main.async {
                isLoading = false
                
                switch result {
                case .success(let event):
                    parsedEvent = event
                    showingResult = true
                case .failure(let error):
                    errorMessage = error.localizedDescription
                }
            }
        }
    }
}

#Preview {
    ContentView()
}
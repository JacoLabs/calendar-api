import SwiftUI
import EventKit

struct EventResultView: View {
    let event: ParsedEvent
    let onDismiss: () -> Void
    
    @State private var showingCalendar = false
    @State private var calendarError: String?
    
    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                // Header
                VStack(spacing: 8) {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.system(size: 50))
                        .foregroundColor(.green)
                    
                    Text("Event Parsed Successfully")
                        .font(.title2)
                        .fontWeight(.semibold)
                    
                    Text("Confidence: \(Int(event.confidenceScore * 100))%")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                
                // Event Details
                VStack(spacing: 16) {
                    EventDetailRow(
                        icon: "text.alignleft",
                        title: "Title",
                        value: event.displayTitle
                    )
                    
                    EventDetailRow(
                        icon: "calendar",
                        title: "Start Date",
                        value: event.formattedStartDate
                    )
                    
                    if event.endDatetime != nil {
                        EventDetailRow(
                            icon: "clock",
                            title: "End Time",
                            value: event.formattedEndDate
                        )
                    }
                    
                    if event.location != nil {
                        EventDetailRow(
                            icon: "location",
                            title: "Location",
                            value: event.displayLocation
                        )
                    }
                    
                    if event.description != nil && !event.description!.isEmpty {
                        EventDetailRow(
                            icon: "note.text",
                            title: "Description",
                            value: event.displayDescription
                        )
                    }
                }
                .padding()
                .background(Color(.systemGray6))
                .cornerRadius(12)
                
                if let calendarError = calendarError {
                    Text(calendarError)
                        .foregroundColor(.red)
                        .font(.caption)
                        .multilineTextAlignment(.center)
                }
                
                // Action Buttons
                VStack(spacing: 12) {
                    Button(action: openCalendarApp) {
                        HStack {
                            Image(systemName: "calendar.badge.plus")
                            Text("Add to Calendar")
                        }
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color.blue)
                        .foregroundColor(.white)
                        .cornerRadius(10)
                    }
                    
                    Button(action: onDismiss) {
                        Text("Done")
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(Color(.systemGray5))
                            .foregroundColor(.primary)
                            .cornerRadius(10)
                    }
                }
                
                Spacer()
            }
            .padding()
            .navigationTitle("Parsed Event")
            .navigationBarTitleDisplayMode(.inline)
            .navigationBarItems(trailing: Button("Close", action: onDismiss))
        }
    }
    
    private func openCalendarApp() {
        let eventStore = EKEventStore()
        
        eventStore.requestAccess(to: .event) { granted, error in
            DispatchQueue.main.async {
                if let error = error {
                    calendarError = "Calendar access error: \(error.localizedDescription)"
                    return
                }
                
                guard granted else {
                    calendarError = "Calendar access denied. Please enable in Settings."
                    return
                }
                
                createCalendarEvent(eventStore: eventStore)
            }
        }
    }
    
    private func createCalendarEvent(eventStore: EKEventStore) {
        let calendarEvent = EKEvent(eventStore: eventStore)
        calendarEvent.title = event.displayTitle
        
        // Parse start date
        if let startDatetime = event.startDatetime {
            let formatter = ISO8601DateFormatter()
            
            if let startDate = formatter.date(from: startDatetime) {
                calendarEvent.startDate = startDate
                
                // Parse end date or default to 1 hour later
                if let endDatetime = event.endDatetime,
                   let endDate = formatter.date(from: endDatetime) {
                    calendarEvent.endDate = endDate
                } else {
                    calendarEvent.endDate = startDate.addingTimeInterval(3600) // 1 hour
                }
            } else {
                // Fallback to current time if parsing fails
                calendarEvent.startDate = Date()
                calendarEvent.endDate = Date().addingTimeInterval(3600)
            }
        } else {
            // Default to current time
            calendarEvent.startDate = Date()
            calendarEvent.endDate = Date().addingTimeInterval(3600)
        }
        
        if let location = event.location, !location.isEmpty {
            calendarEvent.location = location
        }
        
        if let description = event.description, !description.isEmpty {
            calendarEvent.notes = description
        }
        
        calendarEvent.calendar = eventStore.defaultCalendarForNewEvents
        
        do {
            try eventStore.save(calendarEvent, span: .thisEvent)
            
            // Open the Calendar app
            if let url = URL(string: "calshow://") {
                if UIApplication.shared.canOpenURL(url) {
                    UIApplication.shared.open(url)
                }
            }
            
            onDismiss()
        } catch {
            calendarError = "Failed to create event: \(error.localizedDescription)"
        }
    }
}

struct EventDetailRow: View {
    let icon: String
    let title: String
    let value: String
    
    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: icon)
                .foregroundColor(.blue)
                .frame(width: 20)
            
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.caption)
                    .foregroundColor(.secondary)
                
                Text(value)
                    .font(.body)
            }
            
            Spacer()
        }
    }
}

#Preview {
    EventResultView(
        event: ParsedEvent(
            title: "Meeting with John",
            startDatetime: "2024-01-15T14:00:00+00:00",
            endDatetime: "2024-01-15T15:00:00+00:00",
            location: "Starbucks",
            description: "Discuss project updates",
            confidenceScore: 0.85,
            allDay: false,
            timezone: "UTC"
        ),
        onDismiss: {}
    )
}
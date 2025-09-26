import UIKit
import EventKit
import EventKitUI

/**
 * Action Extension for handling selected text from other apps.
 * Appears in the Share Sheet when text is selected.
 */
class ActionViewController: UIViewController {
    
    private let eventStore = EKEventStore()
    private let apiService = ApiService()
    
    override func viewDidLoad() {
        super.viewDidLoad()
        
        // Process the input text
        processInputText()
    }
    
    private func processInputText() {
        guard let extensionItem = extensionContext?.inputItems.first as? NSExtensionItem,
              let itemProvider = extensionItem.attachments?.first else {
            showError("No text found")
            return
        }
        
        // Check if we can load text
        if itemProvider.hasItemConformingToTypeIdentifier("public.text") {
            itemProvider.loadItem(forTypeIdentifier: "public.text", options: nil) { [weak self] (item, error) in
                DispatchQueue.main.async {
                    if let error = error {
                        self?.showError("Failed to load text: \(error.localizedDescription)")
                        return
                    }
                    
                    let text: String
                    if let stringItem = item as? String {
                        text = stringItem
                    } else if let urlItem = item as? URL {
                        text = urlItem.absoluteString
                    } else {
                        self?.showError("Unsupported text format")
                        return
                    }
                    
                    self?.parseTextAndCreateEvent(text)
                }
            }
        } else {
            showError("No text content available")
        }
    }
    
    private func parseTextAndCreateEvent(_ text: String) {
        // Show loading indicator
        let loadingAlert = UIAlertController(title: "Processing", message: "Parsing event information...", preferredStyle: .alert)
        present(loadingAlert, animated: true)
        
        Task {
            do {
                // Get current timezone and locale
                let timezone = TimeZone.current.identifier
                let locale = Locale.current.identifier
                let now = Date()
                
                // Call API to parse text
                let parseResult = try await apiService.parseText(
                    text: text,
                    timezone: timezone,
                    locale: locale,
                    now: now
                )
                
                await MainActor.run {
                    loadingAlert.dismiss(animated: true) {
                        self.presentEventEditor(with: parseResult, originalText: text)
                    }
                }
                
            } catch {
                await MainActor.run {
                    loadingAlert.dismiss(animated: true) {
                        self.showError("Failed to parse text: \(error.localizedDescription)")
                    }
                }
            }
        }
    }
    
    private func presentEventEditor(with parseResult: ParseResult, originalText: String) {
        // Request calendar access
        eventStore.requestAccess(to: .event) { [weak self] (granted, error) in
            DispatchQueue.main.async {
                if !granted {
                    self?.showError("Calendar access is required to create events")
                    return
                }
                
                // Create event with parsed data
                let event = EKEvent(eventStore: self!.eventStore)
                
                // Set basic properties
                event.title = parseResult.title ?? "New Event"
                event.notes = parseResult.description ?? originalText
                
                // Set location
                if let location = parseResult.location {
                    event.location = location
                }
                
                // Set dates
                if let startDateString = parseResult.startDateTime,
                   let startDate = self?.parseISODateTime(startDateString) {
                    event.startDate = startDate
                    
                    // Set end date (default to +30 minutes if not provided)
                    if let endDateString = parseResult.endDateTime,
                       let endDate = self?.parseISODateTime(endDateString) {
                        event.endDate = endDate
                    } else {
                        event.endDate = startDate.addingTimeInterval(30 * 60) // +30 minutes
                    }
                } else {
                    // Default to current time if no date parsed
                    event.startDate = Date()
                    event.endDate = Date().addingTimeInterval(60 * 60) // +1 hour
                }
                
                // Set all-day if applicable
                event.isAllDay = parseResult.allDay
                
                // Set default calendar
                event.calendar = self!.eventStore.defaultCalendarForNewEvents
                
                // Present event edit controller
                let eventEditController = EKEventEditViewController()
                eventEditController.event = event
                eventEditController.eventStore = self!.eventStore
                eventEditController.editViewDelegate = self
                
                self?.present(eventEditController, animated: true)
            }
        }
    }
    
    private func parseISODateTime(_ isoString: String) -> Date? {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        
        if let date = formatter.date(from: isoString) {
            return date
        }
        
        // Fallback for different ISO formats
        formatter.formatOptions = [.withInternetDateTime]
        return formatter.date(from: isoString)
    }
    
    private func showError(_ message: String) {
        let alert = UIAlertController(title: "Error", message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "OK", style: .default) { _ in
            self.extensionContext?.completeRequest(returningItems: nil, completionHandler: nil)
        })
        present(alert, animated: true)
    }
}

// MARK: - EKEventEditViewDelegate

extension ActionViewController: EKEventEditViewDelegate {
    func eventEditViewController(_ controller: EKEventEditViewController, didCompleteWith action: EKEventEditViewAction) {
        controller.dismiss(animated: true) {
            // Complete the extension request
            self.extensionContext?.completeRequest(returningItems: nil, completionHandler: nil)
        }
    }
}
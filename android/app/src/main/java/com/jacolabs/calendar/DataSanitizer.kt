package com.jacolabs.calendar

import android.util.Log
import java.text.SimpleDateFormat
import java.util.*
import java.util.regex.Pattern

/**
 * Utility class for data sanitization operations.
 * Provides specialized sanitization methods for different data types.
 */
class DataSanitizer {
    
    companion object {
        private const val TAG = "DataSanitizer"
        
        // Sanitization patterns
        private val HTML_TAGS = Pattern.compile("<[^>]+>")
        private val SCRIPT_CONTENT = Pattern.compile("<script[^>]*>.*?</script>", Pattern.CASE_INSENSITIVE or Pattern.DOTALL)
        private val EXCESSIVE_PUNCTUATION = Pattern.compile("[.!?]{3,}")
        private val MULTIPLE_SPACES = Pattern.compile("\\s{2,}")
        private val CONTROL_CHARS = Pattern.compile("[\\x00-\\x1F\\x7F]")
        private val UNICODE_CONTROL = Pattern.compile("\\p{Cntrl}")
        
        // Safe character sets
        private val SAFE_TITLE_CHARS = Pattern.compile("[^\\p{L}\\p{N}\\p{P}\\p{Z}]")
        private val SAFE_LOCATION_CHARS = Pattern.compile("[^\\p{L}\\p{N}\\p{P}\\p{Z}]")
        
        /**
         * Sanitizes text for use as event title
         */
        fun sanitizeTitle(title: String?): String {
            if (title.isNullOrBlank()) return ""
            
            var sanitized = title
            
            // Remove HTML tags and script content
            sanitized = SCRIPT_CONTENT.matcher(sanitized).replaceAll("")
            sanitized = HTML_TAGS.matcher(sanitized).replaceAll("")
            
            // Remove control characters
            sanitized = CONTROL_CHARS.matcher(sanitized).replaceAll("")
            sanitized = UNICODE_CONTROL.matcher(sanitized).replaceAll("")
            
            // Normalize punctuation
            sanitized = EXCESSIVE_PUNCTUATION.matcher(sanitized).replaceAll(".")
            
            // Normalize whitespace
            sanitized = MULTIPLE_SPACES.matcher(sanitized).replaceAll(" ")
            sanitized = sanitized.trim()
            
            // Remove unsafe characters
            sanitized = SAFE_TITLE_CHARS.matcher(sanitized).replaceAll("")
            
            return sanitized
        }
        
        /**
         * Sanitizes text for use as location
         */
        fun sanitizeLocation(location: String?): String? {
            if (location.isNullOrBlank()) return null
            
            var sanitized = location
            
            // Remove HTML and control characters
            sanitized = HTML_TAGS.matcher(sanitized).replaceAll("")
            sanitized = CONTROL_CHARS.matcher(sanitized).replaceAll("")
            
            // Normalize whitespace
            sanitized = MULTIPLE_SPACES.matcher(sanitized).replaceAll(" ")
            sanitized = sanitized.trim()
            
            // Remove unsafe characters
            sanitized = SAFE_LOCATION_CHARS.matcher(sanitized).replaceAll("")
            
            return if (sanitized.isBlank()) null else sanitized
        }
        
        /**
         * Sanitizes description text
         */
        fun sanitizeDescription(description: String?): String {
            if (description.isNullOrBlank()) return ""
            
            var sanitized = description
            
            // Remove script content but preserve some HTML formatting
            sanitized = SCRIPT_CONTENT.matcher(sanitized).replaceAll("")
            
            // Remove dangerous control characters but preserve newlines and tabs
            sanitized = sanitized.replace(Regex("[\\x00-\\x08\\x0B\\x0C\\x0E-\\x1F\\x7F]"), "")
            
            // Normalize excessive whitespace but preserve paragraph breaks
            sanitized = sanitized.replace(Regex("[ \\t]+"), " ")
            sanitized = sanitized.replace(Regex("\\n{4,}"), "\n\n\n")
            
            return sanitized.trim()
        }
    }
}
package com.jacolabs.calendar

import android.content.Context
import android.content.SharedPreferences

/**
 * Configuration manager for data validation behavior.
 * Allows customization of validation rules and thresholds.
 */
class ValidationConfig(private val context: Context) {
    
    companion object {
        private const val PREFS_NAME = "validation_config"
        
        // Default configuration values
        const val DEFAULT_MIN_CONFIDENCE_THRESHOLD = 0.3
        const val DEFAULT_WARNING_CONFIDENCE_THRESHOLD = 0.6
        const val DEFAULT_MAX_TITLE_LENGTH = 200
        const val DEFAULT_MAX_DESCRIPTION_LENGTH = 5000
        const val DEFAULT_MAX_LOCATION_LENGTH = 500
        const val DEFAULT_MIN_DURATION_MINUTES = 1
        const val DEFAULT_MAX_DURATION_MINUTES = 10080 // 1 week
        const val DEFAULT_ENABLE_STRICT_VALIDATION = false
        const val DEFAULT_ENABLE_AUTO_SANITIZATION = true
        const val DEFAULT_ENABLE_SMART_DEFAULTS = true
    }
    
    private val prefs: SharedPreferences = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
    
    // Confidence thresholds
    var minConfidenceThreshold: Double
        get() = prefs.getFloat("min_confidence_threshold", DEFAULT_MIN_CONFIDENCE_THRESHOLD.toFloat()).toDouble()
        set(value) = prefs.edit().putFloat("min_confidence_threshold", value.toFloat()).apply()
    
    var warningConfidenceThreshold: Double
        get() = prefs.getFloat("warning_confidence_threshold", DEFAULT_WARNING_CONFIDENCE_THRESHOLD.toFloat()).toDouble()
        set(value) = prefs.edit().putFloat("warning_confidence_threshold", value.toFloat()).apply()
    
    // Length limits
    var maxTitleLength: Int
        get() = prefs.getInt("max_title_length", DEFAULT_MAX_TITLE_LENGTH)
        set(value) = prefs.edit().putInt("max_title_length", value).apply()
    
    var maxDescriptionLength: Int
        get() = prefs.getInt("max_description_length", DEFAULT_MAX_DESCRIPTION_LENGTH)
        set(value) = prefs.edit().putInt("max_description_length", value).apply()
    
    var maxLocationLength: Int
        get() = prefs.getInt("max_location_length", DEFAULT_MAX_LOCATION_LENGTH)
        set(value) = prefs.edit().putInt("max_location_length", value).apply()
    
    // Duration limits
    var minDurationMinutes: Int
        get() = prefs.getInt("min_duration_minutes", DEFAULT_MIN_DURATION_MINUTES)
        set(value) = prefs.edit().putInt("min_duration_minutes", value).apply()
    
    var maxDurationMinutes: Int
        get() = prefs.getInt("max_duration_minutes", DEFAULT_MAX_DURATION_MINUTES)
        set(value) = prefs.edit().putInt("max_duration_minutes", value).apply()
    
    // Validation behavior flags
    var enableStrictValidation: Boolean
        get() = prefs.getBoolean("enable_strict_validation", DEFAULT_ENABLE_STRICT_VALIDATION)
        set(value) = prefs.edit().putBoolean("enable_strict_validation", value).apply()
    
    var enableAutoSanitization: Boolean
        get() = prefs.getBoolean("enable_auto_sanitization", DEFAULT_ENABLE_AUTO_SANITIZATION)
        set(value) = prefs.edit().putBoolean("enable_auto_sanitization", value).apply()
    
    var enableSmartDefaults: Boolean
        get() = prefs.getBoolean("enable_smart_defaults", DEFAULT_ENABLE_SMART_DEFAULTS)
        set(value) = prefs.edit().putBoolean("enable_smart_defaults", value).apply()
    
    /**
     * Resets all configuration to defaults
     */
    fun resetToDefaults() {
        prefs.edit().clear().apply()
    }
    
    /**
     * Gets current configuration as a map
     */
    fun toMap(): Map<String, Any> {
        return mapOf(
            "minConfidenceThreshold" to minConfidenceThreshold,
            "warningConfidenceThreshold" to warningConfidenceThreshold,
            "maxTitleLength" to maxTitleLength,
            "maxDescriptionLength" to maxDescriptionLength,
            "maxLocationLength" to maxLocationLength,
            "minDurationMinutes" to minDurationMinutes,
            "maxDurationMinutes" to maxDurationMinutes,
            "enableStrictValidation" to enableStrictValidation,
            "enableAutoSanitization" to enableAutoSanitization,
            "enableSmartDefaults" to enableSmartDefaults
        )
    }
}
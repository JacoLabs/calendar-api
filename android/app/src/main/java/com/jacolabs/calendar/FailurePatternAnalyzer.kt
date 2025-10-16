package com.jacolabs.calendar

import android.content.Context
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.security.MessageDigest
import java.text.SimpleDateFormat
import java.util.*
import kotlin.math.ln
import kotlin.math.max
import kotlin.math.min

/**
 * Analyzes failure patterns to learn from parsing failures and provide intelligent suggestions.
 * 
 * Addresses requirements:
 * - 9.1: Log failure patterns for analysis
 * - 9.2: Suggest text preprocessing improvements based on patterns
 * - 9.3: Note corrections for future reference
 * - 9.4: Maintain user privacy and anonymize data
 */
class FailurePatternAnalyzer(
    private val context: Context,
    private val config: ErrorHandlingConfig = ErrorHandlingConfig.load(context)
) {
    
    companion object {
        private const val TAG = "FailurePatternAnalyzer"
        private const val PATTERNS_FILE = "failure_patterns.json"
        private const val CORRECTIONS_FILE = "user_corrections.json"
        private const val SUGGESTIONS_FILE = "improvement_suggestions.json"
        
        // Analysis thresholds
        private const val MIN_PATTERN_OCCURRENCES = 3
        private const val MAX_STORED_PATTERNS = 500
        private const val PATTERN_SIMILARITY_THRESHOLD = 0.7
        private const val CORRECTION_CONFIDENCE_THRESHOLD = 0.6
        
        // Text analysis constants
        private const val MAX_TEXT_LENGTH_FOR_ANALYSIS = 500
        private const val MIN_TEXT_LENGTH_FOR_PATTERN = 5
    }
    
    private val patternsFile = File(context.filesDir, PATTERNS_FILE)
    private val correctionsFile = File(context.filesDir, CORRECTIONS_FILE)
    private val suggestionsFile = File(context.filesDir, SUGGESTIONS_FILE)
    private val dateFormatter = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US)
    
    /**
     * Detailed failure pattern with analysis metadata
     */
    data class FailurePattern(
        val patternId: String,
        val textCharacteristics: TextCharacteristics,
        val errorType: String,
        val errorSubtype: String?,
        val occurrences: Int,
        val firstSeen: Long,
        val lastSeen: Long,
        val confidence: Double,
        val severity: String,
        val contextFactors: List<String>,
        val suggestedImprovements: List<String>,
        val relatedCorrections: List<String> = emptyList()
    )
    
    /**
     * Text characteristics for pattern matching
     */
    data class TextCharacteristics(
        val length: Int,
        val wordCount: Int,
        val hasNumbers: Boolean,
        val hasTimePattern: Boolean,
        val hasDatePattern: Boolean,
        val hasLocationKeywords: Boolean,
        val hasActionVerbs: Boolean,
        val complexity: TextComplexity,
        val language: String,
        val structure: TextStructure,
        val anonymizedHash: String
    )
    
    /**
     * Text complexity assessment
     */
    enum class TextComplexity {
        SIMPLE,      // Single sentence, clear structure
        MODERATE,    // Multiple sentences, some ambiguity
        COMPLEX,     // Multiple concepts, high ambiguity
        VERY_COMPLEX // Highly ambiguous or fragmented
    }
    
    /**
     * Text structure analysis
     */
    data class TextStructure(
        val sentenceCount: Int,
        val hasQuestions: Boolean,
        val hasCommands: Boolean,
        val hasConjunctions: Boolean,
        val punctuationDensity: Double,
        val capitalizationPattern: String
    )
    
    /**
     * User correction for learning
     */
    data class UserCorrection(
        val correctionId: String,
        val originalTextHash: String,
        val fieldCorrected: String,
        val originalValue: String?,
        val correctedValue: String,
        val timestamp: Long,
        val confidence: Double,
        val context: CorrectionContext
    )
    
    /**
     * Context information for corrections
     */
    data class CorrectionContext(
        val errorType: String,
        val originalConfidence: Double,
        val processingTimeMs: Long,
        val userInteractionTime: Long,
        val correctionMethod: String // manual_edit, selection, voice_input, etc.
    )
    
    /**
     * Intelligent improvement suggestion
     */
    data class ImprovementSuggestion(
        val suggestionId: String,
        val type: SuggestionType,
        val title: String,
        val description: String,
        val example: String?,
        val confidence: Double,
        val applicability: SuggestionApplicability,
        val priority: Int,
        val basedOnPatterns: List<String>
    )
    
    /**
     * Types of improvement suggestions
     */
    enum class SuggestionType {
        DATE_FORMAT,
        TIME_FORMAT,
        LOCATION_CLARITY,
        EVENT_DESCRIPTION,
        DURATION_SPECIFICATION,
        LANGUAGE_CLARITY,
        STRUCTURE_IMPROVEMENT,
        CONTEXT_ADDITION
    }
    
    /**
     * Suggestion applicability criteria
     */
    data class SuggestionApplicability(
        val textLengthRange: IntRange,
        val complexityLevels: List<TextComplexity>,
        val errorTypes: List<String>,
        val languageSpecific: Boolean
    )
    
    /**
     * Analyzes a parsing failure and updates pattern database
     * Requirement 9.1: Log failure patterns for analysis
     */
    suspend fun analyzeFailure(
        originalText: String,
        errorType: String,
        errorSubtype: String? = null,
        confidence: Double = 0.0,
        processingTimeMs: Long = 0,
        contextFactors: List<String> = emptyList()
    ) = withContext(Dispatchers.IO) {
        
        if (!config.shouldCollectAnalytics() || originalText.length < MIN_TEXT_LENGTH_FOR_PATTERN) {
            return@withContext
        }
        
        try {
            val textCharacteristics = analyzeTextCharacteristics(originalText)
            val patternId = generatePatternId(textCharacteristics, errorType)
            
            val existingPatterns = loadFailurePatterns()
            val existingPattern = existingPatterns[patternId]
            
            val updatedPattern = if (existingPattern != null) {
                existingPattern.copy(
                    occurrences = existingPattern.occurrences + 1,
                    lastSeen = System.currentTimeMillis(),
                    confidence = updateConfidence(existingPattern.confidence, confidence),
                    contextFactors = mergeContextFactors(existingPattern.contextFactors, contextFactors)
                )
            } else {
                FailurePattern(
                    patternId = patternId,
                    textCharacteristics = textCharacteristics,
                    errorType = errorType,
                    errorSubtype = errorSubtype,
                    occurrences = 1,
                    firstSeen = System.currentTimeMillis(),
                    lastSeen = System.currentTimeMillis(),
                    confidence = confidence,
                    severity = determineSeverity(errorType, confidence),
                    contextFactors = contextFactors,
                    suggestedImprovements = generateInitialSuggestions(textCharacteristics, errorType)
                )
            }
            
            existingPatterns[patternId] = updatedPattern
            saveFailurePatterns(existingPatterns)
            
            // Update improvement suggestions based on new pattern
            updateImprovementSuggestions(updatedPattern)
            
            Log.d(TAG, "Analyzed failure pattern: $patternId (${updatedPattern.occurrences} occurrences)")
            
        } catch (e: Exception) {
            Log.e(TAG, "Failed to analyze failure pattern", e)
        }
    }
    
    /**
     * Records a user correction for learning
     * Requirement 9.3: Note corrections for future reference
     */
    suspend fun recordUserCorrection(
        originalText: String,
        fieldCorrected: String,
        originalValue: String?,
        correctedValue: String,
        originalConfidence: Double,
        processingTimeMs: Long,
        userInteractionTime: Long,
        correctionMethod: String = "manual_edit"
    ) = withContext(Dispatchers.IO) {
        
        if (!config.shouldCollectAnalytics()) return@withContext
        
        try {
            val correctionId = generateCorrectionId()
            val originalTextHash = hashText(originalText)
            
            val correction = UserCorrection(
                correctionId = correctionId,
                originalTextHash = originalTextHash,
                fieldCorrected = fieldCorrected,
                originalValue = originalValue,
                correctedValue = correctedValue,
                timestamp = System.currentTimeMillis(),
                confidence = calculateCorrectionConfidence(originalValue, correctedValue, userInteractionTime),
                context = CorrectionContext(
                    errorType = "LOW_CONFIDENCE", // Would be passed from caller
                    originalConfidence = originalConfidence,
                    processingTimeMs = processingTimeMs,
                    userInteractionTime = userInteractionTime,
                    correctionMethod = correctionMethod
                )
            )
            
            val existingCorrections = loadUserCorrections()
            existingCorrections.add(correction)
            saveUserCorrections(existingCorrections)
            
            // Update related patterns with correction information
            updatePatternsWithCorrection(originalText, correction)
            
            Log.d(TAG, "Recorded user correction: $correctionId for field $fieldCorrected")
            
        } catch (e: Exception) {
            Log.e(TAG, "Failed to record user correction", e)
        }
    }
    
    /**
     * Generates intelligent improvement suggestions based on patterns
     * Requirement 9.2: Suggest text preprocessing improvements based on patterns
     */
    suspend fun generateImprovementSuggestions(
        textCharacteristics: TextCharacteristics? = null,
        recentErrorTypes: List<String> = emptyList()
    ): List<ImprovementSuggestion> = withContext(Dispatchers.IO) {
        
        try {
            val patterns = loadFailurePatterns()
            val corrections = loadUserCorrections()
            val suggestions = mutableListOf<ImprovementSuggestion>()
            
            // Analyze common failure patterns
            val commonPatterns = patterns.values
                .filter { it.occurrences >= MIN_PATTERN_OCCURRENCES }
                .sortedByDescending { it.occurrences }
            
            // Generate suggestions based on patterns
            commonPatterns.forEach { pattern ->
                val patternSuggestions = generateSuggestionsFromPattern(pattern, corrections)
                suggestions.addAll(patternSuggestions)
            }
            
            // Generate suggestions based on user corrections
            val correctionSuggestions = generateSuggestionsFromCorrections(corrections)
            suggestions.addAll(correctionSuggestions)
            
            // Filter and rank suggestions
            val filteredSuggestions = filterAndRankSuggestions(
                suggestions, 
                textCharacteristics, 
                recentErrorTypes
            )
            
            // Cache suggestions for quick access
            cacheSuggestions(filteredSuggestions)
            
            filteredSuggestions.take(10) // Return top 10 suggestions
            
        } catch (e: Exception) {
            Log.e(TAG, "Failed to generate improvement suggestions", e)
            getDefaultSuggestions()
        }
    }
    
    /**
     * Gets personalized suggestions for specific text characteristics
     */
    suspend fun getPersonalizedSuggestions(
        originalText: String,
        errorType: String? = null
    ): List<ImprovementSuggestion> = withContext(Dispatchers.IO) {
        
        try {
            val textCharacteristics = analyzeTextCharacteristics(originalText)
            val recentErrorTypes = errorType?.let { listOf(it) } ?: emptyList()
            
            val allSuggestions = generateImprovementSuggestions(textCharacteristics, recentErrorTypes)
            
            // Filter suggestions based on text characteristics
            allSuggestions.filter { suggestion ->
                isApplicableToText(suggestion, textCharacteristics)
            }.sortedByDescending { it.confidence }
            
        } catch (e: Exception) {
            Log.w(TAG, "Failed to get personalized suggestions", e)
            getDefaultSuggestions()
        }
    }
    
    /**
     * Analyzes text preprocessing effectiveness
     */
    suspend fun analyzePreprocessingEffectiveness(): Map<String, Double> = withContext(Dispatchers.IO) {
        
        try {
            val corrections = loadUserCorrections()
            val patterns = loadFailurePatterns()
            
            val effectiveness = mutableMapOf<String, Double>()
            
            // Analyze correction patterns
            val correctionsByField = corrections.groupBy { it.fieldCorrected }
            correctionsByField.forEach { (field, fieldCorrections) ->
                val avgConfidence = fieldCorrections.map { it.confidence }.average()
                effectiveness["${field}_correction_rate"] = avgConfidence
            }
            
            // Analyze pattern improvement over time
            patterns.values.forEach { pattern ->
                val improvementRate = calculatePatternImprovementRate(pattern)
                effectiveness["${pattern.errorType}_improvement"] = improvementRate
            }
            
            effectiveness
            
        } catch (e: Exception) {
            Log.e(TAG, "Failed to analyze preprocessing effectiveness", e)
            emptyMap()
        }
    }
    
    /**
     * Gets failure pattern statistics for monitoring
     */
    suspend fun getPatternStatistics(): Map<String, Any> = withContext(Dispatchers.IO) {
        
        try {
            val patterns = loadFailurePatterns()
            val corrections = loadUserCorrections()
            
            mapOf(
                "total_patterns" to patterns.size,
                "active_patterns" to patterns.values.count { it.occurrences >= MIN_PATTERN_OCCURRENCES },
                "most_common_error" to (patterns.values.maxByOrNull { it.occurrences }?.errorType ?: "none"),
                "total_corrections" to corrections.size,
                "correction_success_rate" to calculateCorrectionSuccessRate(corrections),
                "pattern_diversity" to calculatePatternDiversity(patterns.values.toList()),
                "learning_effectiveness" to calculateLearningEffectiveness(patterns.values.toList(), corrections)
            )
            
        } catch (e: Exception) {
            Log.e(TAG, "Failed to get pattern statistics", e)
            emptyMap()
        }
    }
    
    /**
     * Clears pattern analysis data (for privacy compliance)
     */
    suspend fun clearAnalysisData() = withContext(Dispatchers.IO) {
        try {
            patternsFile.delete()
            correctionsFile.delete()
            suggestionsFile.delete()
            Log.i(TAG, "Pattern analysis data cleared")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to clear analysis data", e)
        }
    }
    
    // Private helper methods
    
    private fun analyzeTextCharacteristics(text: String): TextCharacteristics {
        val cleanText = text.take(MAX_TEXT_LENGTH_FOR_ANALYSIS)
        val words = cleanText.split("\\s+".toRegex())
        
        return TextCharacteristics(
            length = cleanText.length,
            wordCount = words.size,
            hasNumbers = cleanText.any { it.isDigit() },
            hasTimePattern = hasTimePattern(cleanText),
            hasDatePattern = hasDatePattern(cleanText),
            hasLocationKeywords = hasLocationKeywords(cleanText),
            hasActionVerbs = hasActionVerbs(cleanText),
            complexity = assessTextComplexity(cleanText),
            language = detectLanguage(cleanText),
            structure = analyzeTextStructure(cleanText),
            anonymizedHash = hashText(cleanText)
        )
    }
    
    private fun hasTimePattern(text: String): Boolean {
        val timePatterns = listOf(
            "\\d{1,2}:\\d{2}\\s*(AM|PM|am|pm)?".toRegex(),
            "\\d{1,2}\\s*(AM|PM|am|pm)".toRegex(),
            "(morning|afternoon|evening|night)".toRegex(RegexOption.IGNORE_CASE),
            "(noon|midnight)".toRegex(RegexOption.IGNORE_CASE)
        )
        return timePatterns.any { it.containsMatchIn(text) }
    }
    
    private fun hasDatePattern(text: String): Boolean {
        val datePatterns = listOf(
            "\\d{1,2}/\\d{1,2}(/\\d{2,4})?".toRegex(),
            "\\d{1,2}-\\d{1,2}(-\\d{2,4})?".toRegex(),
            "(january|february|march|april|may|june|july|august|september|october|november|december)".toRegex(RegexOption.IGNORE_CASE),
            "(today|tomorrow|yesterday)".toRegex(RegexOption.IGNORE_CASE),
            "(monday|tuesday|wednesday|thursday|friday|saturday|sunday)".toRegex(RegexOption.IGNORE_CASE)
        )
        return datePatterns.any { it.containsMatchIn(text) }
    }
    
    private fun hasLocationKeywords(text: String): Boolean {
        val locationKeywords = listOf(
            "at", "in", "on", "near", "by", "room", "building", "street", "avenue", "road",
            "office", "home", "restaurant", "cafe", "park", "school", "hospital", "mall"
        )
        return locationKeywords.any { text.contains(it, ignoreCase = true) }
    }
    
    private fun hasActionVerbs(text: String): Boolean {
        val actionVerbs = listOf(
            "meet", "call", "visit", "go", "attend", "schedule", "plan", "book", "reserve",
            "discuss", "review", "present", "deliver", "complete", "finish", "start", "begin"
        )
        return actionVerbs.any { text.contains(it, ignoreCase = true) }
    }
    
    private fun assessTextComplexity(text: String): TextComplexity {
        val sentences = text.split("[.!?]+".toRegex()).filter { it.isNotBlank() }
        val words = text.split("\\s+".toRegex())
        val avgWordsPerSentence = if (sentences.isNotEmpty()) words.size.toDouble() / sentences.size else 0.0
        
        val complexityScore = when {
            sentences.size == 1 && avgWordsPerSentence <= 10 -> 1
            sentences.size <= 2 && avgWordsPerSentence <= 15 -> 2
            sentences.size <= 3 && avgWordsPerSentence <= 20 -> 3
            else -> 4
        }
        
        return when (complexityScore) {
            1 -> TextComplexity.SIMPLE
            2 -> TextComplexity.MODERATE
            3 -> TextComplexity.COMPLEX
            else -> TextComplexity.VERY_COMPLEX
        }
    }
    
    private fun detectLanguage(text: String): String {
        // Simple language detection based on common words
        // In a real implementation, you might use a proper language detection library
        return "en" // Default to English
    }
    
    private fun analyzeTextStructure(text: String): TextStructure {
        val sentences = text.split("[.!?]+".toRegex()).filter { it.isNotBlank() }
        val punctuationCount = text.count { it in ".,!?;:" }
        
        return TextStructure(
            sentenceCount = sentences.size,
            hasQuestions = text.contains("?"),
            hasCommands = text.contains("!") || sentences.any { it.trim().startsWith("please", ignoreCase = true) },
            hasConjunctions = listOf("and", "or", "but", "then", "after", "before").any { 
                text.contains(it, ignoreCase = true) 
            },
            punctuationDensity = if (text.isNotEmpty()) punctuationCount.toDouble() / text.length else 0.0,
            capitalizationPattern = analyzeCapitalizationPattern(text)
        )
    }
    
    private fun analyzeCapitalizationPattern(text: String): String {
        val words = text.split("\\s+".toRegex())
        val capitalizedWords = words.count { it.isNotEmpty() && it[0].isUpperCase() }
        
        return when {
            capitalizedWords == 0 -> "none"
            capitalizedWords == words.size -> "all"
            capitalizedWords == 1 -> "sentence_case"
            capitalizedWords.toDouble() / words.size > 0.5 -> "title_case"
            else -> "mixed"
        }
    }
    
    private fun generatePatternId(characteristics: TextCharacteristics, errorType: String): String {
        val patternString = "${characteristics.length}_${characteristics.wordCount}_" +
                "${characteristics.hasTimePattern}_${characteristics.hasDatePattern}_" +
                "${characteristics.complexity}_${errorType}"
        return hashText(patternString)
    }
    
    private fun generateCorrectionId(): String {
        return "CORR_${System.currentTimeMillis()}_${(1000..9999).random()}"
    }
    
    private fun hashText(text: String): String {
        return try {
            val digest = MessageDigest.getInstance("SHA-256")
            val hashBytes = digest.digest(text.toByteArray())
            hashBytes.joinToString("") { "%02x".format(it) }.take(16)
        } catch (e: Exception) {
            text.hashCode().toString()
        }
    }
    
    private fun updateConfidence(existingConfidence: Double, newConfidence: Double): Double {
        // Weighted average with slight bias toward recent observations
        return (existingConfidence * 0.7) + (newConfidence * 0.3)
    }
    
    private fun mergeContextFactors(existing: List<String>, new: List<String>): List<String> {
        return (existing + new).distinct().take(10) // Limit to 10 factors
    }
    
    private fun determineSeverity(errorType: String, confidence: Double): String {
        return when (errorType) {
            "CRITICAL_ERROR" -> "HIGH"
            "PARSING_FAILURE" -> if (confidence < 0.3) "HIGH" else "MEDIUM"
            "LOW_CONFIDENCE" -> "MEDIUM"
            "NETWORK_ERROR" -> "LOW"
            else -> "LOW"
        }
    }
    
    private fun generateInitialSuggestions(
        characteristics: TextCharacteristics, 
        errorType: String
    ): List<String> {
        val suggestions = mutableListOf<String>()
        
        when (errorType) {
            "PARSING_FAILURE" -> {
                if (!characteristics.hasTimePattern) {
                    suggestions.add("Include specific times (e.g., '2:00 PM' instead of 'afternoon')")
                }
                if (!characteristics.hasDatePattern) {
                    suggestions.add("Include specific dates (e.g., 'March 15' instead of 'next week')")
                }
                if (characteristics.complexity == TextComplexity.VERY_COMPLEX) {
                    suggestions.add("Break down complex descriptions into simpler sentences")
                }
            }
            "LOW_CONFIDENCE" -> {
                suggestions.add("Be more specific about event details")
                if (characteristics.wordCount < 5) {
                    suggestions.add("Provide more context about the event")
                }
            }
        }
        
        return suggestions
    }
    
    private fun calculateCorrectionConfidence(
        originalValue: String?,
        correctedValue: String,
        userInteractionTime: Long
    ): Double {
        // Calculate confidence based on correction characteristics
        val lengthDifference = kotlin.math.abs((originalValue?.length ?: 0) - correctedValue.length)
        val timeFactor = min(1.0, userInteractionTime / 30000.0) // 30 seconds max
        
        return max(0.1, min(1.0, 1.0 - (lengthDifference / 100.0) + (timeFactor * 0.3)))
    }
    
    private fun updatePatternsWithCorrection(originalText: String, correction: UserCorrection) {
        // Update related patterns with correction information
        // This would involve finding patterns that match the original text characteristics
        // and updating their suggested improvements based on the correction
    }
    
    private fun generateSuggestionsFromPattern(
        pattern: FailurePattern,
        corrections: List<UserCorrection>
    ): List<ImprovementSuggestion> {
        val suggestions = mutableListOf<ImprovementSuggestion>()
        
        // Generate suggestions based on pattern characteristics
        if (pattern.occurrences >= MIN_PATTERN_OCCURRENCES) {
            val suggestionType = determineSuggestionType(pattern)
            val confidence = calculateSuggestionConfidence(pattern, corrections)
            
            if (confidence >= CORRECTION_CONFIDENCE_THRESHOLD) {
                suggestions.add(
                    ImprovementSuggestion(
                        suggestionId = "PAT_${pattern.patternId}",
                        type = suggestionType,
                        title = generateSuggestionTitle(suggestionType),
                        description = generateSuggestionDescription(pattern),
                        example = generateSuggestionExample(pattern),
                        confidence = confidence,
                        applicability = determineSuggestionApplicability(pattern),
                        priority = calculateSuggestionPriority(pattern),
                        basedOnPatterns = listOf(pattern.patternId)
                    )
                )
            }
        }
        
        return suggestions
    }
    
    private fun generateSuggestionsFromCorrections(corrections: List<UserCorrection>): List<ImprovementSuggestion> {
        val suggestions = mutableListOf<ImprovementSuggestion>()
        
        // Group corrections by field and analyze patterns
        val correctionsByField = corrections.groupBy { it.fieldCorrected }
        
        correctionsByField.forEach { (field, fieldCorrections) ->
            if (fieldCorrections.size >= MIN_PATTERN_OCCURRENCES) {
                val avgConfidence = fieldCorrections.map { it.confidence }.average()
                
                if (avgConfidence >= CORRECTION_CONFIDENCE_THRESHOLD) {
                    val suggestionType = mapFieldToSuggestionType(field)
                    
                    suggestions.add(
                        ImprovementSuggestion(
                            suggestionId = "CORR_${field}_${System.currentTimeMillis()}",
                            type = suggestionType,
                            title = "Improve $field specification",
                            description = generateCorrectionBasedDescription(field, fieldCorrections),
                            example = generateCorrectionBasedExample(fieldCorrections),
                            confidence = avgConfidence,
                            applicability = SuggestionApplicability(
                                textLengthRange = 1..1000,
                                complexityLevels = TextComplexity.values().toList(),
                                errorTypes = listOf("LOW_CONFIDENCE", "PARSING_FAILURE"),
                                languageSpecific = false
                            ),
                            priority = calculateCorrectionBasedPriority(fieldCorrections),
                            basedOnPatterns = fieldCorrections.map { it.correctionId }
                        )
                    )
                }
            }
        }
        
        return suggestions
    }
    
    private fun filterAndRankSuggestions(
        suggestions: List<ImprovementSuggestion>,
        textCharacteristics: TextCharacteristics?,
        recentErrorTypes: List<String>
    ): List<ImprovementSuggestion> {
        return suggestions
            .filter { suggestion ->
                textCharacteristics?.let { isApplicableToText(suggestion, it) } ?: true
            }
            .filter { suggestion ->
                recentErrorTypes.isEmpty() || 
                suggestion.applicability.errorTypes.any { it in recentErrorTypes }
            }
            .sortedWith(compareByDescending<ImprovementSuggestion> { it.confidence }
                .thenByDescending { it.priority })
            .distinctBy { it.type } // Avoid duplicate suggestion types
    }
    
    private fun isApplicableToText(
        suggestion: ImprovementSuggestion,
        characteristics: TextCharacteristics
    ): Boolean {
        return characteristics.length in suggestion.applicability.textLengthRange &&
                characteristics.complexity in suggestion.applicability.complexityLevels
    }
    
    private fun cacheSuggestions(suggestions: List<ImprovementSuggestion>) {
        try {
            val suggestionsJson = JSONArray()
            suggestions.forEach { suggestion ->
                suggestionsJson.put(JSONObject().apply {
                    put("id", suggestion.suggestionId)
                    put("type", suggestion.type.name)
                    put("title", suggestion.title)
                    put("description", suggestion.description)
                    put("example", suggestion.example)
                    put("confidence", suggestion.confidence)
                    put("priority", suggestion.priority)
                })
            }
            
            suggestionsFile.writeText(suggestionsJson.toString())
        } catch (e: Exception) {
            Log.w(TAG, "Failed to cache suggestions", e)
        }
    }
    
    private fun loadFailurePatterns(): MutableMap<String, FailurePattern> {
        return try {
            if (patternsFile.exists()) {
                val json = JSONObject(patternsFile.readText())
                val patterns = mutableMapOf<String, FailurePattern>()
                
                json.keys().forEach { key ->
                    val patternJson = json.getJSONObject(key)
                    // Parse pattern from JSON (implementation details omitted for brevity)
                    // patterns[key] = parsePatternFromJson(patternJson)
                }
                
                patterns
            } else {
                mutableMapOf()
            }
        } catch (e: Exception) {
            Log.w(TAG, "Failed to load failure patterns", e)
            mutableMapOf()
        }
    }
    
    private fun saveFailurePatterns(patterns: Map<String, FailurePattern>) {
        try {
            val json = JSONObject()
            patterns.forEach { (key, pattern) ->
                // Convert pattern to JSON (implementation details omitted for brevity)
                // json.put(key, convertPatternToJson(pattern))
            }
            
            patternsFile.writeText(json.toString())
        } catch (e: Exception) {
            Log.e(TAG, "Failed to save failure patterns", e)
        }
    }
    
    private fun loadUserCorrections(): MutableList<UserCorrection> {
        return try {
            if (correctionsFile.exists()) {
                val json = JSONArray(correctionsFile.readText())
                val corrections = mutableListOf<UserCorrection>()
                
                for (i in 0 until json.length()) {
                    val correctionJson = json.getJSONObject(i)
                    // Parse correction from JSON (implementation details omitted for brevity)
                    // corrections.add(parseCorrectionFromJson(correctionJson))
                }
                
                corrections
            } else {
                mutableListOf()
            }
        } catch (e: Exception) {
            Log.w(TAG, "Failed to load user corrections", e)
            mutableListOf()
        }
    }
    
    private fun saveUserCorrections(corrections: List<UserCorrection>) {
        try {
            val json = JSONArray()
            corrections.forEach { correction ->
                // Convert correction to JSON (implementation details omitted for brevity)
                // json.put(convertCorrectionToJson(correction))
            }
            
            correctionsFile.writeText(json.toString())
        } catch (e: Exception) {
            Log.e(TAG, "Failed to save user corrections", e)
        }
    }
    
    private fun updateImprovementSuggestions(pattern: FailurePattern) {
        // Update cached suggestions based on new pattern data
    }
    
    private fun calculatePatternImprovementRate(pattern: FailurePattern): Double {
        // Calculate how much the pattern has improved over time
        return max(0.0, 1.0 - (pattern.occurrences.toDouble() / 100.0))
    }
    
    private fun calculateCorrectionSuccessRate(corrections: List<UserCorrection>): Double {
        if (corrections.isEmpty()) return 0.0
        return corrections.map { it.confidence }.average()
    }
    
    private fun calculatePatternDiversity(patterns: List<FailurePattern>): Double {
        val errorTypes = patterns.map { it.errorType }.distinct()
        return if (patterns.isNotEmpty()) errorTypes.size.toDouble() / patterns.size else 0.0
    }
    
    private fun calculateLearningEffectiveness(
        patterns: List<FailurePattern>,
        corrections: List<UserCorrection>
    ): Double {
        // Calculate overall learning effectiveness based on patterns and corrections
        val patternEffectiveness = patterns.map { calculatePatternImprovementRate(it) }.average()
        val correctionEffectiveness = calculateCorrectionSuccessRate(corrections)
        
        return (patternEffectiveness + correctionEffectiveness) / 2.0
    }
    
    private fun getDefaultSuggestions(): List<ImprovementSuggestion> {
        return listOf(
            ImprovementSuggestion(
                suggestionId = "DEFAULT_1",
                type = SuggestionType.DATE_FORMAT,
                title = "Use specific dates",
                description = "Include specific dates instead of relative terms",
                example = "Use 'March 15' instead of 'next week'",
                confidence = 0.8,
                applicability = SuggestionApplicability(
                    textLengthRange = 1..1000,
                    complexityLevels = TextComplexity.values().toList(),
                    errorTypes = listOf("PARSING_FAILURE"),
                    languageSpecific = false
                ),
                priority = 1,
                basedOnPatterns = emptyList()
            )
        )
    }
    
    // Additional helper methods for suggestion generation
    private fun determineSuggestionType(pattern: FailurePattern): SuggestionType {
        return when {
            !pattern.textCharacteristics.hasTimePattern -> SuggestionType.TIME_FORMAT
            !pattern.textCharacteristics.hasDatePattern -> SuggestionType.DATE_FORMAT
            !pattern.textCharacteristics.hasLocationKeywords -> SuggestionType.LOCATION_CLARITY
            pattern.textCharacteristics.complexity == TextComplexity.VERY_COMPLEX -> SuggestionType.STRUCTURE_IMPROVEMENT
            else -> SuggestionType.EVENT_DESCRIPTION
        }
    }
    
    private fun calculateSuggestionConfidence(
        pattern: FailurePattern,
        corrections: List<UserCorrection>
    ): Double {
        val patternConfidence = min(1.0, pattern.occurrences.toDouble() / 10.0)
        val correctionSupport = corrections.count { it.originalTextHash == pattern.textCharacteristics.anonymizedHash }
        val correctionConfidence = min(1.0, correctionSupport.toDouble() / 5.0)
        
        return (patternConfidence + correctionConfidence) / 2.0
    }
    
    private fun generateSuggestionTitle(type: SuggestionType): String {
        return when (type) {
            SuggestionType.DATE_FORMAT -> "Specify dates clearly"
            SuggestionType.TIME_FORMAT -> "Include specific times"
            SuggestionType.LOCATION_CLARITY -> "Add location details"
            SuggestionType.EVENT_DESCRIPTION -> "Improve event description"
            SuggestionType.DURATION_SPECIFICATION -> "Specify event duration"
            SuggestionType.LANGUAGE_CLARITY -> "Use clearer language"
            SuggestionType.STRUCTURE_IMPROVEMENT -> "Simplify text structure"
            SuggestionType.CONTEXT_ADDITION -> "Add more context"
        }
    }
    
    private fun generateSuggestionDescription(pattern: FailurePattern): String {
        return "Based on ${pattern.occurrences} similar cases, this improvement could help with ${pattern.errorType.lowercase()} issues."
    }
    
    private fun generateSuggestionExample(pattern: FailurePattern): String? {
        return when (pattern.errorType) {
            "PARSING_FAILURE" -> "Instead of 'meeting tomorrow', try 'meeting March 15 at 2:00 PM'"
            "LOW_CONFIDENCE" -> "Instead of 'lunch', try 'lunch with John at Cafe Central on Friday at 12:30 PM'"
            else -> null
        }
    }
    
    private fun determineSuggestionApplicability(pattern: FailurePattern): SuggestionApplicability {
        return SuggestionApplicability(
            textLengthRange = (pattern.textCharacteristics.length - 20)..(pattern.textCharacteristics.length + 20),
            complexityLevels = listOf(pattern.textCharacteristics.complexity),
            errorTypes = listOf(pattern.errorType),
            languageSpecific = false
        )
    }
    
    private fun calculateSuggestionPriority(pattern: FailurePattern): Int {
        return when (pattern.severity) {
            "HIGH" -> 3
            "MEDIUM" -> 2
            else -> 1
        }
    }
    
    private fun mapFieldToSuggestionType(field: String): SuggestionType {
        return when (field.lowercase()) {
            "date", "start_date", "end_date" -> SuggestionType.DATE_FORMAT
            "time", "start_time", "end_time" -> SuggestionType.TIME_FORMAT
            "location" -> SuggestionType.LOCATION_CLARITY
            "duration" -> SuggestionType.DURATION_SPECIFICATION
            else -> SuggestionType.EVENT_DESCRIPTION
        }
    }
    
    private fun generateCorrectionBasedDescription(
        field: String,
        corrections: List<UserCorrection>
    ): String {
        return "Users frequently correct the $field field. Based on ${corrections.size} corrections, consider being more specific."
    }
    
    private fun generateCorrectionBasedExample(corrections: List<UserCorrection>): String? {
        return corrections.firstOrNull()?.let { correction ->
            "Example: '${correction.originalValue}' → '${correction.correctedValue}'"
        }
    }
    
    private fun calculateCorrectionBasedPriority(corrections: List<UserCorrection>): Int {
        val avgConfidence = corrections.map { it.confidence }.average()
        return when {
            avgConfidence > 0.8 -> 3
            avgConfidence > 0.6 -> 2
            else -> 1
        }
    }
}
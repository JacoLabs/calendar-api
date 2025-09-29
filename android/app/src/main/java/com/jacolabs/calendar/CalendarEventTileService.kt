package com.jacolabs.calendar

import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.os.Build
import android.service.quicksettings.TileService
import android.widget.Toast
import androidx.annotation.RequiresApi

/**
 * Quick Settings Tile for creating calendar events from clipboard text.
 * Available on Android 7.0+ (API 24+)
 */
@RequiresApi(Build.VERSION_CODES.N)
class CalendarEventTileService : TileService() {
    
    override fun onTileAdded() {
        super.onTileAdded()
        updateTile()
    }
    
    override fun onStartListening() {
        super.onStartListening()
        updateTile()
    }
    
    override fun onClick() {
        super.onClick()
        
        // Get text from clipboard
        val clipboardManager = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        val clip = clipboardManager.primaryClip
        
        if (clip != null && clip.itemCount > 0) {
            val clipText = clip.getItemAt(0).text?.toString()
            
            if (!clipText.isNullOrBlank()) {
                // Launch TextProcessorActivity with clipboard text
                val intent = Intent(this, TextProcessorActivity::class.java).apply {
                    action = Intent.ACTION_PROCESS_TEXT
                    putExtra(Intent.EXTRA_PROCESS_TEXT, clipText)
                    flags = Intent.FLAG_ACTIVITY_NEW_TASK
                }
                
                startActivityAndCollapse(intent)
            } else {
                // Show toast if clipboard is empty
                Toast.makeText(this, "Clipboard is empty", Toast.LENGTH_SHORT).show()
            }
        } else {
            // Show toast if no clipboard data
            Toast.makeText(this, "No text in clipboard", Toast.LENGTH_SHORT).show()
        }
    }
    
    private fun updateTile() {
        val tile = qsTile ?: return
        
        tile.label = "Calendar Event"
        tile.contentDescription = "Create calendar event from clipboard text"
        tile.state = android.service.quicksettings.Tile.STATE_ACTIVE
        tile.updateTile()
    }
}
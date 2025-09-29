package com.jacolabs.calendar

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/**
 * Receiver for handling notification dismiss actions.
 */
class NotificationDismissReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context?, intent: Intent?) {
        // Handle notification dismissal
        // Could track analytics here in production
    }
}
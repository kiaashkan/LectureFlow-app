/*
 * Copyright 2020 Google Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package ir.kiaashkan.lectureflow;

import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.content.pm.ActivityInfo;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.widget.Toast;

import androidx.browser.customtabs.CustomTabsIntent;

public class LauncherActivity
        extends com.google.androidbrowserhelper.trusted.LauncherActivity {

    private static final String LAUNCH_URL = "https://lf.kiaashkan.workers.dev/";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        try {
            super.onCreate(savedInstanceState);
            // Setting an orientation crashes the app due to the transparent background on Android 8.0
            // Oreo and below. We only set the orientation on Oreo and above. This only affects the
            // splash screen and Chrome will still respect the orientation.
            // See https://github.com/GoogleChromeLabs/bubblewrap/issues/496 for details.
            if (Build.VERSION.SDK_INT > Build.VERSION_CODES.O) {
                setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_USER_PORTRAIT);
            } else {
                setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED);
            }
        } catch (Throwable t) {
            // Never die silently: if the trusted launch path fails on this
            // device/browser combination, still land the user on LectureFlow
            // via a Custom Tab, then a plain browser intent.
            openFallback();
            finish();
        }
    }

    private void openFallback() {
        Uri url = Uri.parse(LAUNCH_URL);
        try {
            new CustomTabsIntent.Builder().build().launchUrl(this, url);
            return;
        } catch (Throwable ignored) {
        }
        try {
            startActivity(new Intent(Intent.ACTION_VIEW, url));
            return;
        } catch (ActivityNotFoundException ignored) {
        }
        Toast.makeText(this, "No browser available", Toast.LENGTH_LONG).show();
    }

    @Override
    protected Uri getLaunchingUrl() {
        // Get the original launch Url.
        Uri uri = super.getLaunchingUrl();

        return uri;
    }
}

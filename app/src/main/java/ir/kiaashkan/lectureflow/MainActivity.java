package ir.kiaashkan.lectureflow;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.DownloadManager;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.webkit.*;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import java.io.File;
import java.io.FileOutputStream;
import java.util.Locale;

public class MainActivity extends AppCompatActivity {

    private static final String HOME_URL = "https://lf.kiaashkan.workers.dev";
    private static final int PERMISSION_REQUEST_CODE = 100;
    private static final int FILE_CHOOSER_REQUEST_CODE = 101;

    private WebView webView;
    private ValueCallback<Uri[]> filePathCallback;
    private boolean isDarkMode = false;
    private boolean isOnHomePage = true;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        webView = findViewById(R.id.webview);

        // Detect system dark mode
        int nightMode = getResources().getConfiguration().uiMode
                & android.content.res.Configuration.UI_MODE_NIGHT_MASK;
        isDarkMode = nightMode == android.content.res.Configuration.UI_MODE_NIGHT_YES;

        // Prevent white/black flash before page loads
        webView.setBackgroundColor(android.graphics.Color.parseColor(
                isDarkMode ? "#0b1220" : "#f1f5f9"));

        setupWebView();
        requestStoragePermission();
        webView.loadUrl(HOME_URL);
    }

    @SuppressLint("SetJavaScriptEnabled")
    private void setupWebView() {
        WebSettings settings = webView.getSettings();

        // JavaScript — required for site functionality
        settings.setJavaScriptEnabled(true);
        settings.setJavaScriptCanOpenWindowsAutomatically(false); // تغییر: جلوگیری از popup های ناخواسته
        settings.setMediaPlaybackRequiresUserGesture(true); // تغییر: نیاز به تعامل کاربر برای پخش مدیا
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);
        settings.setUseWideViewPort(true);
        settings.setLoadWithOverviewMode(true);
        settings.setBuiltInZoomControls(false);
        settings.setSupportZoom(false);
        settings.setAllowFileAccess(false); // تغییر: غیرفعال - نیازی نیست
        settings.setAllowContentAccess(true);
        settings.setAllowFileAccessFromFileURLs(false); // امنیت
        settings.setAllowUniversalAccessFromFileURLs(false); // امنیت
        settings.setUserAgentString(settings.getUserAgentString() + " LectureFlowApp/1.0");

        // Safe Browsing
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            settings.setSafeBrowsingEnabled(true);
        }

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                String url = request.getUrl().toString();

                // blob/data → download listener handles it
                if (url.startsWith("blob:") || url.startsWith("data:")) {
                    return false;
                }

                // PDF → block
                if (url.toLowerCase(Locale.ROOT).endsWith(".pdf")
                        || url.toLowerCase(Locale.ROOT).contains(".pdf?")) {
                    Toast.makeText(MainActivity.this,
                            "دانلود PDF در این نسخه پشتیبانی نمیشه", Toast.LENGTH_SHORT).show();
                    return true;
                }

                // Our domain → stay in WebView
                if (url.startsWith(HOME_URL)) {
                    return false;
                }

                // External → open in browser safely
                try {
                    Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                    intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                    startActivity(intent);
                } catch (Exception ignored) {}
                return true;
            }

            @Override
            public void onPageStarted(WebView view, String url, android.graphics.Bitmap favicon) {
                super.onPageStarted(view, url, favicon);
                isOnHomePage = url != null && url.startsWith(HOME_URL);
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                isOnHomePage = url != null && url.startsWith(HOME_URL);

                // Sync theme with system setting
                String theme = isDarkMode ? "dark" : "light";
                String themeKey = isDarkMode ? "d" : "l";
                String sunMoon = isDarkMode ? "\u2600\uFE0F" : "\uD83C\uDF19";
                String modeLabel = isDarkMode ? "Light mode" : "Dark mode";
                view.evaluateJavascript(
                    "(function(){" +
                    "document.body.classList.remove('dark','light');" +
                    "document.body.classList.add('" + theme + "');" +
                    "localStorage.setItem('t','" + themeKey + "');" +
                    "var ti=document.getElementById('ti');" +
                    "var tl=document.getElementById('tl');" +
                    "if(ti)ti.textContent='" + sunMoon + "';" +
                    "if(tl)tl.textContent='" + modeLabel + "';" +
                    "})();", null);

                // Intercept PDF clicks
                view.evaluateJavascript(
                    "(function(){" +
                    "function interceptPDF(e){" +
                    "  var el=e.target.closest('a');" +
                    "  if(!el)return;" +
                    "  var href=el.href||'';" +
                    "  if(href.toLowerCase().indexOf('.pdf')!==-1){" +
                    "    e.preventDefault();e.stopPropagation();" +
                    "    AndroidBridge.showToast('دانلود PDF در این نسخه پشتیبانی نمیشه');" +
                    "  }" +
                    "}" +
                    "document.removeEventListener('click',interceptPDF,true);" +
                    "document.addEventListener('click',interceptPDF,true);" +
                    "})();", null);
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request,
                                        WebResourceError error) {
                // فقط برای main frame خطا نشون بده
                if (request.isForMainFrame()) {
                    // صفحه خطا نشون نده، همون صفحه بمونه
                }
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(PermissionRequest request) {
                // فقط مجوزهای مورد نیاز سایت رو بده
                String[] granted = {};
                request.grant(granted); // هیچ مجوز اضافه‌ای نده
            }

            @Override
            public boolean onShowFileChooser(WebView webView, ValueCallback<Uri[]> filePath,
                                             FileChooserParams fileChooserParams) {
                // اگه قبلی باز مونده cancel کن
                if (filePathCallback != null) {
                    filePathCallback.onReceiveValue(null);
                    filePathCallback = null;
                }
                filePathCallback = filePath;

                try {
                    Intent chooserIntent = fileChooserParams.createIntent();
                    Intent finalIntent = Intent.createChooser(chooserIntent, "انتخاب فایل صوتی");
                    startActivityForResult(finalIntent, FILE_CHOOSER_REQUEST_CODE);
                } catch (Exception e) {
                    filePathCallback = null;
                    return false;
                }
                return true;
            }

            @Override
            public boolean onJsAlert(WebView view, String url, String message, JsResult result) {
                result.confirm();
                return true;
            }

            @Override
            public boolean onJsConfirm(WebView view, String url, String message, JsResult result) {
                result.cancel(); // تغییر: cancel به جای confirm برای امنیت بیشتر
                return true;
            }

            @Override
            public boolean onConsoleMessage(ConsoleMessage msg) {
                // فقط توی debug log بنویس، نه release
                if (BuildConfig.DEBUG) {
                    android.util.Log.d("LectureFlow_JS",
                            msg.message() + " -- Line " + msg.lineNumber());
                }
                return true;
            }
        });

        webView.addJavascriptInterface(new JSBridge(), "AndroidBridge");

        // Download listener
        webView.setDownloadListener((url, userAgent, contentDisposition, mimetype, contentLength) -> {
            if (mimetype != null && mimetype.contains("pdf")) {
                Toast.makeText(this, "دانلود PDF در این نسخه پشتیبانی نمیشه", Toast.LENGTH_SHORT).show();
                return;
            }

            if (url.startsWith("blob:")) {
                String safeUrl = url.replace("'", "\\'");
                String safeMime = (mimetype != null ? mimetype : "text/plain").replace("'", "\\'");
                String safeDisp = (contentDisposition != null ? contentDisposition : "").replace("'", "\\'");
                webView.evaluateJavascript(
                    "(function(){" +
                    "var xhr=new XMLHttpRequest();" +
                    "xhr.open('GET','" + safeUrl + "',true);" +
                    "xhr.responseType='blob';" +
                    "xhr.onload=function(){" +
                    "  var reader=new FileReader();" +
                    "  reader.onloadend=function(){" +
                    "    AndroidBridge.downloadBase64(reader.result,'" + safeDisp + "','" + safeMime + "');" +
                    "  };" +
                    "  reader.readAsDataURL(xhr.response);" +
                    "};" +
                    "xhr.send();" +
                    "})();", null);
                return;
            }

            try {
                DownloadManager.Request req = new DownloadManager.Request(Uri.parse(url));
                req.setMimeType(mimetype);
                req.addRequestHeader("User-Agent", userAgent);
                String fileName = URLUtil.guessFileName(url, contentDisposition, mimetype);
                req.setTitle(fileName);
                req.setDescription("در حال دانلود...");
                req.setNotificationVisibility(
                        DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
                req.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, fileName);
                DownloadManager dm = (DownloadManager) getSystemService(Context.DOWNLOAD_SERVICE);
                if (dm != null) {
                    dm.enqueue(req);
                    Toast.makeText(this, "✓ دانلود: " + fileName, Toast.LENGTH_SHORT).show();
                }
            } catch (Exception e) {
                Toast.makeText(this, "خطا در دانلود", Toast.LENGTH_SHORT).show();
            }
        });
    }

    // JavaScript Bridge — فقط متدهای ضروری
    public class JSBridge {
        @JavascriptInterface
        public String getAppVersion() { return BuildConfig.VERSION_NAME; }

        @JavascriptInterface
        public String getPlatform() { return "android"; }

        @JavascriptInterface
        public void showToast(String message) {
            // محدود کردن طول پیام برای جلوگیری از سوءاستفاده
            if (message == null || message.length() > 200) return;
            runOnUiThread(() ->
                    Toast.makeText(MainActivity.this, message, Toast.LENGTH_SHORT).show());
        }

        @JavascriptInterface
        public void downloadBase64(String base64Data, String contentDisposition, String mimeType) {
            if (mimeType != null && mimeType.contains("pdf")) return;
            if (base64Data == null || base64Data.length() > 10 * 1024 * 1024) return; // max 10MB

            try {
                String base64 = base64Data.contains(",") ? base64Data.split(",")[1] : base64Data;
                byte[] bytes = android.util.Base64.decode(base64, android.util.Base64.DEFAULT);
                String ext = (mimeType != null && mimeType.contains("text")) ? ".txt" : ".bin";
                String fileName = "LectureFlow_" + System.currentTimeMillis() + ext;
                File downloadsDir = Environment.getExternalStoragePublicDirectory(
                        Environment.DIRECTORY_DOWNLOADS);
                File file = new File(downloadsDir, fileName);

                // اطمینان از اینکه فایل داخل Downloads ذخیره میشه
                if (!file.getCanonicalPath().startsWith(downloadsDir.getCanonicalPath())) {
                    return; // path traversal attack prevention
                }

                try (FileOutputStream fos = new FileOutputStream(file)) {
                    fos.write(bytes);
                }
                runOnUiThread(() -> Toast.makeText(MainActivity.this,
                        "✓ دانلود شد: " + fileName, Toast.LENGTH_LONG).show());
            } catch (Exception e) {
                runOnUiThread(() -> Toast.makeText(MainActivity.this,
                        "خطا در دانلود فایل", Toast.LENGTH_SHORT).show());
            }
        }
    }

    private void requestStoragePermission() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.READ_EXTERNAL_STORAGE)
                    != PackageManager.PERMISSION_GRANTED) {
                ActivityCompat.requestPermissions(this,
                        new String[]{Manifest.permission.READ_EXTERNAL_STORAGE},
                        PERMISSION_REQUEST_CODE);
            }
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, @NonNull String[] permissions,
                                           @NonNull int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        // نیازی به reload نیست
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == FILE_CHOOSER_REQUEST_CODE) {
            if (filePathCallback == null) return;
            Uri[] results = null;
            if (resultCode == Activity.RESULT_OK && data != null && data.getData() != null) {
                results = new Uri[]{data.getData()};
            }
            filePathCallback.onReceiveValue(results);
            filePathCallback = null;
        }
    }

    @Override
    public void onBackPressed() {
        String currentUrl = webView.getUrl();
        boolean onHome = currentUrl == null
                || currentUrl.equals(HOME_URL)
                || currentUrl.equals(HOME_URL + "/");

        if (onHome) {
            super.onBackPressed();
        } else if (webView.canGoBack()) {
            webView.goBack();
        } else {
            webView.loadUrl(HOME_URL);
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        webView.onPause(); // کاهش مصرف باتری وقتی اپ پس‌زمینه‌ست
    }

    @Override
    protected void onResume() {
        super.onResume();
        webView.onResume();
    }

    @Override
    protected void onDestroy() {
        if (webView != null) {
            webView.stopLoading();
            webView.destroy(); // آزاد کردن حافظه
        }
        super.onDestroy();
    }
}

plugins { id("com.android.application") }

android {
    namespace = "com.aqss.bodyguard.sharetest"
    compileSdk = 36
    defaultConfig {
        applicationId = "com.aqss.bodyguard.sharetest"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "1-test-only"
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

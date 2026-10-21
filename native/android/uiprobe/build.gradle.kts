plugins { id("com.android.application") }

android {
    namespace = "com.aqss.bodyguard.uiprobe"
    compileSdk = 36
    defaultConfig {
        applicationId = "com.aqss.bodyguard.uiprobe"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "1-test-only"
    }
    sourceSets.getByName("main").assets.srcDir("../../ios/Tests/AQSSNativeFeedbackTests/Fixtures")
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

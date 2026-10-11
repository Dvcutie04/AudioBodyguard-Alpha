plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.aqss.bodyguard.prototype"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.aqss.bodyguard.prototype"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "0.1-simulation"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation(project(":"))
    implementation("com.google.mlkit:text-recognition:16.0.1")
}

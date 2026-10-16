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
        versionCode = 2
        versionName = "0.2-input-check"
    }

    buildTypes {
        create("liveInput") {
            initWith(getByName("debug"))
            applicationIdSuffix = ".liveinput"
            versionNameSuffix = "-live-input"
            matchingFallbacks += listOf("debug")
            resValue("string", "app_name", "Audio Bodyguard Live Test")
        }
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

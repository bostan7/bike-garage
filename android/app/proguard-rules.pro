# Filament / gltfio are called from native code (JNI callbacks, enums looked up by name): keep their Java side whole.
-keep class com.google.android.filament.** { *; }
-dontwarn com.google.android.filament.**

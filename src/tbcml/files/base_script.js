'use strict';

// This part of the script is automatically generated by tbcml.
// You can see the log by running adb logcat -s tbcml.

function logError(message) {
    Java.perform(function () {
        var Log = Java.use("android.util.Log");
        Log.e("tbcml", message);
        console.error(message);
    });
}
function logWarning(message) {
    Java.perform(function () {
        var Log = Java.use("android.util.Log");
        Log.w("tbcml", message);
        console.warn(message);
    });
}
function logInfo(message) {
    Java.perform(function () {
        var Log = Java.use("android.util.Log");
        Log.i("tbcml", message);
        console.info(message);
    });
}
function logVerbose(message) {
    Java.perform(function () {
        var Log = Java.use("android.util.Log");
        Log.v("tbcml", message);
        console.log(message);
    });
}
function logDebug(message) {
    Java.perform(function () {
        var Log = Java.use("android.util.Log");
        Log.d("tbcml", message);
        console.log(message);
    });
}
function log(message, level = "info") {
    switch (level) {
        case "error":
            logError(message);
            break;
        case "warning":
            logWarning(message);
            break;
        case "info":
            logInfo(message);
            break;
        case "verbose":
            logVerbose(message);
            break;
        case "debug":
            logDebug(message);
            break;
        default:
            logInfo(message);
            break;
    }
}


function getBaseAddress() {
    let base_address = Module.findBaseAddress("libnative-lib.so")
    if (base_address == null) {
        return null;
    }
    return base_address.add(4096); // offset due to libgadget being added
}

function readStdString(address) {
    const isTiny = (address.readU8() & 1) === 0;
    if (isTiny) {
        return address.add(1).readUtf8String();
    }

    return address.add(2 * Process.pointerSize).readPointer().readUtf8String();
}

function readJString(address) {
    return Java.cast(address, Java.use("java.lang.String"));

}

function writeStdString(address, content) {
    const isTiny = (address.readU8() & 1) === 0;
    if (isTiny)
        address.add(1).writeUtf8String(content);
    else
        address.add(2 * Process.pointerSize).readPointer().writeUtf8String(content);
}

function writeJString(address, content) {
    Java.cast(address, Java.use("java.lang.String")).$new(content);
}

function readByteBuffer(address) {
    let bb = Java.cast(address, Java.use("java.nio.ByteBuffer"));
    let limit = bb.limit();
    let data = "";
    for (let i = 0; i < limit; i++) {
        data += String.fromCharCode(bb.get(i));
    }
    return data;
}

function getJavaClass(className) {
    var classFactory;
    const classLoaders = Java.enumerateClassLoadersSync();
    for (const classLoader in classLoaders) {
        try {
            classLoaders[classLoader].findClass(className);
            classFactory = Java.ClassFactory.get(classLoaders[classLoader]);
            break;
        } catch (e) {
            continue;
        }
    }
    return classFactory.use(className);
}

function getArcitecture() {
    return Process.arch;
}

function is_64_bit() {
    return Process.pointerSize === 8;
}

function getPackageName() {
    return Java.use("android.app.ActivityThread").currentApplication().getPackageName();
}

function getPackageVersion() {
    let context = Java.use("android.app.ActivityThread").currentApplication().getApplicationContext();
    let packageManager = context.getPackageManager();
    let packageInfo = packageManager.getPackageInfo(context.getPackageName(), 0);
    return packageInfo.versionCode.value;
}

function download_file(url) {
    let URL = Java.use("java.net.URL");
    let BufferedReader = Java.use("java.io.BufferedReader");
    let InputStreamReader = Java.use("java.io.InputStreamReader");
    let StringBuilder = Java.use("java.lang.StringBuilder");
    let url_obj = URL.$new(url);
    let urlConnection = url_obj.openConnection();
    let inputStreamReader = InputStreamReader.$new(urlConnection.getInputStream());
    let bufferedReader = BufferedReader.$new(inputStreamReader);
    let stringBuilder = StringBuilder.$new();
    let inputLine = null;
    while ((inputLine = bufferedReader.readLine()) != null) {
        stringBuilder.append(inputLine);
    }
    bufferedReader.close();
    return stringBuilder.toString();
}


rpc.exports = {
    init(stage, parameters) {
        log(`Script loaded successfully\nStage: ${stage}\nParameters: ${JSON.stringify(parameters)}`);
        log(`Base address: ${getBaseAddress()}`);
        log(`Architecture: ${getArcitecture()}`);
        log(`Package name: ${getPackageName()}`);
        log(`Package version: ${getPackageVersion()}`);
    },
};


// Mod scripts go here

// {{SCRIPTS}}
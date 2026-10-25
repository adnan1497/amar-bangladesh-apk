#!/usr/bin/env python3
"""cap add android এর পরে চলে: আইকন, অ্যালার্ম-শব্দ ও অনুমতি বসায়।"""
import os, re, math, struct, wave, sys
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, 'android/app/src/main/res')
MAN = os.path.join(ROOT, 'android/app/src/main/AndroidManifest.xml')
SRC = os.path.join(ROOT, 'www/icon-512.png')

# ---------- অ্যালার্মের শব্দ (জোরালো সাইরেন, ৩০ সেকেন্ড) ----------
def make_alarm(path, secs=30, sr=22050):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    frames = bytearray()
    for i in range(int(secs * sr)):
        t = i / sr
        phase = int(t / 0.5) % 2            # প্রতি আধা সেকেন্ডে দুই সুর
        f = (880.0 if phase == 0 else 1320.0) * (1 + 0.12 * ((t % 0.5) / 0.5))
        env = min(1.0, (t % 0.5) / 0.01, (0.5 - (t % 0.5)) / 0.03)
        sq = 1.0 if math.sin(2 * math.pi * f * t) >= 0 else -1.0
        saw = 2.0 * ((f * t) % 1.0) - 1.0
        v = max(-1.0, min(1.0, (0.6 * sq + 0.4 * saw) * 0.95 * env))
        frames += struct.pack('<h', int(v * 32000))
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(bytes(frames))
make_alarm(os.path.join(RES, 'raw/alarm.wav'))

# ---------- নতুন "কথা"-র নোটিফিকেশন শব্দ (পুশের জন্য, জোরালো তিন-সুরের ঘণ্টা) ----------
def make_msg(path, sr=22050):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    notes = [(784.0, 0.00), (1047.0, 0.22), (1319.0, 0.44), (784.0, 0.95), (1047.0, 1.17), (1319.0, 1.39)]
    total = 2.2
    frames = bytearray()
    for i in range(int(total * sr)):
        t = i / sr
        v = 0.0
        for f, st in notes:
            if t >= st:
                dt = t - st
                env = min(1.0, dt / 0.01) * math.exp(-dt * 5.0)
                v += env * (math.sin(2 * math.pi * f * t) + 0.35 * math.sin(2 * math.pi * 2 * f * t) + 0.15 * math.sin(2 * math.pi * 3 * f * t))
        v = max(-1.0, min(1.0, v * 0.75))
        frames += struct.pack('<h', int(v * 32000))
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(bytes(frames))
make_msg(os.path.join(RES, 'raw/msg.wav'))

# ---------- আইকন ----------
img = Image.open(SRC).convert('RGBA')
legacy = {'mdpi': 48, 'hdpi': 72, 'xhdpi': 96, 'xxhdpi': 144, 'xxxhdpi': 192}
fore = {'mdpi': 108, 'hdpi': 162, 'xhdpi': 216, 'xxhdpi': 324, 'xxxhdpi': 432}
for d, px in legacy.items():
    folder = os.path.join(RES, 'mipmap-' + d); os.makedirs(folder, exist_ok=True)
    im = img.resize((px, px), Image.LANCZOS)
    im.save(os.path.join(folder, 'ic_launcher.png')); im.save(os.path.join(folder, 'ic_launcher_round.png'))
for d, px in fore.items():
    folder = os.path.join(RES, 'mipmap-' + d); os.makedirs(folder, exist_ok=True)
    canvas = Image.new('RGBA', (px, px), (0, 0, 0, 0))
    inner = int(px * 0.62)
    canvas.paste(img.resize((inner, inner), Image.LANCZOS), ((px - inner) // 2, (px - inner) // 2))
    canvas.save(os.path.join(folder, 'ic_launcher_foreground.png'))
bg = os.path.join(RES, 'values/ic_launcher_background.xml')
os.makedirs(os.path.dirname(bg), exist_ok=True)
open(bg, 'w').write('<?xml version="1.0" encoding="utf-8"?>\n<resources>\n    <color name="ic_launcher_background">#006A4E</color>\n</resources>\n')

# নোটিফিকেশনের ছোট আইকন (সাদা-স্বচ্ছ)
stat = Image.new('RGBA', (96, 96), (0, 0, 0, 0))
from PIL import ImageDraw
dr = ImageDraw.Draw(stat); dr.ellipse((14, 14, 82, 82), outline=(255, 255, 255, 255), width=8); dr.line((48, 48, 48, 26), fill=(255, 255, 255, 255), width=7); dr.line((48, 48, 64, 56), fill=(255, 255, 255, 255), width=7)
for d in ['mdpi', 'hdpi', 'xhdpi', 'xxhdpi', 'xxxhdpi']:
    folder = os.path.join(RES, 'drawable-' + d); os.makedirs(folder, exist_ok=True)
    stat.resize((48, 48)).save(os.path.join(folder, 'ic_stat_icon_config_sample.png'))

# ---------- অনুমতি ----------
m = open(MAN, encoding='utf-8').read()
need = ['android.permission.POST_NOTIFICATIONS', 'android.permission.SCHEDULE_EXACT_ALARM', 'android.permission.USE_EXACT_ALARM',
        'android.permission.RECEIVE_BOOT_COMPLETED', 'android.permission.VIBRATE', 'android.permission.WAKE_LOCK', 'android.permission.USE_FULL_SCREEN_INTENT', 'android.permission.ACCESS_COARSE_LOCATION', 'android.permission.ACCESS_FINE_LOCATION', 'com.android.alarm.permission.SET_ALARM']
add = ''.join('\n    <uses-permission android:name="%s" />' % p for p in need if p not in m)
if 'android.permission.INTERNET' in m:
    m = re.sub(r'(<uses-permission android:name="android.permission.INTERNET"\s*/>)', r'\1' + add.replace('\\', '\\\\'), m, count=1)
else:
    m = m.replace('</manifest>', add + '\n</manifest>')
# পুশ নোটিফিকেশনের ডিফল্ট চ্যানেল ও আইকন
meta = ('\n        <meta-data android:name="com.google.firebase.messaging.default_notification_channel_id" android:value="msg" />'
        '\n        <meta-data android:name="com.google.firebase.messaging.default_notification_icon" android:resource="@drawable/ic_stat_icon_config_sample" />')
if 'default_notification_channel_id' not in m:
    m = re.sub(r'(<application\b[^>]*>)', lambda mo: mo.group(1) + meta, m, count=1)
# টেক্সট-টু-স্পিচ (পড়ে শোনান): অ্যান্ড্রয়েড ১১+ এ TTS ইঞ্জিন দেখতে পাওয়ার অনুমতি
if 'TTS_SERVICE' not in m:
    m = m.replace('<application', '<queries><intent><action android:name="android.intent.action.TTS_SERVICE" /></intent></queries>\n    <application', 1)

# ---------- অ্যাপের নিজস্ব নেটিভ অ্যালার্ম (সাধারণ অ্যালার্মের মতো জোরে বাজে; রিস্টার্টের পরও টেকে) ----------
import glob
JAVA = {
    'AmarAlarmStore': r'''package __PK__;

import android.app.AlarmManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Build;
import org.json.JSONArray;
import org.json.JSONObject;

/** নির্ধারিত অ্যালার্মের তালিকা ফোনে জমা রাখে (রিস্টার্টের পর আবার বসানোর জন্য) এবং AlarmManager-এ বসায়। */
public class AmarAlarmStore {
    static final String PREF = "amar_alarms";
    static final String KEY = "list";
    static final String ACT_RING = "__PK__.AMAR_RING";

    static PendingIntent opIntent(Context c, int id, String title, String body) {
        Intent i = new Intent(c, AmarAlarmReceiver.class);
        i.setAction(ACT_RING);
        i.putExtra("id", id);
        i.putExtra("title", title);
        i.putExtra("body", body);
        int flags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= 23) flags |= PendingIntent.FLAG_IMMUTABLE;
        return PendingIntent.getBroadcast(c, id, i, flags);
    }

    static void setOne(Context c, int id, long at, String title, String body) {
        try {
            AlarmManager am = (AlarmManager) c.getSystemService(Context.ALARM_SERVICE);
            Intent launch = c.getPackageManager().getLaunchIntentForPackage(c.getPackageName());
            int f = PendingIntent.FLAG_UPDATE_CURRENT;
            if (Build.VERSION.SDK_INT >= 23) f |= PendingIntent.FLAG_IMMUTABLE;
            PendingIntent show = PendingIntent.getActivity(c, 0, launch, f);
            am.setAlarmClock(new AlarmManager.AlarmClockInfo(at, show), opIntent(c, id, title, body));
        } catch (Exception e) {
        }
    }

    static void cancelOne(Context c, int id) {
        try {
            AlarmManager am = (AlarmManager) c.getSystemService(Context.ALARM_SERVICE);
            am.cancel(opIntent(c, id, "", ""));
        } catch (Exception e) {
        }
    }

    static JSONArray load(Context c) {
        try {
            SharedPreferences p = c.getSharedPreferences(PREF, Context.MODE_PRIVATE);
            return new JSONArray(p.getString(KEY, "[]"));
        } catch (Exception e) {
            return new JSONArray();
        }
    }

    static void save(Context c, JSONArray a) {
        c.getSharedPreferences(PREF, Context.MODE_PRIVATE).edit().putString(KEY, a.toString()).apply();
    }

    /** একটি গ্রুপ (med / alarm) পুরোটা বদলে নতুন তালিকা বসায়। */
    static int replaceGroup(Context c, String group, JSONArray items) {
        JSONArray old = load(c), keep = new JSONArray();
        try {
            for (int k = 0; k < old.length(); k++) {
                JSONObject o = old.getJSONObject(k);
                if (group.equals(o.optString("g"))) cancelOne(c, o.getInt("id"));
                else keep.put(o);
            }
            long now = System.currentTimeMillis();
            int n = 0;
            for (int k = 0; k < items.length() && n < 300; k++) {
                JSONObject o = items.getJSONObject(k);
                long at = o.getLong("at");
                if (at <= now) continue;
                int id = o.getInt("id");
                JSONObject s = new JSONObject();
                s.put("id", id);
                s.put("at", at);
                s.put("g", group);
                s.put("title", o.optString("title", "অ্যালার্ম"));
                s.put("body", o.optString("body", ""));
                keep.put(s);
                setOne(c, id, at, s.getString("title"), s.getString("body"));
                n++;
            }
            save(c, keep);
            return n;
        } catch (Exception e) {
            return -1;
        }
    }

    static void remove(Context c, int id) {
        JSONArray old = load(c), keep = new JSONArray();
        try {
            for (int k = 0; k < old.length(); k++) {
                JSONObject o = old.getJSONObject(k);
                if (o.getInt("id") != id) keep.put(o);
            }
            save(c, keep);
        } catch (Exception e) {
        }
    }

    /** ফোন চালু/সময় বদলের পর আবার বসানো */
    static void rescheduleAll(Context c) {
        JSONArray a = load(c), keep = new JSONArray();
        long now = System.currentTimeMillis();
        try {
            for (int k = 0; k < a.length(); k++) {
                JSONObject o = a.getJSONObject(k);
                if (o.getLong("at") > now) {
                    keep.put(o);
                    setOne(c, o.getInt("id"), o.getLong("at"), o.optString("title"), o.optString("body"));
                }
            }
            save(c, keep);
        } catch (Exception e) {
        }
    }
}
''',
    'AmarAlarmReceiver': r'''package __PK__;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.media.AudioAttributes;
import android.media.AudioManager;
import android.net.Uri;
import android.os.Build;

/** অ্যালার্মের সময় হলে জোরে বাজায় (অ্যালার্ম-শব্দ-ধারায়, সাইলেন্ট মোডেও), বন্ধ ও ৫ মিনিট-পরে বোতামসহ। */
public class AmarAlarmReceiver extends BroadcastReceiver {
    static final String CH = "amar_alarm_v1";
    static final String ACT_STOP = "__PK__.AMAR_STOP";
    static final String ACT_SNOOZE = "__PK__.AMAR_SNOOZE";

    @Override
    public void onReceive(Context ctx, Intent intent) {
        String act = intent.getAction();
        int id = intent.getIntExtra("id", 0);
        NotificationManager nm = (NotificationManager) ctx.getSystemService(Context.NOTIFICATION_SERVICE);
        String title = intent.getStringExtra("title");
        String body = intent.getStringExtra("body");
        if (title == null) title = "অ্যালার্ম";
        if (body == null) body = "";
        if (ACT_STOP.equals(act)) {
            nm.cancel(id);
            return;
        }
        if (ACT_SNOOZE.equals(act)) {
            nm.cancel(id);
            long at = System.currentTimeMillis() + 5 * 60 * 1000L;
            AmarAlarmStore.setOne(ctx, id, at, title, body);
            return;
        }
        AmarAlarmStore.remove(ctx, id);
        ring(ctx, nm, id, title, body);
    }

    static PendingIntent act(Context ctx, int id, String action, String title, String body, int rc) {
        Intent i = new Intent(ctx, AmarAlarmReceiver.class);
        i.setAction(action);
        i.putExtra("id", id);
        i.putExtra("title", title);
        i.putExtra("body", body);
        int f = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= 23) f |= PendingIntent.FLAG_IMMUTABLE;
        return PendingIntent.getBroadcast(ctx, rc, i, f);
    }

    static void ring(Context ctx, NotificationManager nm, int id, String title, String body) {
        Uri sound = Uri.parse("android.resource://" + ctx.getPackageName() + "/raw/alarm");
        if (Build.VERSION.SDK_INT >= 26) {
            NotificationChannel c = new NotificationChannel(CH, "অ্যালার্ম ও ওষুধ (জোরে বাজে)", NotificationManager.IMPORTANCE_HIGH);
            AudioAttributes aa = new AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_ALARM)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                    .build();
            c.setSound(sound, aa);
            c.enableVibration(true);
            c.setVibrationPattern(new long[]{0, 700, 300, 700, 300, 700});
            c.setLockscreenVisibility(Notification.VISIBILITY_PUBLIC);
            nm.createNotificationChannel(c);
        }
        Notification.Builder b;
        if (Build.VERSION.SDK_INT >= 26) b = new Notification.Builder(ctx, CH);
        else b = new Notification.Builder(ctx);
        int icon = ctx.getResources().getIdentifier("ic_stat_icon_config_sample", "drawable", ctx.getPackageName());
        if (icon == 0) icon = android.R.drawable.ic_lock_idle_alarm;
        Intent launch = ctx.getPackageManager().getLaunchIntentForPackage(ctx.getPackageName());
        int f = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= 23) f |= PendingIntent.FLAG_IMMUTABLE;
        PendingIntent open = PendingIntent.getActivity(ctx, id, launch, f);
        b.setSmallIcon(icon)
                .setContentTitle(title)
                .setContentText(body)
                .setContentIntent(open)
                .setFullScreenIntent(open, true)
                .setAutoCancel(true)
                .setOngoing(false)
                .setCategory(Notification.CATEGORY_ALARM)
                .setVisibility(Notification.VISIBILITY_PUBLIC)
                .addAction(0, "⏹ বন্ধ করুন", act(ctx, id, ACT_STOP, title, body, id + 1000000))
                .addAction(0, "😴 ৫ মিনিট পরে", act(ctx, id, ACT_SNOOZE, title, body, id + 2000000));
        if (Build.VERSION.SDK_INT < 26) {
            b.setSound(sound, AudioManager.STREAM_ALARM);
            b.setVibrate(new long[]{0, 700, 300, 700, 300, 700});
            b.setPriority(Notification.PRIORITY_MAX);
        } else {
            b.setTimeoutAfter(10 * 60 * 1000L);
        }
        Notification n = b.build();
        n.flags |= Notification.FLAG_INSISTENT;
        nm.notify(id, n);
    }
}
''',
    'AmarBootReceiver': r'''package __PK__;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

/** ফোন রিস্টার্ট, অ্যাপ আপডেট বা সময় বদলালে অ্যালার্মগুলো আবার বসায়। */
public class AmarBootReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context ctx, Intent intent) {
        AmarAlarmStore.rescheduleAll(ctx);
    }
}
''',
    'AmarAlarmPlugin': r'''package __PK__;

import android.content.Intent;
import android.provider.AlarmClock;
import com.getcapacitor.JSArray;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import java.util.ArrayList;

@CapacitorPlugin(name = "AmarAlarm")
public class AmarAlarmPlugin extends Plugin {

    /** অ্যাপের নিজস্ব অ্যালার্ম: group ("med" বা "alarm") + items [{id, at(ms), title, body}] */
    @PluginMethod
    public void scheduleAll(PluginCall call) {
        String group = call.getString("group", "alarm");
        JSArray items = call.getArray("items");
        if (items == null) items = new JSArray();
        int n = AmarAlarmStore.replaceGroup(getContext(), group, items);
        if (n < 0) {
            call.reject("অ্যালার্ম বসানো যায়নি");
            return;
        }
        JSObject r = new JSObject();
        r.put("count", n);
        call.resolve(r);
    }

    @PluginMethod
    public void cancelGroup(PluginCall call) {
        AmarAlarmStore.replaceGroup(getContext(), call.getString("group", "alarm"), new JSArray());
        call.resolve();
    }

    /** ফোনের নিজস্ব ঘড়ির অ্যাপে অ্যালার্ম বসানো (ঐচ্ছিক ব্যাকআপ) */
    @PluginMethod
    public void setAlarm(PluginCall call) {
        Integer hour = call.getInt("hour");
        Integer minute = call.getInt("minute");
        if (hour == null || minute == null) {
            call.reject("hour ও minute দরকার");
            return;
        }
        String label = call.getString("label", "");
        Intent i = new Intent(AlarmClock.ACTION_SET_ALARM);
        i.putExtra(AlarmClock.EXTRA_HOUR, hour.intValue());
        i.putExtra(AlarmClock.EXTRA_MINUTES, minute.intValue());
        i.putExtra(AlarmClock.EXTRA_MESSAGE, label);
        i.putExtra(AlarmClock.EXTRA_SKIP_UI, true);
        i.putExtra(AlarmClock.EXTRA_VIBRATE, true);
        JSArray arr = call.getArray("days");
        if (arr != null && arr.length() > 0) {
            ArrayList<Integer> d = new ArrayList<Integer>();
            for (int k = 0; k < arr.length(); k++) {
                d.add(Integer.valueOf(arr.optInt(k)));
            }
            i.putExtra(AlarmClock.EXTRA_DAYS, d);
        }
        i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        try {
            getContext().startActivity(i);
            call.resolve();
        } catch (Exception e) {
            call.reject("ফোনে ঘড়ির অ্যাপ পাওয়া যায়নি");
        }
    }
}
''',
}
mains = glob.glob(os.path.join(ROOT, 'android/app/src/main/java/**/MainActivity.java'), recursive=True)
if mains:
    mp = mains[0]; mdir = os.path.dirname(mp)
    pk = re.search(r'^package\s+([\w.]+);', open(mp, encoding='utf-8').read(), re.M).group(1)
    for name, src in JAVA.items():
        open(os.path.join(mdir, name + '.java'), 'w', encoding='utf-8').write(src.replace('__PK__', pk))
    main = """package %s;

import android.os.Bundle;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(AmarAlarmPlugin.class);
        super.onCreate(savedInstanceState);
    }
}
""" % pk
    open(mp, 'w', encoding='utf-8').write(main)
    recv = ('\n        <receiver android:name="%s.AmarAlarmReceiver" android:exported="false" />'
            '\n        <receiver android:name="%s.AmarBootReceiver" android:exported="true">'
            '\n            <intent-filter>'
            '\n                <action android:name="android.intent.action.BOOT_COMPLETED" />'
            '\n                <action android:name="android.intent.action.MY_PACKAGE_REPLACED" />'
            '\n                <action android:name="android.intent.action.TIME_SET" />'
            '\n                <action android:name="android.intent.action.TIMEZONE_CHANGED" />'
            '\n            </intent-filter>'
            '\n        </receiver>\n    ') % (pk, pk)
    if 'AmarAlarmReceiver' not in m:
        m = m.replace('</application>', recv + '</application>', 1)
    print('AmarAlarm native ok', pk)
else:
    print('WARNING: MainActivity.java পাওয়া যায়নি')

open(MAN, 'w', encoding='utf-8').write(m)
print('prepare ok')

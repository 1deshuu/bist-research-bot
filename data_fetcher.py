# -*- coding: utf-8 -*-
"""
Borsa Istanbul Canli Veri Cekme Modulu
- Is Yatirim'dan guncel bilanço, gelir tablosu, nakit akis ve rasyolari ceker.
- yfinance uzerinden eksik rasyolari veya baglanti hatalarini tamamlar.
- Google News RSS uzerinden en son KAP bildirimlerini ve piyasa haberlerini ceker.
"""

import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import re
import os
import json
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# BIST Hisseleri Sozluk Onbellegi (bist_stocks.json)
BIST_STOCKS_MAP = {}
try:
    _json_path = os.path.join(os.path.dirname(__file__), "bist_stocks.json")
    if os.path.exists(_json_path):
        with open(_json_path, "r", encoding="utf-8") as f:
            BIST_STOCKS_MAP = json.load(f)
except Exception:
    pass

def clean_ticker(ticker: str) -> str:
    """Hisse kodunu temizler ve standart hale getirir (orn. THYAO.IS -> THYAO)"""
    t = ticker.strip().upper()
    if t.endswith('.IS'):
        t = t[:-3]
    return t

def format_currency_amount(val_str: str) -> str:
    """
    İş Yatırım veya yfinance'ten gelen mnTL / TL tutarlarını insan okuyuşuna uygun
    Trilyon, Milyar veya Milyon TL birimlerine dönüştürür.
    Örnek: '3.262.315,0 mnTL' -> '3,26 Trilyon TL'
           '727009,0 mnTL' -> '727,0 Milyar TL'
           '620.383,0 mnTL' -> '620,4 Milyar TL'
           '2.100,9 mnTL' -> '2,1 Milyar TL'
           '421,4 mnTL' -> '421,4 Milyon TL'
           '-130.717,9 mnTL' -> '-130,7 Milyar TL'
    """
    if not val_str or str(val_str).strip() in ['-', 'Yok', 'N/A', '', 'None']:
        return '-'
    
    val_clean = str(val_str).strip()
    if any(k in val_clean for k in ['Trilyon', 'Milyar', 'Milyon']):
        return val_clean

    clean = re.sub(r'(?i)\s*(?:mn\s*TL|mn|TL)\s*$', '', val_clean).strip()
    clean = clean.replace(' ', '')
    
    try:
        if ',' in clean:
            num_str = clean.replace('.', '').replace(',', '.')
        else:
            if clean.count('.') > 1:
                num_str = clean.replace('.', '')
            else:
                num_str = clean
        val_mn = float(num_str)
    except Exception:
        return val_str
    
    is_neg = val_mn < 0
    abs_mn = abs(val_mn)
    
    if abs_mn >= 1_000_000:
        tril = abs_mn / 1_000_000
        fmt = f"{tril:.2f}".replace('.', ',')
        unit = "Trilyon TL"
    elif abs_mn >= 1_000:
        bil = abs_mn / 1_000
        fmt = f"{bil:.1f}".replace('.', ',')
        unit = "Milyar TL"
    elif abs_mn >= 1:
        fmt = f"{abs_mn:.1f}".replace('.', ',').rstrip('0').rstrip(',')
        unit = "Milyon TL"
    elif abs_mn > 0:
        fmt = f"{abs_mn:.2f}".replace('.', ',')
        unit = "Milyon TL"
    else:
        return "0 TL"
    
    sign = '-' if is_neg else ''
    return f"{sign}{fmt} {unit}"

def _fill_ratios_from_yfinance(symbol: str, target_dict: dict):
    """yfinance uzerinden eksik veya '-' olan rasyolari tamamlar."""
    try:
        import yfinance as yf
        t = yf.Ticker(f"{symbol}.IS")
        info = t.info or {}
        
        # 1. F/K
        if target_dict.get("F/K") in ["-", "", None, "A/D"]:
            pe = info.get("trailingPE") or info.get("forwardPE")
            if pe and pe > 0:
                target_dict["F/K"] = f"{pe:.1f}".replace('.', ',')

        # 2. PD/DD
        if target_dict.get("PD/DD") in ["-", "", None, "A/D"]:
            pb = info.get("priceToBook")
            if pb and pb > 0:
                target_dict["PD/DD"] = f"{pb:.1f}".replace('.', ',')

        # 3. FD/FAVÖK
        if target_dict.get("FD/FAVÖK") in ["-", "", None, "A/D"]:
            ev_ebitda = info.get("enterpriseToEbitda")
            if ev_ebitda is not None:
                target_dict["FD/FAVÖK"] = f"{ev_ebitda:.1f}".replace('.', ',')

        # 4. Net Borç
        if target_dict.get("Net Borç") in ["-", "", None]:
            debt = info.get("totalDebt")
            cash = info.get("totalCash")
            if debt is not None and cash is not None:
                net_debt = debt - cash
                target_dict["Net Borç"] = format_currency_amount(f"{net_debt / 1e6:.1f}")

        # 5. Halka Açıklık Oranı
        if target_dict.get("Halka Açıklık Oranı (%)") in ["-", "", None]:
            shares = info.get("sharesOutstanding")
            fl = info.get("floatShares")
            if shares and fl:
                ff = (fl / shares) * 100
                target_dict["Halka Açıklık Oranı (%)"] = f"{ff:.1f}".replace('.', ',')

        # 6. Piyasa Değeri
        if target_dict.get("Piyasa Değeri") in ["-", "", None]:
            mc = info.get("marketCap")
            if mc:
                target_dict["Piyasa Değeri"] = format_currency_amount(f"{mc / 1e6:.1f}")

        # 7. Kapanış Fiyatı
        if target_dict.get("Kapanış Fiyatı (TL)") in ["-", "", None]:
            reg_price = info.get("regularMarketPrice") or info.get("previousClose")
            if reg_price:
                target_dict["Kapanış Fiyatı (TL)"] = f"{reg_price:.2f}".replace('.', ',')
                
    except Exception:
        pass

def fetch_company_card(symbol: str) -> dict:
    """Is Yatirim Sirket Karti uzerinden guncel rasyolari ve finansallari ceker; eksikleri yfinance ile tamamlar."""
    symbol = clean_ticker(symbol)
    known_title = BIST_STOCKS_MAP.get(symbol, symbol)

    result = {
        "symbol": symbol,
        "title": known_title,
        "business": "",
        "ratios": {
            "F/K": "-",
            "PD/DD": "-",
            "FD/FAVÖK": "-",
            "FD/Satışlar": "-",
            "Piyasa Değeri": "-",
            "Net Borç": "-",
            "Halka Açıklık Oranı (%)": "-",
            "Yabancı Oranı (%)": "-",
            "Ortalama Hacim ($)": "-",
            "Kapanış Fiyatı (TL)": "-"
        },
        "financials": {},
        "ownership": {},
        "success": False
    }

    url = f"https://www.isyatirim.com.tr/tr-tr/analiz/hisse/Sayfalar/sirket-karti.aspx?hisse={symbol}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7'
    }

    # 1. Is Yatirim Denemesi (2 tekrar)
    data_map = {}
    for attempt in range(2):
        try:
            resp = requests.get(url, headers=headers, timeout=12)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                for tr in soup.find_all('tr'):
                    cells = [c.text.strip().replace('\xa0', ' ') for c in tr.find_all(['th', 'td'])]
                    if len(cells) >= 2:
                        key = cells[0].strip()
                        val = cells[1].strip()
                        if key and val and key not in data_map:
                            data_map[key] = val
                if data_map:
                    break
        except Exception:
            time.sleep(0.5)

    if data_map:
        result["title"] = data_map.get("Ünvanı", known_title)
        result["business"] = data_map.get("Faal Alanı", "")
        result["ratios"] = {
            "F/K": data_map.get("F/K", "-"),
            "PD/DD": data_map.get("PD/DD", "-"),
            "FD/FAVÖK": data_map.get("FD/FAVÖK", "-"),
            "FD/Satışlar": data_map.get("FD/Satışlar", "-"),
            "Piyasa Değeri": format_currency_amount(data_map.get("Piyasa Değeri", "-")),
            "Net Borç": format_currency_amount(data_map.get("Net Borç", "-")),
            "Halka Açıklık Oranı (%)": data_map.get("Halka Açıklık Oranı (%)", "-"),
            "Yabancı Oranı (%)": data_map.get("Yabancı Oranı (%)", "-"),
            "Ortalama Hacim ($)": data_map.get("Ort Hacim (mn$) 3A/12A", "-"),
            "Kapanış Fiyatı (TL)": data_map.get("Kapanış (TL)", data_map.get("Kod: Kapanış Fiyat (TL)", "-")),
        }
        result["financials"] = {
            "Satış Gelirleri": data_map.get("Satış Gelirleri", data_map.get("Satışlar", "-")),
            "Satışların Maliyeti": data_map.get("Satışların Maliyeti (-)", "-"),
            "BRÜT KÂR": data_map.get("BRÜT KAR (ZARAR)", data_map.get("Ticari Faaliyetlerden Brüt Kar (Zarar)", "-")),
            "FAVÖK": data_map.get("FAVÖK", "-"),
            "Faaliyet Kârı": data_map.get("FAALİYET KARI (ZARARI)", "-"),
            "Finansman Giderleri": data_map.get("Finansman Giderleri (-)", data_map.get("Finansman Giderleri", "-")),
            "Net Dönem Kârı": data_map.get("Net Kar", data_map.get("DÖNEM KARI (ZARARI)", "-")),
            "Dönen Varlıklar": data_map.get("Dönen Varlıklar", "-"),
            "Nakit ve Benzerleri": data_map.get("Nakit ve Nakit Benzerleri", "-"),
            "Ticari Alacaklar": data_map.get("Ticari Alacaklar", "-"),
            "Stoklar": data_map.get("Stoklar", "-"),
            "Duran Varlıklar": data_map.get("Duran Varlıklar", "-"),
            "Toplam Varlıklar": data_map.get("TOPLAM VARLIKLAR", "-"),
            "Kısa Vadeli Borçlar": data_map.get("Kısa Vadeli Yükümlülükler", "-"),
            "Kısa Vadeli Finansal Borçlar": data_map.get("Finansal Borçlar", "-"),
            "Uzun Vadeli Borçlar": data_map.get("Uzun Vadeli Yükümlülükler", "-"),
            "Özkaynaklar": data_map.get("Özkaynaklar", data_map.get("Ana Ortaklığa Ait Özkaynaklar", "-")),
            "Net Yabancı Para Pozisyonu": data_map.get("Net Yabancı Para Pozisyonu", data_map.get("Net YPP (Hedge Dahil)", "-")),
            "Yurtdışı Satışlar": data_map.get("Yurtdışı Satışlar", "-"),
            "Yurtiçi Satışlar": data_map.get("Yurtiçi Satışlar", "-"),
            "İşletme Faaliyetlerinden Net Nakit": data_map.get("İşletme Faaliyetlerinden Kaynaklanan Net Nakit", "-"),
            "Serbest Nakit Akımı": data_map.get("Serbest Nakit Akım", "-"),
            "Yatırım Harcamaları (Capex)": data_map.get("Sabit Sermaye Yatırımları", data_map.get("Yatırım Faaliyetlerinden Kaynaklanan Nakit", "-")),
        }
        result["success"] = True

    # 2. Eksik veya '-' Rasyolari yfinance ile Doldur
    _fill_ratios_from_yfinance(symbol, result["ratios"])
    if not result["success"] and any(v != "-" for v in result["ratios"].values()):
        result["success"] = True

    return result

def fetch_kap_and_news(symbol: str, max_items: int = 15) -> list:
    """Hisse ile ilgili guncel KAP bildirimleri ve haber basliklarini ceker."""
    symbol = clean_ticker(symbol)
    query = f"{symbol} KAP bildirim OR hisse"
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=tr&gl=TR&ceid=TR:tr"

    news_list = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)

            for item in root.findall('.//item')[:max_items]:
                title = item.find('title').text if item.find('title') is not None else ""
                pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
                link = item.find('link').text if item.find('link') is not None else ""
                source = item.find('source').text if item.find('source') is not None else "KAP / Medya"

                clean_title = title
                if " - " in title:
                    clean_title = title.rsplit(" - ", 1)[0]

                news_list.append({
                    "title": clean_title,
                    "date": pub_date,
                    "source": source,
                    "link": link
                })
    except Exception as e:
        news_list.append({
            "title": f"Haber tarama uyarisi: {e}",
            "date": datetime.now().strftime("%d.%m.%Y"),
            "source": "Sistem",
            "link": ""
        })

    return news_list

def fetch_technical_data(symbol: str) -> dict:
    """Son 90 gunluk fiyat hareketlerinden temel teknik gostergeleri hesaplar."""
    symbol = clean_ticker(symbol)
    
    # 1. Oncelik: yfinance uzerinden hizli ve guvenli teknik veri
    try:
        import yfinance as yf
        df = yf.Ticker(f"{symbol}.IS").history(period="3mo")
        if df is not None and not df.empty:
            closes = df['Close'].dropna().tolist()
            if closes:
                last_price = closes[-1]
                sma20 = sum(closes[-20:]) / min(len(closes), 20)
                sma50 = sum(closes[-50:]) / min(len(closes), 50)
                high90 = max(df['High'].dropna().tolist())
                low90 = min(df['Low'].dropna().tolist())
                ret30 = ((last_price - closes[-min(22, len(closes))]) / closes[-min(22, len(closes))]) * 100
                return {
                    "Son Kapanış Fiyatı (TL)": round(last_price, 2),
                    "20 Günlük Hareketli Ortalama (SMA 20)": round(sma20, 2),
                    "50 Günlük Hareketli Ortalama (SMA 50)": round(sma50, 2),
                    "90 Günlük En Yüksek (Direnç / Zirve)": round(high90, 2),
                    "90 Günlük En Düşük (Destek / Dip)": round(low90, 2),
                    "Son 1 Aylık Fiyat Değişimi (%)": f"%{round(ret30, 2)}",
                    "Fiyat / SMA20 Konumu": "SMA20 Üzerinde (Kısa Vade Pozitif)" if last_price >= sma20 else "SMA20 Altında (Kısa Vade Zayıf)"
                }
    except Exception:
        pass

    # 2. Alternatif: isyatirimhisse
    try:
        from isyatirimhisse import fetch_stock_data
        from datetime import timedelta
        start = (datetime.now() - timedelta(days=90)).strftime('%d-%m-%Y')
        df = fetch_stock_data(symbols=symbol, start_date=start)
        if df is not None and not df.empty:
            closes = df['HGDG_KAPANIS'].dropna().tolist()
            if closes:
                last_price = closes[-1]
                sma20 = sum(closes[-20:]) / min(len(closes), 20)
                sma50 = sum(closes[-50:]) / min(len(closes), 50)
                high90 = max(df['HGDG_MAX'].dropna().tolist())
                low90 = min(df['HGDG_MIN'].dropna().tolist())
                ret30 = ((last_price - closes[-min(22, len(closes))]) / closes[-min(22, len(closes))]) * 100
                return {
                    "Son Kapanış Fiyatı (TL)": round(last_price, 2),
                    "20 Günlük Hareketli Ortalama (SMA 20)": round(sma20, 2),
                    "50 Günlük Hareketli Ortalama (SMA 50)": round(sma50, 2),
                    "90 Günlük En Yüksek (Direnç / Zirve)": round(high90, 2),
                    "90 Günlük En Düşük (Destek / Dip)": round(low90, 2),
                    "Son 1 Aylık Fiyat Değişimi (%)": f"%{round(ret30, 2)}",
                    "Fiyat / SMA20 Konumu": "SMA20 Üzerinde (Kısa Vade Pozitif)" if last_price >= sma20 else "SMA20 Altında (Kısa Vade Zayıf)"
                }
    except Exception:
        pass

    return {}

def prepare_analysis_context(symbol: str) -> dict:
    """Tüm verileri birlestirip botlar icin hazir metin ve sozluk formatina donusturur."""
    card = fetch_company_card(symbol)
    news = fetch_kap_and_news(symbol)
    tech = fetch_technical_data(symbol)

    context_lines = []
    context_lines.append(f"=== {card['symbol']} CANLI PİYASA VE FİNANSAL VERİ RAPORU ===")
    context_lines.append(f"Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    context_lines.append(f"Şirket Ünvanı: {card.get('title', symbol)}")
    if card.get("business"):
        context_lines.append(f"Faaliyet Alanı: {card.get('business')}")

    context_lines.append("\n--- TEMEL PİYASA RASYOLARI VE ORANLAR ---")
    for k, v in card.get("ratios", {}).items():
        context_lines.append(f"• {k}: {v}")

    if tech:
        context_lines.append("\n--- TEKNİK GÖSTERGELER VE FİYAT TRENDİ ---")
        for k, v in tech.items():
            context_lines.append(f"• {k}: {v}")

    context_lines.append("\n--- FİNANSAL TABLO KALEMLERİ (SON DÖNEM) ---")
    for k, v in card.get("financials", {}).items():
        context_lines.append(f"• {k}: {v}")

    context_lines.append("\n--- SON KAP BİLDİRİMLERİ VE PİYASA HABERLERİ ---")
    if news:
        for idx, item in enumerate(news, 1):
            context_lines.append(f"{idx}. [{item.get('date', '')}] {item.get('title', '')} (Kaynak: {item.get('source', '')})")
    else:
        context_lines.append("Yakın tarihli bildirim bulunamadı.")

    formatted_context = "\n".join(context_lines)

    return {
        "symbol": card["symbol"],
        "title": card.get("title", symbol),
        "card": card,
        "news": news,
        "technical": tech,
        "context_text": formatted_context
    }

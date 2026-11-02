# -*- coding: utf-8 -*-
"""
Borsa İstanbul Çok Ajanlı Hisse Senedi Araştırma Portali
Modern Kurumsal Finans UI Bileşenleri ve Rapor Formatlayıcı
"""

import re
import streamlit as st

def clean_verdict_text(v: str) -> str:
    """
    Karar metnini tek ve net bir kelimeye indirger.
    Parantez içi detayları, slash (/) alternatiflerini ve gereksiz ekleri temizler.
    Örn: 'RİSKLİ (DAĞINIK/PAZARLAMA)' -> 'RİSKLİ'
         'POZİTİF (Toplu/Fon İlgisi)' -> 'POZİTİF'
         'ALMA / KAÇIN' -> 'ALMA'
         'GÜÇLÜ KATALİZÖR' -> 'GÜÇLÜ'
         'BASKI ALTINDA' -> 'BASKI'
         'YÜKSEK RİSK' -> 'YÜKSEK'
         'İZLE-VE-GÖR' -> 'İZLE'
    """
    if not v:
        return ""
    
    # 1. Parantez içindeki tüm açıklamaları temizle
    v = re.sub(r'\(.*?\)', '', v).strip()
    
    # 2. Slash (/) ile ayrılmış alternatiflerden ilkini al
    if '/' in v:
        v = v.split('/')[0].strip()
        
    # 3. Köşeli parantez, iki nokta ve markdown işaretlerini temizle
    v = v.replace('[', '').replace(']', '').replace('*', '').replace(':', '').strip()
    v_upper = v.upper()

    # 4. Bilinen çok kelimeli veya ekli kalıpları tek kelimeye indir
    phrase_map = {
        'GÜÇLÜ KATALİZÖR': 'GÜÇLÜ',
        'BASKI ALTINDA': 'BASKI',
        'YÜKSEK RİSK': 'YÜKSEK',
        'ORTA RİSK': 'ORTA',
        'DÜŞÜK RİSK': 'DÜŞÜK',
        'İZLE-VE-GÖR': 'İZLE',
        'İZLE VE GÖR': 'İZLE',
        'NİHAİ KARAR AL': 'AL',
        'NİHAİ KARAR ALMA': 'ALMA',
        'NİHAİ KARAR İZLE': 'İZLE'
    }
    for phrase, single in phrase_map.items():
        if phrase in v_upper:
            return single

    # 5. Kelime listesinden ilk anlamlı terimi al
    words = v.split()
    if len(words) > 1 and words[0].upper() in ['GÜÇLÜ', 'POZİTİF', 'RİSKLİ', 'SAĞLAM', 'CAZİP', 'MAKUL', 'PAHALI', 'AL', 'ALMA', 'İZLE', 'DENGELİ', 'İSTİKRARLI']:
        return words[0]

    return v.strip()


def classify_verdict(verdict_str: str):
    """
    Analist veya Portföy Stratejisti kararını 3 kesin renge sınıflandırır:
    - Kırmızı (Kötü / Riskli / Baskı): BASKI, RİSKLİ, PAHALI, KATALİZÖRSÜZ, YÜKSEK, ALMA, SAT, KAÇIN
    - Sarı (Orta / Nötr / Dengeli): NÖTR, MAKUL, DENGELİ, İSTİKRARLI, ORTA, İZLE, BEKLE
    - Yeşil (Olumlu / İyi / Fırsat): GÜÇLÜ, CAZİP, SAĞLAM, POZİTİF, AL, DÜŞÜK, YÖNETİLEBİLİR
    """
    if not verdict_str:
        return "gray", "rgba(100, 116, 139, 0.15)", "#64748b", "#94a3b8"
    
    t = verdict_str.upper()

    # 1. Kırmızı Kontrolleri (Önemli: BASKI önce kontrol edilir)
    red_keywords = [
        "BASKI", "RİSKLİ", "PAHALI", "KATALİZÖRSÜZ", "YÜKSEK", 
        "ALMA", "SAT", "KAÇIN", "NEGATİF", "BOZULMA", "ZAYIF"
    ]
    if any(k in t for k in red_keywords):
        return "red", "rgba(239, 68, 68, 0.16)", "#ef4444", "#f87171"

    # 2. Sarı / Nötr Kontrolleri
    yellow_keywords = [
        "NÖTR", "MAKUL", "DENGELİ", "İSTİKRARLI", "ORTA", 
        "İZLE", "GÖR", "BEKLE", "TEMKİNLİ"
    ]
    if any(k in t for k in yellow_keywords):
        return "yellow", "rgba(245, 158, 11, 0.16)", "#f59e0b", "#fbbf24"

    # 3. Yeşil / Pozitif Kontrolleri
    green_keywords = [
        "GÜÇLÜ", "CAZİP", "SAĞLAM", "POZİTİF", "YÖNETİLEBİLİR", "DÜŞÜK", "FIRSAT"
    ]
    if any(k in t for k in green_keywords) or re.search(r'\bAL\b', t):
        return "green", "rgba(16, 185, 129, 0.16)", "#10b981", "#34d399"

    return "yellow", "rgba(245, 158, 11, 0.16)", "#f59e0b", "#fbbf24"


def extract_bot_verdict(bot_text: str):
    """
    Tekil analist botunun kararını ayıklar ve tek net kelimeye indirger.
    """
    if not bot_text:
        return None
    
    pattern = r'[^\w\n]*([A-ZÇĞİÖŞÜa-zçğıöşü\s&]+?(?:KARAR[Iİ]?|DEĞERLENDİRME(?:Sİ)?))[\s:*]+(?:\[|\*\*)*\s*(?:\n\s*)?([A-ZÇĞİÖŞÜa-zçğıöşü\s\-\(\)\/]+?)(?:\]|\*\*|\n|$)'
    m = re.search(pattern, bot_text, re.IGNORECASE)
    if m:
        raw_v = m.group(2).strip()
        cleaned_v = clean_verdict_text(raw_v)
        return cleaned_v
    return None


def extract_verdict_info(strategist_text: str):
    """
    Portföy Stratejisti metninden Nihai Karar, Portföy Ağırlığı ve Yatırım Ufkunu eksiksiz ve hatasız belirler.
    Metin kırpılmalarını ve yarım kalan cümleleri engeller.
    """
    raw_v = extract_bot_verdict(strategist_text) or "İZLE"
    v_upper = raw_v.upper()

    if any(k in v_upper for k in ["ALMA", "SAT", "KAÇIN", "NEGATİF"]):
        verdict = "ALMA"
        weight = "%0 (Pozisyon Açılmamalı)"
        horizon = "Yok (İşlem Yapılmamalı)"
        strategy_desc = "Mevcut seviyelerde risk-getiri dengesi yeni pozisyon açmayı desteklememektedir."
    elif re.search(r'\bAL\b', v_upper):
        verdict = "AL"
        # Metinde belirtilen spesifik yüzde var mı kontrol et
        pct_m = re.search(r'%\s*([1-9]\d*(?:\s*-\s*\d+)?)', strategist_text)
        if pct_m:
            weight = f"%{pct_m.group(1)} (Kademeli)"
        else:
            weight = "%5 - %10 (Kademeli)"
        
        if "UZUN" in strategist_text.upper():
            horizon = "12+ Ay (Uzun Vade)"
        else:
            horizon = "6 - 12 Ay (Orta Vade)"
        strategy_desc = "Kademeli alım seviyeleri ve çeyreklik finansal kilometre taşları tanımlanmıştır."
    else:
        verdict = "İZLE"
        weight = "%0 (Beklemede)"
        horizon = "İzleme Sürecinde (1–3 Çeyrek)"
        strategy_desc = "Somut toparlanma ve katalizör teyit edilene kadar bekleme önerilir."

    return verdict, weight, horizon, strategy_desc


def format_as_nested_bullets(raw_text: str) -> str:
    """
    Analiz metnini kullanıcı talebine uygun olarak hiyerarşik maddelere dönüştürür:
    - Ana maddeler: İçi dolu yuvarlak (●)
    - Alt maddeler / açıklamalar: İçi boş yuvarlak (○), ana maddenin içine girintili ve görsel olarak bağlı
    - Altında hiçbir açıklama / alt madde bulunmayan başlıkları ASLA göstermez (kullanıcı talebi).
    - Karar satırlarını tamamen temizler (iki defa yazılmasını engeller).
    - Asla ayrı kutucuklama yapmaz (tek bir akıcı kart içinde hiyerarşi oluşturur).
    """
    if not raw_text:
        return ""

    lines = raw_text.strip().split('\n')
    cleaned_lines = []

    # 1. Filtrele: Karar satırlarını tamamen ayıkla (Detaylı inceleme içinde kararın tekrar etmesini engeller)
    verdict_words = r'(?:AL|SAT|TUT|İZLE|ALMA|GÜÇLÜ|NÖTR|RİSKLİ|CAZİP|MAKUL|PAHALI|SAĞLAM|DENGELİ|BASKI|İSTİKRARLI|KATALİZÖRSÜZ|POZİTİF|DÜŞÜK|ORTA|YÜKSEK)'
    verdict_regex = re.compile(rf'(?:KARAR[Iİ]?|DEĞERLENDİRME(?:Sİ)?)\s*:\s*\[?\s*{verdict_words}', re.IGNORECASE)

    for line in lines:
        s = line.strip()
        if not s:
            continue
        if verdict_regex.search(s):
            continue
        cleaned_lines.append(line)

    # 2. Satır satır başlık ve alt madde ayrıştırma
    sections = []
    current_title = None
    current_sub_items = []

    known_main_titles = [
        # Bot 7 (Portföy Stratejisti)
        'Analist Raporlarının Sentezi ve Güçlü-Zayıf Yönler',
        'Portföy Ağırlığı ve Kademeli Alım Seviyeleri',
        'Kritik Riskler ve Çıkış Koşulları',
        'Yatırım Ufku ve Beklenti Özeti',
        'Nihai Karar Değerlendirmesi',
        'Genel Değerlendirme',
        # Bot 1
        'Yönetim Kalitesi ve Kurumsal Yapı Değerlendirmesi',
        'İmtiyazlı Paylar ve Ortaklık Kontrol Haritası',
        'İlişkili Taraf ve Kaynak Aktarımı Taraması',
        'Pay Satış ve Tipe Dönüşüm Riski',
        'Sonuç ve Yönetim Değerlendirmesi',
        # Bot 2
        'Fiyatlama Gücü ve Marj Sürdürülebilirliği',
        'Temel Çarpanlar ve Değerleme Seviyeleri',
        'Sektörel ve Tarihsel Göreceli Konum',
        'Ölçek Avantajı ve Giriş Bariyeri',
        'Sonuç ve Değerleme Özeti',
        # Bot 3
        'Bilanço Yapısı ve Likidite Durumu',
        'Borçluluk ve Borç Çevrim Analizi',
        'Nakit Akış Kalitesi ve Serbest Nakit Akımı',
        'Finansman Giderleri ve Kâr Baskısı',
        'Sonuç ve Mali Sağlık Notu',
        # Bot 4
        'Üretim Kapasitesi ve Büyüme Potansiyeli',
        'Devam Eden Yatırımlar ve Şirket Bildirimleri',
        'Katalizör Takvimi ve Zamanlama',
        'Yatırım Teşvikleri ve Katma Değer Analizi',
        'Sonuç ve Kapasite Özeti',
        # Bot 5
        'Takas Konsantrasyonu ve Mülkiyet Dağılımı',
        'Yatırım Fonları ve Kurumsal Pozisyonlanma',
        'Mal Dağıtımı ve Piyasa Doygunluk Analizi',
        'Halka Açıklık ve İşlem Likiditesi',
        'Sonuç ve Tahta Dinamiği Notu',
        # Bot 6
        'Boğaların Görmezden Geldiği Temel Kör Noktalar',
        'Kırılgan Taşıyıcı Kolon Varsayımı',
        'Tahsilat, Regülasyon ve Makro Risk Faktörleri',
        'Tezi Çökertecek Olası Risk Koşulları',
        'Sonuç ve Risk Analisti Özeti'
    ]

    known_sub_titles = [
        'Yatırım Vadesi', 'Beklenti Özeti',
        '1. Kademe', '2. Kademe', '3. Kademe',
        'Kademe 1', 'Kademe 2', 'Kademe 3',
        'Portföy Ağırlığı', 'Kademeli Alım', 'Kademeli Alım Seviyeleri',
        'Hedef Seviye', 'Stop-Loss', 'Zarar Kes', 'Çıkış Koşulları',
        'Kısa Vade', 'Orta Vade', 'Uzun Vade'
    ]

    def is_canonical_main_title(candidate: str) -> bool:
        c = candidate.strip().lower()
        for m in known_main_titles:
            m_lower = m.lower()
            if c == m_lower or c.startswith(m_lower + ':') or m_lower in c:
                return True
        return False

    def is_title_line(line_str):
        # Markdown başlığı (### Başlık)
        if line_str.startswith(('###', '##')):
            return True, line_str.lstrip('#').strip(), '', True
        
        # Madde imlerini temizle (sadece bullet simgeleri ve tekli tire/yıldız)
        stripped = re.sub(r'^(?:[•●○◦]|(?:[-*](?!\*)\s*))\s*', '', line_str).strip()
        stripped = re.sub(r'^\d+[\.\)]\s+', '', stripped).strip()
        
        # **Başlık:** veya **Başlık**:
        m_bold = re.match(r'^\*\*([^*]+)\*\*:?\s*(.*)$', stripped)
        if m_bold:
            t, rest = m_bold.group(1).rstrip(':').strip(), m_bold.group(2).strip()
            is_main = is_canonical_main_title(t)
            return True, t, rest, is_main
        
        # Bilinen ana başlıklar
        for m in known_main_titles:
            if stripped.lower() == m.lower() or stripped.lower().startswith(m.lower() + ':'):
                rest = stripped[len(m):].lstrip(':').strip()
                return True, m, rest, True
        
        # Bilinen alt başlıklar
        for k in known_sub_titles:
            if stripped.lower() == k.lower() or stripped.lower().startswith(k.lower() + ':'):
                rest = stripped[len(k):].lstrip(':').strip()
                return True, k, rest, False

        # Başlık: Metin (iki nokta ile ayrılmış ve başlık kısmı mantıklı uzunlukta)
        if ':' in stripped and not re.search(r'\d:\d', stripped):
            parts = stripped.split(':', 1)
            candidate_title = parts[0].strip()
            rest = parts[1].strip()
            words = candidate_title.split()
            if 1 <= len(words) <= 9 and len(candidate_title) <= 65:
                if not candidate_title.endswith(('.', '!', '?')):
                    is_main = is_canonical_main_title(candidate_title)
                    return True, candidate_title, rest, is_main

        return False, '', '', False

    def clean_sub_text(text_str):
        # Akışı bozan 'NİHAİ KARAR [ALMA] olduğu için' gibi kalıpları düzelt
        t = re.sub(r'NİHAİ\s+KARAR\s*\[ALMA\]\s*olduğu\s+için', 'Kararın ALMA yönünde olması nedeniyle', text_str, flags=re.IGNORECASE)
        t = re.sub(r'NİHAİ\s+KARAR\s*\[AL\]\s*olduğu\s+için', 'Kararın AL yönünde olması doğrultusunda', t, flags=re.IGNORECASE)
        t = re.sub(r'NİHAİ\s+KARAR\s*\[İZLE(?:-VE-GÖR)?\]\s*olduğu\s+için', 'İzleme tavsiyesi doğrultusunda', t, flags=re.IGNORECASE)
        t = re.sub(r'Karar\s*\[ALMA\]\s*olduğu\s+için', 'Kararın ALMA yönünde olması nedeniyle', t, flags=re.IGNORECASE)
        t = re.sub(r'Çıkış\s*/\s*Maliyetten\s+Kaçış\s+Koşulları:', 'Çıkış Koşulları:', t, flags=re.IGNORECASE)
        t = t.replace('izlenmeiidir', 'izlenmelidir')
        
        # Sadece liste imlerini temizle (cümle başındaki sayılara veya harflere dokunma!)
        t = re.sub(r'^(?:[•●○◦]|(?:[-*](?!\*)\s*))\s*', '', t).strip()
        t = re.sub(r'^\d+[\.\)]\s+', '', t).strip()
        
        # İçi kalın/italik markdown vurgularını HTML'e çevir
        t = re.sub(r'\*\*([^*]+)\*\*', r'<strong style="color: #f8fafc; font-weight: 700;">\1</strong>', t)
        t = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<em style="color: #94a3b8;">\1</em>', t)

        # Cümlenin baş harfini daima büyük yap (Türkçe karakter uyumlu)
        if t:
            if t[0] == 'i':
                t = 'İ' + t[1:]
            elif t[0] == 'ı':
                t = 'I' + t[1:]
            elif t[0].islower():
                t = t[0].upper() + t[1:]

        return t

    for raw_line in cleaned_lines:
        s = raw_line.strip()
        indent_level = len(raw_line) - len(raw_line.lstrip())
        is_indented = indent_level >= 2

        is_t, title, rest, is_main = is_title_line(s)
        
        # Eğer aktif bir ana başlık varsa ve bu satır açıkça kanonik bir ana başlık değilse alt madde sayılır
        if current_title is not None and not is_main:
            is_sub_header = True
        else:
            is_sub_header = False

        if is_t and not is_sub_header:
            # Yeni bir ana başlık başlıyor
            if current_title:
                sections.append((current_title, current_sub_items))
            c_title = title.rstrip(':').strip('*').strip()
            c_title = re.sub(r'\s*\(%\)', '', c_title)
            c_title = re.sub(r'\s*\(Stop\)', '', c_title, flags=re.IGNORECASE)
            c_title = c_title.replace('Çıkış (Stop) Şartları', 'Çıkış Koşulları')
            current_title = c_title
            current_sub_items = []
            if rest:
                cleaned_rest = clean_sub_text(rest)
                if cleaned_rest:
                    current_sub_items.append(cleaned_rest)
        else:
            # Mevcut ana başlığın alt maddesi
            if is_t:
                cleaned_rest = clean_sub_text(rest)
                item_text = f'<strong style="color: #f1f5f9;">{title}:</strong> {cleaned_rest}' if cleaned_rest else f'<strong style="color: #f1f5f9;">{title}:</strong>'
            else:
                item_text = clean_sub_text(s)

            if item_text:
                if current_title:
                    # Eğer önceki eleman boş bir alt başlıksa ve şimdiki metin onun açıklamasıysa birleştir
                    if current_sub_items and current_sub_items[-1].endswith(':</strong>'):
                        current_sub_items[-1] = f'{current_sub_items[-1]} {item_text}'
                    else:
                        current_sub_items.append(item_text)
                else:
                    current_title = title if is_t else 'Genel Değerlendirme'
                    if not is_t:
                        current_sub_items.append(item_text)

    if current_title:
        sections.append((current_title, current_sub_items))

    # HTML bloklarını oluştur (Kullanıcı talebi: Altında hiçbir açıklama / alt madde bulunmayan başlıklar ASLA gösterilmez)
    html_blocks = []
    for t, subs in sections:
        # Geçerli alt maddeleri filtrele
        valid_subs = [s for s in subs if s and s.strip()]
        if not valid_subs:
            continue
        
        sub_items_rendered = []
        for item in valid_subs:
            sub_items_rendered.append(
                f'<div style="display: flex; align-items: baseline; gap: 8px; margin-bottom: 6px;">'
                f'<span style="color: #94a3b8; font-size: 12px; line-height: 1; flex-shrink: 0;">○</span>'
                f'<span style="color: #cbd5e1; font-size: 14.2px; line-height: 1.68;">{item}</span>'
                f'</div>'
            )
        sub_content = ''.join(sub_items_rendered)
        sub_html = (
            f'<div style="margin-left: 24px; padding-left: 10px; border-left: 2px solid rgba(56, 189, 248, 0.25); margin-top: 6px; margin-bottom: 18px;">'
            f'{sub_content}'
            f'</div>'
        )
        
        block = (
            f'<div style="margin-bottom: 12px;">'
            f'<div style="font-size: 15px; font-weight: 700; color: #f1f5f9; display: flex; align-items: baseline; gap: 8px;">'
            f'<span style="color: #38bdf8; font-size: 13px; line-height: 1; flex-shrink: 0;">●</span>'
            f'<span>{t}</span>'
            f'</div>'
            f'{sub_html}'
            f'</div>'
        )
        html_blocks.append(block)

    return ''.join(html_blocks)



def render_executive_hero(strategist_text: str, symbol: str = "", company_title: str = ""):
    """En üstteki Portföy Stratejisti Kurumsal Özet Paneli."""
    verdict, weight, horizon, strategy_desc = extract_verdict_info(strategist_text)
    color_type, bg, border, text_color = classify_verdict(verdict)

    badge_text = f"NİHAİ KARAR: {verdict}"

    with st.container(border=True):
        col_main, col_badge = st.columns([3.2, 1.3])
        with col_main:
            st.markdown("### Portföy Stratejisti Değerlendirmesi")
            st.markdown(
                "6 bağımsız analistin tüm bulguları sentezlenmiş; değerleme, borçluluk, yönetim ve "
                "piyasa dinamikleri doğrultusunda kurum standartlarında nihai yatırım mutabakatı oluşturulmuştur."
            )
        with col_badge:
            single_line_badge = (
                f'<div style="background:{bg}; border:2px solid {border}; color:{text_color}; '
                f'padding:10px 16px; border-radius:10px; font-weight:800; font-size:14.5px; text-align:center; '
                f'margin-top:4px; letter-spacing:0.4px; box-shadow:0 2px 10px {bg};">{badge_text}</div>'
            )
            st.markdown(single_line_badge, unsafe_allow_html=True)

        st.markdown("---")

        c1, c2, c3 = st.columns(3)
        with c1:
            st.caption("ÖNERİLEN PORTFÖY AĞIRLIĞI")
            st.markdown(f"**{weight}**")
        with c2:
            st.caption("YATIRIM UFKU (VADE)")
            st.markdown(f"**{horizon}**")
        with c3:
            st.caption("STRATEJİ & EYLEM ÖZETİ")
            st.markdown(f"*{strategy_desc}*")


def render_portfolio_strategist_sections(strategist_text: str):
    """Portföy Stratejistinin detay metnini ayrı kutucuklama yapmadan, hiyerarşik yuvarlak maddelerle çizer."""
    formatted_bullets = format_as_nested_bullets(strategist_text)
    
    with st.container(border=True):
        if formatted_bullets:
            st.markdown(formatted_bullets, unsafe_allow_html=True)
        else:
            st.markdown(strategist_text)




def render_analyst_report(bot_dict: dict):
    """
    Bir analist botunun raporunu çizer:
    1. Üst Başlık & Sağ Rozet Kartı (Tek Kelime Karar)
    2. Detaylı İnceleme (Ayrı kutucuklama yapmadan TEK bir kartta; ● ana madde, ○ alt madde düzeninde)
    3. Karar metin içinde asla ikinci kez tekrar etmez.
    """
    name = bot_dict.get("name", "Analist")
    label = bot_dict.get("label", "")
    content = bot_dict.get("content", "Rapor içeriği bulunamadı.")
    
    # 1. Karar Rozeti
    verdict = extract_bot_verdict(content)
    color_type, bg, border, text_color = classify_verdict(verdict)

    # 2. Üst Başlık Kartı
    with st.container(border=True):
        col1, col2 = st.columns([3, 1.3])
        with col1:
            st.markdown(f"### {name}")
            st.caption(label)
        with col2:
            if verdict:
                badge_html = (
                    f'<div style="background:{bg}; border:2px solid {border}; color:{text_color}; '
                    f'padding:8px 16px; border-radius:10px; font-weight:800; text-align:center; '
                    f'font-size:13.5px; margin-top:8px; letter-spacing:0.4px; box-shadow:0 2px 8px {bg};">'
                    f'{verdict.upper()}</div>'
                )
                st.markdown(badge_html, unsafe_allow_html=True)

    # 3. Detaylı İnceleme (Ayrı kutucuklama yapmadan TEK kart içinde hiyerarşik maddeler)
    formatted_bullets = format_as_nested_bullets(content)
    with st.container(border=True):
        st.markdown(formatted_bullets, unsafe_allow_html=True)


def render_financial_metric_bar(ratios: dict, business: str):
    """6 Temel Rasyoyu modern koyu finansal kartlar olarak çizer."""
    if business:
        st.caption(f"**Faaliyet Alanı:** {business}")

    from data_fetcher import format_currency_amount

    items = [
        ("F/K Oranı", ratios.get("F/K", "-")),
        ("PD/DD Oranı", ratios.get("PD/DD", "-")),
        ("FD/FAVÖK", ratios.get("FD/FAVÖK", "-")),
        ("Net Borç", format_currency_amount(ratios.get("Net Borç", "-"))),
        ("Halka Açıklık", ratios.get("Halka Açıklık Oranı (%)", "-")),
        ("Yabancı Payı", ratios.get("Yabancı Oranı (%)", "-"))
    ]

    cols = st.columns(6)
    for col, (label, val) in zip(cols, items):
        val_str = str(val)
        val_font_size = "20px"

        card_html = (
            f'<div style="'
            f'background: #10172a; '
            f'border: 1px solid rgba(148, 163, 184, 0.18); '
            f'border-radius: 12px; '
            f'padding: 14px 6px; '
            f'text-align: center; '
            f'display: flex; '
            f'flex-direction: column; '
            f'align-items: center; '
            f'justify-content: center; '
            f'min-height: 82px; '
            f'box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);'
            f'">'
            f'<div style="'
            f'font-size: 12px; '
            f'font-weight: 600; '
            f'color: #94a3b8; '
            f'letter-spacing: 0.3px; '
            f'margin-bottom: 6px; '
            f'text-align: center; '
            f'width: 100%; '
            f'white-space: nowrap;'
            f'">{label}</div>'
            f'<div style="'
            f'font-size: {val_font_size}; '
            f'font-weight: 800; '
            f'color: #f8fafc; '
            f'line-height: 1.2; '
            f'letter-spacing: -0.2px; '
            f'text-align: center; '
            f'width: 100%; '
            f'white-space: nowrap;'
            f'">{val_str}</div>'
            f'</div>'
        )
        with col:
            st.markdown(card_html, unsafe_allow_html=True)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)




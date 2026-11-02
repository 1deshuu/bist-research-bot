# -*- coding: utf-8 -*-
"""
Borsa İstanbul Çok Ajanlı Hisse Senedi Araştırma Sistemi
Streamlit Tabanlı Yerel Web Portali
"""

import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
import json
import os
import importlib
import data_fetcher
import agent_engine
import bots_config
import ui_components

importlib.reload(data_fetcher)
importlib.reload(bots_config)
importlib.reload(agent_engine)
importlib.reload(ui_components)

from data_fetcher import prepare_analysis_context, clean_ticker
from agent_engine import run_full_research
from bots_config import BOTS
from ui_components import (
    render_executive_hero,
    render_portfolio_strategist_sections,
    render_analyst_report,
    render_financial_metric_bar
)

# Sayfa Yapilandirmasi
st.set_page_config(
    page_title="Borsa İstanbul Çok Ajanlı Hisse Senedi Araştırma Sistemi",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Anahtarı: st.secrets veya ortam değişkeninden güvenle okunur
try:
    DEFAULT_API_KEY = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))
except Exception:
    DEFAULT_API_KEY = os.getenv("GEMINI_API_KEY", "")

# BIST Hisse Listesini Yukle (632 Hisse ve Sirket Unvanlari)
@st.cache_data
def load_bist_stocks():
    json_path = os.path.join(os.path.dirname(__file__), "bist_stocks.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "THYAO": "Türk Hava Yolları", "ASELS": "Aselsan", "FROTO": "Ford Otosan",
        "BIMAS": "Bim Mağazalar", "TUPRS": "Tüpraş",
        "ASTOR": "Astor Enerji", "SISE": "Şişecam", "EREGL": "Ereğli Demir Çelik",
        "GARAN": "Garanti Bankası", "AKBNK": "Akbank", "ISCTR": "İş Bankası",
        "DOAS": "Doğuş Otomotiv", "DOHOL": "Doğan Holding"
    }

BIST_STOCKS = load_bist_stocks()

# Favoriler Dosyasi ve Kalici Depolama Fonksiyonlari
FAVORITES_FILE = os.path.join(os.path.dirname(__file__), "favorites.json")

def load_favorites():
    if os.path.exists(FAVORITES_FILE):
        try:
            with open(FAVORITES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return [str(x).upper().strip() for x in data if x]
        except Exception:
            pass
    return []

def save_favorites(fav_list):
    try:
        with open(FAVORITES_FILE, "w", encoding="utf-8") as f:
            json.dump(fav_list, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# 632 BIST Hissesini Alfabetik Olarak Hazırla
stock_options = [f"{code} — {name}" for code, name in sorted(BIST_STOCKS.items())]

# Ozel CSS Temasi (Koyu Kurumsal Finans Tasarimi)
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #0b132b 0%, #1c2541 60%, #3a506b 100%);
        padding: 26px 30px;
        border-radius: 12px;
        color: #ffffff;
        margin-bottom: 25px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.25);
        border: 1px solid rgba(255, 255, 255, 0.08);
    }
    .main-header h1 {
        margin: 0;
        font-size: 26px;
        font-weight: 700;
        letter-spacing: -0.3px;
        color: #f8f9fa;
    }
    .main-header p {
        margin: 8px 0 0 0;
        font-size: 14px;
        line-height: 1.6;
        color: #cbd5e1;
    }
    /* Sidebar Alanı: Ferah, Dengeli ve Kurumsal Tipografi */
    section[data-testid="stSidebar"] .stSidebarContent {
        padding-top: 1.8rem !important;
        padding-bottom: 2rem !important;
        padding-left: 1.25rem !important;
        padding-right: 1.25rem !important;
    }
    
    /* Bölüm Başlıkları */
    .sidebar-section-title {
        font-size: 15px;
        font-weight: 700;
        color: #f8fafc;
        margin-bottom: 10px;
        letter-spacing: -0.2px;
    }
    
    /* Doğal ve Şık Bölücü */
    .sidebar-divider {
        height: 1px;
        background: rgba(255, 255, 255, 0.08);
        margin: 22px 0 20px 0;
    }
    
    /* Analiz Ekibi: Doğal, Okunaklı ve Rahat Aralıklar */
    .team-container {
        display: flex;
        flex-direction: column;
        gap: 15px;
        margin-top: 6px;
    }
    .team-card {
        display: flex;
        flex-direction: column;
    }
    .team-title {
        font-size: 14px;
        font-weight: 700;
        color: #ffffff;
        letter-spacing: -0.2px;
        margin-bottom: 3px;
    }
    .team-desc {
        font-size: 12.5px;
        line-height: 1.45;
        color: #94a3b8;
    }
    .settings-spacer {
        margin-top: 32px;
    }
    /* Analizi Başlat Butonu (Hafif Koyu Yeşil) */
    div.stButton > button[kind="primary"] {
        background-color: #166534 !important;
        border-color: #14532d !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        font-size: 15px !important;
        letter-spacing: 0.2px !important;
        transition: all 0.2s ease-in-out !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #14532d !important;
        border-color: #052e16 !important;
        box-shadow: 0 4px 12px rgba(22, 101, 52, 0.35) !important;
    }
    div.stButton > button[kind="primary"]:active {
        background-color: #052e16 !important;
        border-color: #022c22 !important;
    }
    /* Focus Ring Renklerini Ana Temaya Uygun Mavi/Cyan Yap (Kırmızı Çerçeveyi Kaldır) */
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div {
        border-color: #334155 !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
    }
    div[data-baseweb="select"] > div:focus-within,
    div[data-baseweb="select"]:focus-within,
    div[data-baseweb="input"] > div:focus-within,
    div[data-baseweb="input"]:focus-within,
    input:focus {
        border-color: #0284c7 !important;
        box-shadow: 0 0 0 1px #0284c7, 0 0 10px rgba(2, 132, 199, 0.4) !important;
    }
    /* Açılır Liste (Dropdown) Menü Tasarımı */
    div[data-baseweb="popover"],
    ul[role="listbox"] {
        background-color: #1e293b !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
    }
    li[role="option"] {
        color: #e2e8f0 !important;
    }
    li[role="option"]:hover,
    li[aria-selected="true"] {
        background-color: #334155 !important;
        color: #38bdf8 !important;
    }
    /* Modern Sekmeler (Tab Bar) */
    div[data-baseweb="tab-list"] {
        gap: 6px !important;
        background: #0f172a !important;
        padding: 5px !important;
        border-radius: 10px !important;
        border: 1px solid rgba(148, 163, 184, 0.12) !important;
        margin-bottom: 20px !important;
        overflow-x: auto !important;
    }
    button[data-baseweb="tab"] {
        border-radius: 7px !important;
        font-size: 13px !important;
        font-weight: 600 !important;
        color: #94a3b8 !important;
        padding: 8px 14px !important;
        background: transparent !important;
        border: none !important;
        transition: all 0.2s ease !important;
        white-space: nowrap !important;
    }
    button[data-baseweb="tab"]:hover {
        color: #f8fafc !important;
        background: rgba(255, 255, 255, 0.04) !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #ffffff !important;
        background: #0284c7 !important;
        box-shadow: 0 4px 12px rgba(2, 132, 199, 0.35) !important;
    }
    div[data-baseweb="tab-border"],
    div[data-baseweb="tab-highlight"] {
        display: none !important;
    }

    /* Rapor Metinleri: Ferah, Kontrastlı ve Okunaklı */
    .report-content-body {
        font-size: 14.5px !important;
        line-height: 1.72 !important;
        color: #cbd5e1 !important;
    }
    .report-content-body p {
        margin-bottom: 12px !important;
    }
    .report-content-body strong,
    .report-content-body b {
        color: #f8fafc !important;
        font-weight: 700 !important;
    }
    .report-content-body ul,
    .report-content-body ol {
        margin: 8px 0 16px 20px !important;
        padding-left: 0 !important;
    }
    .report-content-body li {
        margin-bottom: 8px !important;
        line-height: 1.65 !important;
    }

    /* Modern Expander & Kart Çerçeveleri */
    div[data-testid="stExpander"] {
        background: #10172a !important;
        border: 1px solid rgba(148, 163, 184, 0.15) !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2) !important;
    }
    div[data-testid="stExpander"] summary {
        font-weight: 700 !important;
        font-size: 15px !important;
        color: #e2e8f0 !important;
        padding: 14px 18px !important;
    }

    /* Modern Kart Çerçeveleri (st.container border=True) */
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        background: #111b2f !important;
        border: 1px solid rgba(148, 163, 184, 0.15) !important;
        border-radius: 12px !important;
        padding: 16px 20px !important;
        margin-bottom: 8px !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] > div:hover {
        border-color: rgba(56, 189, 248, 0.25) !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] .stMarkdown p,
    div[data-testid="stVerticalBlockBorderWrapper"] .stMarkdown li {
        font-size: 14.5px !important;
        line-height: 1.68 !important;
        color: #cbd5e1 !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] .stMarkdown h4 {
        color: #38bdf8 !important;
        font-weight: 700 !important;
        margin-top: 10px !important;
        margin-bottom: 8px !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] .stMarkdown strong {
        color: #f1f5f9 !important;
    }

    /* Favori Butonu: Normal (Gold) ve Hover Vurgusu */
    button:has([title*="Favori"]):not(:has([title*="Ekle"])) {
        border-color: rgba(245, 158, 11, 0.45) !important;
        background-color: rgba(245, 158, 11, 0.08) !important;
        color: #fbbf24 !important;
        transition: all 0.15s ease-in-out !important;
    }
    button:has([title*="Favori"]):not(:has([title*="Ekle"])):hover {
        border-color: #ef4444 !important;
        background-color: rgba(239, 68, 68, 0.16) !important;
        color: #f87171 !important;
        box-shadow: 0 0 12px rgba(239, 68, 68, 0.25) !important;
    }

    /* Sidebar Buton Tasarımı (Portföy Stratejisti Sekmesi) */
    div[data-testid="stSidebar"] div.stButton > button {
        background-color: #111b2f !important;
        border: 1px solid rgba(56, 189, 248, 0.28) !important;
        color: #f1f5f9 !important;
        font-weight: 600 !important;
        font-size: 13.5px !important;
        padding: 11px 16px !important;
        border-radius: 9px !important;
        text-align: center !important;
        transition: all 0.2s ease-in-out !important;
    }
    div[data-testid="stSidebar"] div.stButton > button:hover {
        border-color: #38bdf8 !important;
        background-color: rgba(56, 189, 248, 0.12) !important;
        color: #38bdf8 !important;
        box-shadow: 0 4px 14px rgba(56, 189, 248, 0.22) !important;
    }

    /* Dialog Ortalaması, Boyutlandırma ve Rahat Düzen */
    div[data-testid="stDialog"] {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    div[data-testid="stDialog"] > div[role="dialog"] {
        max-width: 920px !important;
        width: 90vw !important;
        margin: auto !important;
        border-radius: 12px !important;
        padding: 20px 24px 22px 24px !important;
        border: 1px solid rgba(56, 189, 248, 0.28) !important;
        background: #0b1120 !important;
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.85) !important;
    }
    div[data-testid="stDialog"] [data-testid="stDialogHeader"] {
        padding: 0 0 10px 0 !important;
        margin-bottom: 8px !important;
        border-bottom: 1px solid rgba(148, 163, 184, 0.14) !important;
    }
    div[data-testid="stDialog"] [data-testid="stDialogHeader"] h2 {
        font-size: 16px !important;
        font-weight: 700 !important;
        color: #f8fafc !important;
        margin: 0 !important;
    }
</style>
""", unsafe_allow_html=True)

# Oturum Durumu (Session State)
if "favorites" not in st.session_state:
    st.session_state.favorites = load_favorites()
if "current_ticker" not in st.session_state:
    st.session_state.current_ticker = ""
if "last_results" not in st.session_state:
    st.session_state.last_results = None
if "last_context" not in st.session_state:
    st.session_state.last_context = None
if "analysis_cache" not in st.session_state:
    st.session_state.analysis_cache = {}

# Portföy Stratejisti Karar Mekanizması Modal Penceresi
@st.dialog("Portföy Stratejisti Karar Mekanizması", width="large")
def show_strategist_explanation_dialog():
    st.html("""
<div style="background: linear-gradient(135deg, #0b132b 0%, #1c2541 100%); border: 1px solid rgba(56, 189, 248, 0.22); border-radius: 9px; padding: 12px 18px; margin-bottom: 12px;">
    <div style="font-size: 13.5px; font-weight: 700; color: #38bdf8; margin-bottom: 5px;">Kurumsal Yatırım Mutabakatı ve Karar Mimarisi</div>
    <p style="margin: 0; font-size: 12px; line-height: 1.55; color: #cbd5e1;">
        Portföy Stratejisti tek bir indikatöre dayanmaz. Sistemdeki <strong>6 bağımsız analist botunun</strong> (Patron & Yönetim, Değerleme, Finansal, Katalizörler, Takas, Risk) çıkar çatışmasız raporlarını çapraz denetimden geçirerek <strong>rasyonel ve sermaye koruma öncelikli</strong> nihai karar üretir.
    </p>
</div>

<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; align-items: stretch; margin-bottom: 12px;">
    <div style="background: #111b2f; border: 1px solid rgba(148, 163, 184, 0.15); border-radius: 9px; padding: 13px 16px; display: flex; flex-direction: column; justify-content: flex-start; height: 100%; box-sizing: border-box;">
        <div style="font-size: 13px; font-weight: 700; color: #38bdf8; margin-bottom: 8px; padding-bottom: 6px; border-bottom: 1px solid rgba(148, 163, 184, 0.12);">
            1. Doğrulanmış Veri Paketi
        </div>
        <div style="display: flex; flex-direction: column; gap: 7px; font-size: 12px; line-height: 1.5; color: #cbd5e1; flex: 1 1 auto;">
            <div><strong>Resmi KAP Bildirimleri:</strong> Son 15 şirket açıklaması, yeni iş ilişkileri, genel kurul ve pay işlemleri denetlenir.</div>
            <div><strong>İş Yatırım Finansalları:</strong> F/K, PD/DD, FD/FAVÖK, Net Borç/FAVÖK çarpanları ve sermaye kârlılığı incelenir.</div>
            <div><strong>Piyasa ve Takas Verileri:</strong> Fiyat hareketleri, likidite, hacim dağılımı ve sektör çarpan seviyeleri teyit edilir.</div>
        </div>
    </div>
    <div style="background: #111b2f; border: 1px solid rgba(239, 68, 68, 0.25); border-radius: 9px; padding: 13px 16px; display: flex; flex-direction: column; justify-content: flex-start; height: 100%; box-sizing: border-box;">
        <div style="font-size: 13px; font-weight: 700; color: #f87171; margin-bottom: 8px; padding-bottom: 6px; border-bottom: 1px solid rgba(239, 68, 68, 0.15);">
            2. Sermaye Koruma ve Veto Kuralı
        </div>
        <div style="display: flex; flex-direction: column; gap: 7px; font-size: 12px; line-height: 1.5; color: #cbd5e1; flex: 1 1 auto;">
            <div><strong>Patron Riski Veto Eder:</strong> Patron analisti (<strong>RİSKLİ</strong>) kararı verdiyse hisse ne kadar ucuz olursa olsun kesinlikle AL kararı verilemez.</div>
            <div><strong>Taşıyıcı Kolon Çöküşü:</strong> Risk Analisti (<strong>YÜKSEK</strong>) risk tespit ederse ana büyüme tezi doğrudan geçersiz sayılır.</div>
            <div><strong>Aşırı Borçluluk:</strong> Net Borç / FAVÖK sürdürülemez seviyedeyse yeni sermaye tahsisi derhal durdurulur.</div>
        </div>
    </div>
</div>

<div style="font-size: 13.5px; font-weight: 700; color: #f8fafc; margin-bottom: 9px;">Nihai Karar Matrisi (AL / İZLE / ALMA)</div>

<div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; align-items: stretch; margin-bottom: 12px;">
    <div style="background: rgba(34, 197, 94, 0.08); border: 1px solid rgba(34, 197, 94, 0.35); border-radius: 9px; padding: 13px 14px; display: flex; flex-direction: column; justify-content: space-between; height: 100%; box-sizing: border-box;">
        <div>
            <div style="font-size: 13px; font-weight: 700; color: #4ade80; margin-bottom: 8px; padding-bottom: 5px; border-bottom: 1px solid rgba(34, 197, 94, 0.2);">AL KARARI</div>
            <div style="font-size: 12px; color: #e2e8f0; line-height: 1.55;">
                <strong>Gerekli Şartlar:</strong><br>
                • Değerleme: (<strong>UCUZ / MAKUL</strong>)<br>
                • Finansal Yapı: (<strong>GÜÇLÜ</strong>)<br>
                • Büyüme Katalizörü: (<strong>GÜÇLÜ / İSTİKRARLI</strong>)<br>
                • Yönetim Kalitesi: (<strong>GÜVENİLİR</strong>)<br>
                • Risk Seviyesi: (<strong>DÜŞÜK / ORTA</strong>)
            </div>
        </div>
        <div style="font-size: 11.5px; color: #cbd5e1; line-height: 1.45; margin-top: 10px; padding-top: 8px; border-top: 1px solid rgba(34, 197, 94, 0.2);">
            <strong style="color: #4ade80;">Strateji:</strong> Portföyde %3 - %8 ağırlık. Riskleri dağıtmak için 3 Kademeli Alım Seviyesi oluşturulur.
        </div>
    </div>
    <div style="background: rgba(234, 179, 8, 0.08); border: 1px solid rgba(234, 179, 8, 0.35); border-radius: 9px; padding: 13px 14px; display: flex; flex-direction: column; justify-content: space-between; height: 100%; box-sizing: border-box;">
        <div>
            <div style="font-size: 13px; font-weight: 700; color: #facc15; margin-bottom: 8px; padding-bottom: 5px; border-bottom: 1px solid rgba(234, 179, 8, 0.2);">İZLE KARARI</div>
            <div style="font-size: 12px; color: #e2e8f0; line-height: 1.55;">
                <strong>Gerekli Şartlar:</strong><br>
                • Değerleme: Primli çarpanlar (<strong>PAHALI</strong>)<br>
                • Finansal Yapı: Dengeli bilanço (<strong>DENGELİ</strong>)<br>
                • Büyüme Katalizörü: Yatırım süreci (<strong>BEKLEMEDE</strong>)<br>
                • Takas Dinamiği: Fon ilgisi (<strong>İZLEMEDE</strong>)<br>
                • Risk Seviyesi: Döngüsel riskler (<strong>ORTA</strong>)
            </div>
        </div>
        <div style="font-size: 11.5px; color: #cbd5e1; line-height: 1.45; margin-top: 10px; padding-top: 8px; border-top: 1px solid rgba(234, 179, 8, 0.2);">
            <strong style="color: #facc15;">Strateji:</strong> Portföy ağırlığı %0. Belirlenen hedef fiyat veya bilanço kilometre taşları takip edilir.
        </div>
    </div>
    <div style="background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.35); border-radius: 9px; padding: 13px 14px; display: flex; flex-direction: column; justify-content: space-between; height: 100%; box-sizing: border-box;">
        <div>
            <div style="font-size: 13px; font-weight: 700; color: #f87171; margin-bottom: 8px; padding-bottom: 5px; border-bottom: 1px solid rgba(239, 68, 68, 0.2);">ALMA KARARI</div>
            <div style="font-size: 12px; color: #e2e8f0; line-height: 1.55;">
                <strong>Gerekli Şartlar:</strong><br>
                • Değerleme: Değer tuzağı riski (<strong>RİSKLİ</strong>)<br>
                • Finansal Yapı: Ağır borç veya nakit açığı (<strong>RİSKLİ</strong>)<br>
                • Büyüme Katalizörü: Somut katalizör yok (<strong>KATALİZÖRSÜZ</strong>)<br>
                • Yönetim Kalitesi: Şeffaflık zayıf (<strong>RİSKLİ</strong>)<br>
                • Risk Seviyesi: Taşıyıcı kolon kırılgan (<strong>YÜKSEK</strong>)
            </div>
        </div>
        <div style="font-size: 11.5px; color: #cbd5e1; line-height: 1.45; margin-top: 10px; padding-top: 8px; border-top: 1px solid rgba(239, 68, 68, 0.2);">
            <strong style="color: #f87171;">Strateji:</strong> Portföy ağırlığı %0. Kesinlikle yeni sermaye tahsis edilmez; mevcut pozisyonlar derhal kapatılır.
        </div>
    </div>
</div>

<div style="background: #111b2f; border: 1px solid rgba(148, 163, 184, 0.15); border-radius: 9px; padding: 11px 18px;">
    <div style="font-size: 12.5px; font-weight: 700; color: #38bdf8; margin-bottom: 4px;">Kademeli Giriş ve Disiplinli Çıkış (Stop-Loss) Kuralı</div>
    <p style="font-size: 12px; line-height: 1.5; color: #cbd5e1; margin: 0;">
        Portföy Stratejisti tek bir seviyeden tüm sermayeyle alım önermez. Karar AL olduğunda sermaye; mevcut fiyat seviyesi (%40), bilanço teyidi (%30) ve teknik destek (%30) şeklinde 3 kademeye bölünür. Hangi somut finansal bozulmada pozisyonun kapatılacağı önceden kurallara bağlanır.
    </p>
</div>
""")

# ==================== YAN MENÜ (SIDEBAR) ====================
with st.sidebar:
    # 1. FAVORİLER (HIZLI ERİŞİM)
    st.markdown('<div class="sidebar-section-title">⭐ Favoriler</div>', unsafe_allow_html=True)

    if st.session_state.favorites:
        fav_display_options = ["(Favorilerden Seçiniz)"] + [
            f"{code} — {BIST_STOCKS.get(code, '')}" for code in st.session_state.favorites
        ]
        
        # Eğer mevcut hisse favorilerdeyse varsayılan index'i bul
        fav_default_idx = 0
        if st.session_state.current_ticker in st.session_state.favorites:
            try:
                fav_default_idx = st.session_state.favorites.index(st.session_state.current_ticker) + 1
            except ValueError:
                fav_default_idx = 0

        selected_fav = st.selectbox(
            "Favori Hisseler:",
            options=fav_display_options,
            index=fav_default_idx,
            label_visibility="collapsed",
            help="Favori hisseleriniz arasından hızlıca seçim yapın."
        )
        
        if selected_fav != "(Favorilerden Seçiniz)":
            chosen_code = selected_fav.split(" — ")[0].strip()
            if chosen_code != st.session_state.current_ticker:
                st.session_state.current_ticker = chosen_code
                st.rerun()
    else:
        st.markdown("""
        <div style="background: rgba(30, 41, 59, 0.4); border: 1px dashed rgba(148, 163, 184, 0.25); border-radius: 8px; padding: 10px 12px; font-size: 12.5px; color: #94a3b8; line-height: 1.45; margin-bottom: 8px;">
            Henüz favori hisseniz yok.<br>Ana ekrandaki arama alanından hisse seçip <strong>☆ Favoriye Ekle</strong> butonuna basabilirsiniz.
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

    # 2. ANALİZ EKİBİ (GÖRSELE BİREBİR UYUMLU, RAHAT VE OKUNAKLI)
    st.markdown('<div class="sidebar-section-title">Analiz Ekibi</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="team-container">
        <div class="team-card">
            <div class="team-title">01 · Patron & Yönetim Analisti</div>
            <div class="team-desc">Yönetim kalitesini, şirket yapısını, imtiyazları ve kurumsal şeffaflığı denetler.</div>
        </div>
        <div class="team-card">
            <div class="team-title">02 · Değerleme Analisti</div>
            <div class="team-desc">Kâr marjlarını koruyabilecek fiyatlama gücünü, ölçek avantajını ve piyasa çarpanlarını tespit eder.</div>
        </div>
        <div class="team-card">
            <div class="team-title">03 · Finansal Analist</div>
            <div class="team-desc">Bilanço yapısını, gelir tablosunu, borç çevrimini ve nakit akış kalitesini değerlendirir.</div>
        </div>
        <div class="team-card">
            <div class="team-title">04 · Katalizörler & Kapasite Analisti</div>
            <div class="team-desc">Üretim kapasitesini, devam eden yatırımları ve gelecekteki büyüme katalizörlerini inceler.</div>
        </div>
        <div class="team-card">
            <div class="team-title">05 · Takas & Piyasa Analisti</div>
            <div class="team-desc">Takas konsantrasyonunu, fon pozisyonlarını, yatırımcı psikolojisini ve piyasa dinamiklerini analiz eder.</div>
        </div>
        <div class="team-card">
            <div class="team-title">06 · Risk Analisti</div>
            <div class="team-desc">Şüpheci bir fon yöneticisi gibi davranarak boğaların görmezden geldiği tüm kör noktaları ve riskleri ortaya çıkarır.</div>
        </div>
        <div class="team-card">
            <div class="team-title">07 · Portföy Stratejisti</div>
            <div class="team-desc">Tüm analistlerin bulgularını sentezleyerek kurumsal yatırım mutabakatını ve nihai stratejiyi oluşturur.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 3. PORTFÖY STRATEJİSTİ KARAR METODOLOJİSİ (DİREKT TIKLANABİLİR SEKME BUTONU)
    st.markdown('<div class="sidebar-divider" style="margin-top: 24px; margin-bottom: 20px;"></div>', unsafe_allow_html=True)
    if st.button("Portföy Stratejisti kararlarını nasıl veriyor?", use_container_width=True, key="btn_open_strat_dlg"):
        show_strategist_explanation_dialog()

    # 4. GELİŞMİŞ AYARLAR (AYIRICI ÇİZGİ EKLENDİ VE DAHA AŞAĞIYA KONUMLANDIRILDI)
    st.markdown('<div class="sidebar-divider" style="margin-top: 24px; margin-bottom: 22px;"></div>', unsafe_allow_html=True)
    with st.expander("Gelişmiş Ayarlar", expanded=False):
        api_key_input = st.text_input(
            "Gemini API Key:",
            value=DEFAULT_API_KEY,
            type="password",
            help="Sistem tanımlı anahtarı kullanır. İsterseniz değiştirebilirsiniz."
        )
    api_key = api_key_input if 'api_key_input' in locals() and api_key_input else DEFAULT_API_KEY

# ==================== ANA EKRAN ====================

# Ana Başlık ve Açıklama
st.markdown("""
<div class="main-header">
    <h1>Borsa İstanbul Çok Ajanlı Hisse Senedi Araştırma Sistemi</h1>
    <p>
        Resmi KAP bildirimleri ve doğrulanmış finansal tabloları analiz eden 
        6 bağımsız analist botu; değerleme, likidite, borçluluk ve karlılık dinamiklerini ayrı ayrı denetler.
        Tüm bu çıktılar, Portföy Analisti tarafından hesaplanarak, hisse seçiminden
        rasyonel sermaye dağılımına kadar her adımda veriye dayalı, derinlemesine karar desteği sağlar.
    </p>
</div>
""", unsafe_allow_html=True)

# Eğer Favorilerden veya Önceden Belirlenmiş Hisse Varsa İndeksini Bul
default_stock_idx = None
if st.session_state.current_ticker:
    for idx, opt in enumerate(stock_options):
        if opt.startswith(st.session_state.current_ticker + " —") or opt == st.session_state.current_ticker:
            default_stock_idx = idx
            break

# Hisse Arama, Favori Ekle/Çıkar Butonu ve Analiz Başlat Butonu
col_search, col_fav_star, col_btn = st.columns([3.0, 1.15, 1.15], vertical_alignment="bottom")

with col_search:
    selected_stock = st.selectbox(
        "Analiz Edilecek Hisse Kodu veya Şirket Adı:",
        options=stock_options,
        index=default_stock_idx,
        placeholder="Hisse kodu yazın... (Örn: GARAN, FROTO, THYAO)",
        filter_mode="prefix",
        help="Hisse kodunu yazmaya başladığınızda harf sırasına göre sadece onunla başlayan hisseler filtrelenir."
    )

# Seçilen hisseden kodu ayıkla
user_query = selected_stock.split(" — ")[0].strip() if selected_stock else ""
if user_query and user_query != st.session_state.current_ticker:
    st.session_state.current_ticker = user_query

with col_fav_star:
    if user_query:
        is_favorite = user_query in st.session_state.favorites
        if is_favorite:
            if st.button("⭐ Favori", use_container_width=True, key=f"btn_fav_active_{user_query}"):
                st.session_state.favorites.remove(user_query)
                save_favorites(st.session_state.favorites)
                st.rerun()
        else:
            if st.button("☆ Favoriye Ekle", use_container_width=True, key=f"btn_fav_add_{user_query}"):
                st.session_state.favorites.append(user_query)
                save_favorites(st.session_state.favorites)
                st.rerun()
    else:
        st.button("☆ Favoriye Ekle", disabled=True, use_container_width=True, key="main_fav_toggle_disabled")

with col_btn:
    start_btn = st.button("Analizi Başlat", type="primary", use_container_width=True)

# Favori Butonu: Fare üzerine gelince 'Favorilerden Çıkar' yazısına dinamik geçiş
components.html("""
<script>
(function() {
    const parentDoc = window.parent.document;
    function setupFavHover() {
        const buttons = parentDoc.querySelectorAll('button');
        buttons.forEach(btn => {
            const p = btn.querySelector('p');
            if (!p) return;
            const txt = p.textContent.trim();

            // Eğer buton "Favoriye Ekle" ise veya favori değilse, favori stillerini sıfırla
            if (txt.includes('Ekle') || (!txt.includes('Favori') && txt !== 'Favorilerden Çıkar')) {
                btn.dataset.isFavActive = 'false';
                if (btn.dataset.favStyled === 'true') {
                    btn.style.borderColor = '';
                    btn.style.backgroundColor = '';
                    btn.style.color = '';
                    btn.dataset.favStyled = 'false';
                }
                return;
            }

            // Yalnızca aktif favori butonu için ("⭐ Favori" veya "Favorilerden Çıkar")
            if (txt === '⭐ Favori' || txt === 'Favorilerden Çıkar') {
                btn.dataset.isFavActive = 'true';
                if (!btn.matches(':hover') && txt === '⭐ Favori') {
                    btn.style.borderColor = 'rgba(245, 158, 11, 0.45)';
                    btn.style.backgroundColor = 'rgba(245, 158, 11, 0.08)';
                    btn.style.color = '#fbbf24';
                    btn.dataset.favStyled = 'true';
                }
                if (!btn.dataset.hoverBound) {
                    btn.dataset.hoverBound = 'true';
                    btn.style.transition = 'all 0.15s ease-in-out';
                    btn.addEventListener('mouseenter', function() {
                        if (btn.dataset.isFavActive === 'true') {
                            const curP = btn.querySelector('p');
                            if (curP) curP.textContent = 'Favorilerden Çıkar';
                            btn.style.borderColor = '#ef4444';
                            btn.style.backgroundColor = 'rgba(239, 68, 68, 0.16)';
                            btn.style.color = '#f87171';
                            btn.dataset.favStyled = 'true';
                        }
                    });
                    btn.addEventListener('mouseleave', function() {
                        if (btn.dataset.isFavActive === 'true') {
                            const curP = btn.querySelector('p');
                            if (curP) curP.textContent = '⭐ Favori';
                            btn.style.borderColor = 'rgba(245, 158, 11, 0.45)';
                            btn.style.backgroundColor = 'rgba(245, 158, 11, 0.08)';
                            btn.style.color = '#fbbf24';
                            btn.dataset.favStyled = 'true';
                        }
                    });
                }
            }
        });
    }
    setupFavHover();
    const obs = new MutationObserver(setupFavHover);
    obs.observe(parentDoc.body, { childList: true, subtree: true });
})();
</script>
""", height=0, width=0)

st.markdown("---")

# ==================== ANALİZ ÇALIŞTIRMA ====================
if start_btn:
    target_ticker = clean_ticker(user_query)
    if not target_ticker:
        st.markdown("""
        <div style="background-color: #7f1d1d; color: #fee2e2; border: 1px solid #991b1b; padding: 12px 18px; border-radius: 8px; font-size: 14px; font-weight: 500; margin-top: 8px; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
            <span> Lütfen geçerli bir hisse kodu girin.</span>
        </div>
        """, unsafe_allow_html=True)
    elif not api_key:
        st.error("⚠️ Lütfen sol menüdeki 'Gelişmiş Ayarlar' bölümünden geçerli bir Gemini API Anahtarı girin.")
    else:
        with st.status(f"{target_ticker} için canlı veriler toplanıyor ve analiz ekibi çalıştırılıyor...", expanded=True) as status:
            # 1. Adım: Canlı Veri Çekme
            status.update(label=f"{target_ticker} resmi finansalları, teknik verileri ve KAP bildirimleri taranıyor...", expanded=True)
            try:
                context_data = prepare_analysis_context(target_ticker)
                st.session_state.last_context = context_data
                st.write(f"**{context_data.get('title', target_ticker)}** finansalları, fiyat verileri ve KAP bildirimleri çekildi.")
            except Exception as e:
                st.error(f"Veri çekme hatası: {e}")
                status.update(label="Veri çekme sırasında hata oluştu.", state="error", expanded=True)
                st.stop()

            # 2. Adım: Ajanları Çalıştırma
            status.update(label="Analiz Ekibi ve Portföy Stratejisti araştırma yapıyor...", expanded=True)
            progress_bar = st.progress(0)
            status_text = st.empty()

            def progress_callback(index, name, message):
                progress_bar.progress(int((index / 7.0) * 100))
                status_text.text(f"[{index}/7] {message}")

            try:
                results = run_full_research(
                    context_data["context_text"],
                    api_key,
                    progress_callback=progress_callback
                )
                st.session_state.last_results = results
                st.session_state.current_ticker = target_ticker
                if "analysis_cache" not in st.session_state:
                    st.session_state.analysis_cache = {}
                st.session_state.analysis_cache[target_ticker] = {
                    "results": results,
                    "context": context_data,
                    "time": datetime.now().strftime("%H:%M")
                }
                status.update(label=f"{target_ticker} analizi başarıyla tamamlandı.", state="complete", expanded=False)
            except Exception as e:
                st.error(f"Analiz hatası: {e}")
                status.update(label="Analiz sırasında hata oluştu.", state="error", expanded=True)
                st.stop()

# ==================== SONUÇLARI GÖRÜNTÜLEME ====================
active_code = st.session_state.current_ticker or user_query
active_entry = st.session_state.analysis_cache.get(active_code)

if active_entry:
    results = active_entry["results"]
    context_data = active_entry["context"]
elif st.session_state.last_results and st.session_state.last_context:
    last_sym = st.session_state.last_context.get("symbol", "")
    if not active_code or active_code == last_sym:
        results = st.session_state.last_results
        context_data = st.session_state.last_context
    else:
        results = None
        context_data = None
else:
    results = None
    context_data = None

if results and context_data:
    card = context_data.get("card", {})
    ratios = card.get("ratios", {})
    symbol = context_data.get("symbol", active_code)
    title = context_data.get("title", symbol)
    if title == symbol:
        from data_fetcher import BIST_STOCKS_MAP
        title = BIST_STOCKS_MAP.get(symbol, symbol)

    # 1. Finansal Rasyolar Barı (Modern Bloomberg / TradingView Tarzı)
    st.markdown(f"## {title} ({symbol}) Finansal Göstergeleri")
    render_financial_metric_bar(ratios, card.get("business", ""))

    # 2. Portföy Stratejisti Nihai Karar Paneli (Hero Dashboard - Asla Yarım Kalmaz)
    strategist_res = results.get("bot7", {})
    strategist_content = strategist_res.get("content", "")
    render_executive_hero(strategist_content, symbol, title)

    # 3. Portföy Stratejisti Detaylı Kurumsal Rapor Kartları
    with st.expander("Portföy Stratejisti Analiz Notları ve Sentez Detayları", expanded=True):
        render_portfolio_strategist_sections(strategist_content)

    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
    st.markdown("### Analiz Ekibi Detaylı İncelemeleri")

    # Sekmeler (Tabs - Modern Pill Tasarımı)
    tab1, tab2, tab3, tab4, tab5, tab6, tab_raw = st.tabs([
        "Patron & Yönetim Analisti",
        "Değerleme Analisti",
        "Finansal Analist",
        "Katalizörler & Kapasite Analisti",
        "Takas & Piyasa Analisti",
        "Risk Analisti",
        "Doğrulanmış Canlı Veriler"
    ])

    with tab1:
        render_analyst_report(results.get("bot1", {}))

    with tab2:
        render_analyst_report(results.get("bot2", {}))

    with tab3:
        render_analyst_report(results.get("bot3", {}))

    with tab4:
        render_analyst_report(results.get("bot4", {}))

    with tab5:
        render_analyst_report(results.get("bot5", {}))

    with tab6:
        render_analyst_report(results.get("bot6", {}))

    with tab_raw:
        st.markdown("#### Botlara Beslenen Doğrulanmış Canlı Veri Paketi")
        st.text_area("İş Yatırım, Fiyat & KAP Bildirim Özeti:", value=context_data.get("context_text", ""), height=350)
        
        news_list = context_data.get("news", [])
        if news_list:
            st.markdown("##### Taranan Son KAP ve Piyasa Başlıkları:")
            for n in news_list:
                st.markdown(f"- **[{n.get('date')}]** [{n.get('title')}]({n.get('link')}) *({n.get('source')})*")

    # İndirme Butonu
    full_markdown_report = f"""# {context_data.get('title')} ({context_data.get('symbol')}) — BIST Çoklu Ajan Araştırma Raporu
Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}

---
## PORTFÖY STRATEJİSTİ (NİHAİ DEĞERLENDİRME)
{strategist_content}

---
## PATRON & YÖNETİM ANALİSTİ
{results.get('bot1', {}).get('content', '')}

---
## DEĞERLEME ANALİSTİ
{results.get('bot2', {}).get('content', '')}

---
## FİNANSAL ANALİST
{results.get('bot3', {}).get('content', '')}

---
## KATALİZÖRLER & KAPASİTE ANALİSTİ
{results.get('bot4', {}).get('content', '')}

---
## TAKAS & PİYASA ANALİSTİ
{results.get('bot5', {}).get('content', '')}

---
## RİSK ANALİSTİ
{results.get('bot6', {}).get('content', '')}

---
## DOĞRULANMIŞ CANLI VERİ VE KAP BİLGİLERİ
{context_data.get('context_text', '')}
"""
    st.download_button(
        label="Tüm Raporu Markdown (.md) Olarak İndir",
        data=full_markdown_report.encode('utf-8'),
        file_name=f"{context_data.get('symbol')}_BIST_Arastirma_Raporu_{datetime.now().strftime('%Y%m%d')}.md",
        mime="text/markdown",
        use_container_width=True
    )
elif active_code and not start_btn:
    comp_title = BIST_STOCKS.get(active_code, active_code)
    st.markdown(f"""
    <div style="background: #111b2f; border: 1px solid rgba(56, 189, 248, 0.22); border-radius: 12px; padding: 28px 24px; text-align: center; margin-top: 20px; margin-bottom: 24px;">
        <div style="font-size: 28px; margin-bottom: 8px;">📈</div>
        <div style="font-size: 18px; font-weight: 700; color: #f8fafc; margin-bottom: 6px;">{comp_title} ({active_code})</div>
        <div style="font-size: 14px; color: #94a3b8; max-width: 520px; margin: 0 auto 14px auto; line-height: 1.5;">
            Bu hisse için canlı KAP bildirimleri, finansal oranlar ve 7 bağımsız analiz botunun raporu bu oturumda henüz hazırlanmadı.
        </div>
        <div style="font-size: 13.5px; color: #38bdf8; font-weight: 500;">
            Analizi başlatmak için yukarıdaki <strong style="color: #4ade80;">"Analizi Başlat"</strong> butonuna tıklayabilirsiniz.
        </div>
    </div>
    """, unsafe_allow_html=True)


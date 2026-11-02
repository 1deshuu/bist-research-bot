# 📈 Borsa İstanbul Çok Ajanlı Hisse Senedi Araştırma Sistemi

Borsa İstanbul (BIST) pay senetlerini 6 uzman yapay zeka analisti ve 1 baş portföy stratejisti ile çok boyutlu olarak analiz eden, canlı finansal veriler, KAP bildirimleri ve piyasa çarpanlarıyla desteklenen profesyonel bir araştırma ve yatırım karar destek portalıdır.

---

## 🏛️ Analiz Ekibi ve Çalışma Mimarisi

Sistem, tek bir modelin yüzeysel yorumu yerine bağımsız uzman roller üstlenen **7 yapay zeka ajanından** oluşur:

1. **Patron & Yönetim Analisti:** Yönetim kurulu kalitesini, ortaklık yapısını, imtiyazlı payları, ilişkili taraf işlemlerini ve patronun küçük yatırımcıyla çıkar ortaklığını denetler.
2. **Değerleme Analisti:** Şirketin fiyatlama gücünü, F/K, PD/DD, FD/FAVÖK çarpanlarını sektörel ve tarihsel medyanlara göre değerlendirir.
3. **Finansal Sağlık & Borçluluk Analisti:** Net borç, işletme sermayesi, faiz karşılama gücü ve nakit akış kalitesini inceler.
4. **Kapasite & Katalizör Analisti:** Üretim kapasitesi artışlarını, yatırım teşviklerini, yeni iş anlaşmalarını ve şirketi büyütecek katalizör takvimini araştırır.
5. **Takas & Piyasa Analisti:** Kurumsal fon pozisyonlanmasını, takas konsantrasyonunu, mal dağıtım/toplama emarelerini ve tahta likiditesini analiz eder.
6. **Risk Analisti:** Boğa tezlerinin görmezden geldiği en büyük kör noktaları, kırılgan taşıyıcı kolon varsayımlarını ve olası şok senaryolarını ortaya koyar.
7. **Portföy Stratejisti (Nihai Karar Mercii):** 6 analistin tüm raporlarını sentezler; sermaye koruma ve veto kurallarını işleterek kesin bir **[AL]**, **[İZLE]** veya **[ALMA]** kararı verir. Portföy ağırlığı, kademeli alım seviyeleri ve çıkış koşullarını belirler.

---

## 🚀 Öne Çıkan Özellikler

- **Canlı Veri Entegrasyonu:** İş Yatırım şirket kartları ve Yahoo Finance üzerinden gerçek zamanlı rasyolar (F/K, PD/DD, FD/FAVÖK, Net Borç, Halka Açıklık, Yabancı Payı).
- **Hızlı Erişim & Favoriler:** Sık takip edilen BIST hisselerini tek tıkla favorilere ekleme/çıkarma ve saklama (`favorites.json`).
- **Gelişmiş Arayüz (Streamlit):** Koyu tema, akıcı hiyerarşik kartlar, dinamik hover efektleri ve karar rozetleri.
- **Güvenli API Yönetimi:** Streamlit `secrets.toml` ve ortam değişkeni desteği.

---

## 🛠️ Kurulum

### 1. Depoyu Klonlayın
```bash
git clone https://github.com/KULLANICI_ADINIZ/bist-research-bot.git
cd bist-research-bot
```

### 2. Bağımlılıkları Yükleyin
```bash
pip install -r requirements.txt
```

### 3. Gemini API Anahtarını Tanımlayın
`.streamlit/secrets.toml.example` dosyasını `.streamlit/secrets.toml` olarak kopyalayın ve Google AI Studio'dan aldığınız API anahtarınızı yazın:

```toml
# .streamlit/secrets.toml
GEMINI_API_KEY = "AIzaSy..."
```
*(Alternatif olarak sol menüdeki **Gelişmiş Ayarlar** sekmesinden arayüz üzerinden de girebilirsiniz.)*

---

## 💻 Çalıştırma

### Yöntem 1: Doğrudan Streamlit ile
```bash
streamlit run app.py
```

### Yöntem 2: Windows için Tek Tıkla
Windows kullanıyorsanız dizindeki `baslat.bat` dosyasına çift tıklayarak sistemi başlatabilirsiniz. Tarayıcınız otomatik olarak `http://localhost:8501` adresinde açılacaktır.

---

## 📁 Proje Dosya Yapısı

```
bist_research_bot/
├── app.py                     # Streamlit ana arayüzü ve akış yönetimi
├── agent_engine.py            # Gemini API çoklu model yedekli ajan motoru
├── bots_config.py             # 7 Analist botunun sistem talimatları ve çıktı kontratları
├── data_fetcher.py            # İş Yatırım, KAP ve piyasa veri çekici
├── ui_components.py           # Kartlar, hiyerarşik maddeler ve gösterge bileşenleri
├── bist_stocks.json           # Güncel BIST 630+ hisse kodu ve unvan veritabanı
├── favorites.json             # Kullanıcının favori hisse listesi
├── baslat.bat                 # Windows tek tıkla başlatma betiği
├── requirements.txt           # Python bağımlılıkları
├── .gitignore                 # Hassas ve geçici dosyaları hariç tutma kuralları
└── .streamlit/
    ├── config.toml            # Streamlit tema ve UI ayarları
    └── secrets.toml.example   # Örnek API anahtarı yapılandırması
```

---

## ⚠️ Yasal Uyarı
Bu yazılım sadece araştırma ve analiz süreçlerini simüle etmek amacıyla geliştirilmiştir. Üretilen analizler, değerlendirmeler ve modeller **kesinlikle yatırım tavsiyesi niteliğinde değildir**.

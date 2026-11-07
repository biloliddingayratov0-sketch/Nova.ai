# NOVA AI — Enterprise Multi-Modal AI SaaS Platform (v3.0)

NOVA AI — bu professional, zamonaviy, to'liq integratsiyalangan va ishlab chiqarishga tayyor (production-ready) ko'p tarmoqli AI SaaS platformasi.

---

## 🌟 Platforma Imkoniyatlari (Features)

1. **AI Chat Assistant (ChatGPT & Claude Experience)**
   - Kontekstni to'liq saqlovchi intellektual chat.
   - Kod sintaksisini ajratib ko'rsatish (syntax highlighting) va nusxalash.
   - Markdown, jadvallar va formulalarni chiroyli render qilish.
   - Suhbatlar tarixi, nomini o'zgartirish, qidiruv va Markdown eksporti.

2. **Professional AI Code Assistant & Sandbox**
   - Kod yaratish (Python, JS, TS, React, Go, Java, C++, SQL).
   - Xatolarni aniqlash (Debugger) va to'g'irlangan kod bilan farqlarni ko'rsatish.
   - Arxitektura va xavfsizlik (OWASP) tekshiruvi (Code Review).
   - Multi-file Project Builder (to'liq papka va fayl strukturalari).
   - **Xavfsiz Sandbox**: Python va JavaScript kodlarini izolyatsiyalangan holda real vaqt rejimida serverda ishga tushirish (xavfsiz subprocess, limitlar va resurs nazorati bilan).

3. **Text-to-Image Generator**
   - DALL-E 3 va Flux AI neyron tarmoqlari orqali yuqori aniqlikdagi tasvirlar yaratish.
   - Visual Styles: Photorealistic, Cinematic, 3D Render, Anime, Digital Art, Fantasy, Minimalist.
   - Aspect Ratios: 1:1, 16:9, 9:16.
   - Negative prompts, prompt tarixi va generatsiya variatsiyalari.

4. **AI Image Editor (Tuzatilgan & Integratsiyalangan)**
   - Yuklangan real rasmlarni AI ko'rsatmalari asosida o'zgartirish (Image-to-Image).
   - Avtomatlashtirilgan RGBA formatlash, kvadratga moslash va 4MB gacha hajmni optimallashtirish.
   - "Before / After" interaktiv taqqoslash slayderi va yuklab olish.

5. **AI Video Generator**
   - Text-to-Video va Image-to-Video rejimlari.
   - Asinxron generatsiya navbati (progress 0% -> 100%).
   - Video player va tayyor MP4 videoni yuklab olish.

6. **AI Voice Studio**
   - Text-to-Speech (TTS): Alloy, Echo, Fable, Onyx, Nova, Shimmer ovozlari.
   - Nutq tezligini boshqarish (0.5x - 2.0x).
   - O'zbek, Ingliz va Rus tillarini qo'llab-quvvatlash.
   - Speech-to-Text (STT) mikrofondan yozib olish.

7. **AI Music Generator**
   - Matn ko'rsatmasi bo'yicha original garmonik musiqalar sintezi.
   - Janrlar: Pop, Hip-Hop, Electronic, Classical, Jazz, Rock, Ambient, Cinematic.
   - Kayfiyatlar: Energetic, Happy, Epic, Relaxing, Romantic, Sad.
   - Pleyer va WAV formatida yuklab olish.

8. **Audio Studio Tools**
   - MP3, WAV, OGG fayllarini yuklash va metama'lumotlarni tahlil qilish.
   - Audio kesish (Start time / End time).
   - Ovoz balandligini kuchaytirish/pasaytirish (-6 dB dan +6 dB gacha).
   - Format konvertatsiyasi.

9. **My Creations (Markaziy Kontent Kutubxonasi)**
   - Rasmlar, tahrirlangan rasmlar, videolar, musiqalar, kod loyihalari va suhbatlar.
   - Qidiruv, saralash, yuklab olish va o'chirish.
   - Foydalanuvchi ma'lumotlarining qat'iy xavfsiz izolyatsiyasi.

10. **SaaS Obuna va To'lov Tizimi (Uzbekistan Payment Rails)**
    - Free Starter, Pro Creator va Ultra Enterprise tariflari.
    - **Click**, **Payme** va **Uzum Bank** rasmiy to'lov protokollari (Merchant prepare/complete, JSON-RPC 2.0, webhooks).
    - Dasturchilar uchun xavfsiz **Sandbox Evaluation Mode** (kartasiz to'lov va kreditlarni faollashtirishni sinash).

11. **Xavfsiz Admin Panel**
    - Faqat `admin` roliga ega foydalanuvchilar uchun kirish huquqi.
    - Platforma ko'rsatkichlari (Foydalanuvchilar, Daromad, AI operatsiyalari).
    - Foydalanuvchilarni boshqarish: Rol o'zgartirish, Akkauntni to'xtatish (Suspend), Kredit qo'shish/kamaytirish.
    - Xavfsizlik va ma'muriy Audit loglar.

12. **In-App Bildirishnomalar (Notifications)**
    - Real-time bildirishnomalar va qo'ng'iroqcha vidjeti.

---

## 🚀 Ishga Tushirish (Quick Start)

### 1. Backend

```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --port 8000 --reload
```

- API Manzili: `http://127.0.0.1:8000`
- API Hujjatlari (Swagger UI): `http://127.0.0.1:8000/docs`

### 2. Frontend

VS Code ichida `frontend/index.html` faylini ochib **Live Server** bilan ishga tushiring (`http://127.0.0.1:5500`).
Yoki terminalda:

```bash
cd frontend
python -m http.server 5500
```

Brauzerda `http://127.0.0.1:5500` manziliga kiring.

---

## 🧪 Avtomatlashtirilgan Testlar (24/24 Passed)

Barcha backend xizmatlarini avtomatlashtirilgan testdan o'tkazish uchun:

```bash
backend\venv\Scripts\python.exe -m pytest backend\tests\test_api.py backend\tests\test_all_features.py -v
```

Haqiqiy tasvir yuklash va Image Editor neyron tarmoq testini tekshirish:

```bash
backend\venv\Scripts\python.exe -m pytest backend\tests\test_image_editor_workflow.py -k "test_image_editor_full_workflow" -v -s
```

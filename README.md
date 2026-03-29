# 🏋️ Fitness Tracker

A full-stack fitness tracking web app built with Flask — track calories, macros, water intake, and daily streaks. Works as a Progressive Web App (PWA) so you can install it on Android or iOS like a native app.

**Live Demo → [https://fitness-tracker-0v3q.onrender.com](https://fitness-tracker-0v3q.onrender.com)**

---

## ✨ Features

- 🍽️ **Food Logging** — Search 900,000+ foods via Edamam API. Log by grams or pieces (e.g. 2 chapatis, 1 banana)
- 🎯 **Calorie Goal** — Personalized daily calorie target based on your BMI, age, weight, and activity level
- 📊 **Macro Targets** — Daily protein, carbs, and fat goals with progress bars
- 💧 **Water Tracker** — Log water intake with quick-add buttons (150ml, 250ml, 500ml, custom)
- 🔥 **Streaks** — Daily logging streak counter with a 35-day heatmap calendar
- 📈 **Analytics** — Calorie bar chart, macro donut chart, goal projection, daily log table
- 👤 **Profile** — BMI display, editable stats, activity level, goal timeline
- 📱 **PWA** — Install on Android/iOS as a home screen app
- 🌙 **Dark Theme** — Clean dark UI optimized for mobile

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask, SQLAlchemy |
| Database | SQLite |
| Auth | Flask-Login |
| Food API | Edamam Food Database API |
| Frontend | HTML, CSS, JavaScript, Chart.js |
| Fonts | Libre Baskerville, Plus Jakarta Sans |
| Deployment | Render.com |
| PWA | manifest.json + Service Worker |

---

## 📁 Project Structure

```
fitness-tracker/
├── app.py                  # Main Flask app, routes, models
├── food_service.py         # Food API service + fallback data
├── migrate.py              # DB migration script
├── requirements.txt        # Python dependencies
├── Procfile                # Render/Gunicorn start command
├── .env                    # API keys (never commit this!)
├── .gitignore
├── templates/
│   ├── base.html           # Base layout, navbar, PWA setup
│   ├── index.html          # Landing page
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html      # Main dashboard
│   ├── log_food.html       # Food search and logging
│   ├── analytics.html      # Charts and analytics
│   └── profile.html        # User profile
└── static/
    ├── css/
    │   └── style.css       # All styles
    ├── manifest.json       # PWA manifest
    ├── sw.js               # Service worker
    └── icons/
        ├── icon-192.png    # PWA icon
        └── icon-512.png    # PWA icon
```

---

## 🚀 Run Locally

### 1. Clone the repo
```bash
git clone https://github.com/piyushparanjape98/fitness-tracker.git
cd fitness-tracker
```

### 2. Create virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up environment variables
Create a `.env` file in the root folder:
```
EDAMAM_APP_ID=your_app_id_here
EDAMAM_APP_KEY=your_app_key_here
```

Get free API keys at [developer.edamam.com](https://developer.edamam.com)

### 5. Set up the database
```bash
python migrate.py
```

### 6. Run the app
```bash
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

---

## 🌐 Deploy to Render (Free)

1. Push your code to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your GitHub repo
4. Set:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn app:app --bind 0.0.0.0:$PORT`
5. Add Environment Variables:
   ```
   EDAMAM_APP_ID     = your_id
   EDAMAM_APP_KEY    = your_key
   SECRET_KEY        = any_random_string
   ```
6. Click **Deploy Web Service**

> ⚠️ Free tier sleeps after 15 min of inactivity. First load may take ~50 seconds to wake up.

---

## 📱 Install as Android App (APK)

1. Make sure your app is deployed and live
2. Go to [pwabuilder.com](https://pwabuilder.com)
3. Paste your live URL and click **Start**
4. Click **Package for Stores**
5. Select **Android** → **Other Android** tab
6. Fill in:
   - Package ID: `com.yourname.fitnesstracker`
   - App name: `Fitness Tracker`
7. Click **Download Package** — you get an `.apk` file
8. Transfer APK to your Android phone
9. Enable **Install from unknown sources** in phone settings
10. Tap the APK to install

---

## 📱 Install on iPhone (iOS)

No APK needed for iOS:
1. Open your live Render URL in **Safari**
2. Tap the **Share** button
3. Tap **"Add to Home Screen"**
4. Tap **Add**

The app appears on your home screen with its own icon.

---

## 🔑 Environment Variables

| Variable | Description |
|---|---|
| `EDAMAM_APP_ID` | Edamam Food Database App ID |
| `EDAMAM_APP_KEY` | Edamam Food Database App Key |
| `SECRET_KEY` | Flask session encryption key |

---

## 🗄️ Database

Uses SQLite locally. Three main tables:

- **User** — profile, goals, macro targets, activity level
- **FoodLog** — daily food entries with calories and macros
- **WaterLog** — daily water intake entries

Run `python migrate.py` after pulling new changes to add any new columns.

---

## 📊 How Calorie Target is Calculated

```
BMR  = Mifflin-St Jeor equation (based on weight, height, age, gender)
TDEE = BMR × Activity multiplier
Goal = TDEE - 500 (lose) | TDEE (maintain) | TDEE + 500 (gain)
```

Macro targets:
```
Protein = 1.6–2.0g per kg bodyweight
Fat     = 25% of total calories
Carbs   = remaining calories
```

---

## 🤝 Contributing

Pull requests are welcome! For major changes please open an issue first.

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

## 👤 Author

**Piyush Paranjape**
- GitHub: [@piyushparanjape98](https://github.com/piyushparanjape98)

---

*Built with Flask + lots of debugging 😅*
# Fitness Tracker – Flask Web App

A minimal **fitness and nutrition tracker** built with Flask, SQLAlchemy, and Chart.js.  
Users can register, log in, log their meals, and visualize calories and macros through an interactive analytics dashboard.

---

## Features

- **User accounts**
  - Registration, login, logout.
  - Profile with daily calorie target and goal (lose / maintain / gain).

- **Daily dashboard**
  - Calories consumed vs target with progress bar.
  - Remaining calories for the day.
  - Total protein and carbs consumed.
  - List of today’s logged foods with per-entry macros and calories.

- **Food logging**
  - Log food name, quantity, and macros (calories, protein, carbs, fat).
  - Macros are multiplied by quantity for each entry.

- **Analytics dashboard**
  - Time-range selector: 7, 14, 30 days.
  - Line chart: daily calories vs target.
  - Doughnut chart: average macro breakdown (protein/carbs/fat).
  - Stacked bar chart: macro trends over time.
  - Line chart: goal achievement percentage per day.

- **Modern UI**
  - Gradient background, glassmorphism-style cards.
  - Responsive layout using CSS grid.
  - Local Chart.js file so graphs work even without external CDNs.

---

## Tech Stack

- **Backend:** Python, Flask, Flask-Login, SQLAlchemy
- **Frontend:** Jinja2 templates, HTML, CSS, Chart.js
- **Database:** SQLite (or any SQLAlchemy-supported DB)
- **Other:** Virtual environment for dependencies

---

## Project Structure
project-root/
│
├── app.py # Main Flask application
├── requirements.txt # Python dependencies
├── README.md # Project documentation
│
├── templates/
│ ├── base.html # Base layout + navbar
│ ├── register.html # Registration page
│ ├── login.html # Login page
│ ├── dashboard.html # Main dashboard (daily stats)
│ ├── analytics.html # Analytics + charts
│ └── profile.html # User profile and goals
│
└── static/
├── css/
│ └── style.css # Global styles (modern UI)
└── js/
└── chart.min.js # Local Chart.js bundle

---

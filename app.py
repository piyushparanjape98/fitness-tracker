from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, and_
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta
import os
import requests
from dotenv import load_dotenv
from food_service import food_service
from flask_login import LoginManager, login_required, login_user, logout_user, current_user, UserMixin

app = Flask(__name__)
load_dotenv()
EDAMAM_APP_ID = os.getenv('EDAMAM_APP_ID')
EDAMAM_APP_KEY = os.getenv('EDAMAM_APP_KEY')
app.config['SECRET_KEY'] = 'my-super-secret-fitness-app-key-123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///fitness_tracker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ─── Models ───────────────────────────────────────────────────────────────────

class User(db.Model, UserMixin):
    id               = db.Column(db.Integer, primary_key=True)
    username         = db.Column(db.String(80), unique=True, nullable=False)
    email            = db.Column(db.String(120), unique=True, nullable=False)
    password_hash    = db.Column(db.String(120), nullable=False)
    height           = db.Column(db.Float)
    weight           = db.Column(db.Float)
    age              = db.Column(db.Integer)
    gender           = db.Column(db.String(10), default='male')
    goal             = db.Column(db.String(20))
    activity_level   = db.Column(db.String(20), default='moderate')
    target_calories  = db.Column(db.Integer)
    water_goal_ml    = db.Column(db.Integer, default=2500)
    # macro targets (g/day)
    target_protein   = db.Column(db.Float, default=0)
    target_carbs     = db.Column(db.Float, default=0)
    target_fat       = db.Column(db.Float, default=0)
    # goal timeline
    goal_weeks       = db.Column(db.Integer, default=12)
    onboarded        = db.Column(db.Boolean, default=False)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)
    food_logs        = db.relationship('FoodLog', backref='user', lazy=True)
    water_logs       = db.relationship('WaterLog', backref='user', lazy=True)


class FoodLog(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date        = db.Column(db.Date, default=date.today)
    food_name   = db.Column(db.String(200), nullable=False)
    calories    = db.Column(db.Float, nullable=False)
    protein     = db.Column(db.Float, default=0)
    carbs       = db.Column(db.Float, default=0)
    fat         = db.Column(db.Float, default=0)
    quantity    = db.Column(db.Float, default=1)
    unit        = db.Column(db.String(30), default='g')   # 'g' or piece label
    logged_at   = db.Column(db.DateTime, default=datetime.utcnow)


class WaterLog(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date        = db.Column(db.Date, default=date.today)
    amount_ml   = db.Column(db.Integer, nullable=False)
    logged_at   = db.Column(db.DateTime, default=datetime.utcnow)


# ─── Helpers ──────────────────────────────────────────────────────────────────

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def calculate_bmr(weight, height, age, gender='male'):
    if gender.lower() == 'male':
        return 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)
    else:
        return 447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age)


ACTIVITY_MULT = {
    'sedentary': 1.2,
    'light':     1.375,
    'moderate':  1.55,
    'active':    1.725,
    'very_active': 1.9
}


def calculate_tdee(bmr, activity_level='moderate'):
    return bmr * ACTIVITY_MULT.get(activity_level, 1.55)


def calculate_target_calories(tdee, goal):
    if goal == 'lose':   return int(tdee - 500)
    elif goal == 'gain': return int(tdee + 500)
    else:                return int(tdee)


def calculate_macro_targets(target_calories, goal, weight):
    """
    Returns (protein_g, carbs_g, fat_g) based on goal.
    Protein: 1.6–2g/kg for lose/gain, 1.4g for maintain
    Fat: 25% of calories
    Carbs: remainder
    """
    if goal == 'lose':
        protein = weight * 2.0
    elif goal == 'gain':
        protein = weight * 2.0
    else:
        protein = weight * 1.6

    fat_cals  = target_calories * 0.25
    fat       = fat_cals / 9
    prot_cals = protein * 4
    carb_cals = target_calories - prot_cals - fat_cals
    carbs     = max(carb_cals / 4, 0)
    return round(protein, 1), round(carbs, 1), round(fat, 1)


def bmi_info(weight, height):
    bmi = weight / ((height / 100) ** 2)
    if bmi < 18.5:   cat = 'Underweight'
    elif bmi < 25:   cat = 'Normal'
    elif bmi < 30:   cat = 'Overweight'
    else:            cat = 'Obese'
    return round(bmi, 1), cat


def get_streak(user_id):
    """Count consecutive days with at least one food log ending today/yesterday."""
    today = date.today()
    streak = 0
    check = today
    while True:
        has_log = FoodLog.query.filter_by(user_id=user_id, date=check).first()
        if has_log:
            streak += 1
            check -= timedelta(days=1)
        else:
            break
    return streak


def get_heatmap_data(user_id, days=35):
    """Returns list of {date, calories, has_log} for last N days."""
    start = date.today() - timedelta(days=days - 1)
    rows = db.session.query(
        FoodLog.date,
        func.sum(FoodLog.calories).label('cal')
    ).filter(
        FoodLog.user_id == user_id,
        FoodLog.date >= start
    ).group_by(FoodLog.date).all()

    # Normalize keys to date objects (SQLite may return strings)
    cal_map = {}
    for r in rows:
        key = r.date if isinstance(r.date, date) else date.fromisoformat(str(r.date))
        cal_map[key] = float(r.cal)

    result = []
    for i in range(days):
        d = start + timedelta(days=i)
        result.append({'date': d.isoformat(), 'calories': cal_map.get(d, 0),
                       'has_log': d in cal_map})
    return result


# ─── Auth ─────────────────────────────────────────────────────────────────────

@app.route('/manifest.json')
def manifest():
    return app.send_static_file('manifest.json')

@app.route('/sw.js')
def service_worker():
    response = app.make_response(app.send_static_file('sw.js'))
    response.headers['Service-Worker-Allowed'] = '/'
    response.headers['Cache-Control'] = 'no-cache'
    return response

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email    = request.form['email']
        password = request.form['password']
        height   = float(request.form.get('height', 170))
        weight   = float(request.form.get('weight', 70))
        age      = int(request.form.get('age', 25))
        gender   = request.form.get('gender', 'male')
        goal     = request.form.get('goal', 'maintain')
        activity = request.form.get('activity_level', 'moderate')
        goal_weeks = int(request.form.get('goal_weeks', 12))

        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return render_template('register.html')
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'danger')
            return render_template('register.html')

        bmr    = calculate_bmr(weight, height, age, gender)
        tdee   = calculate_tdee(bmr, activity)
        target = calculate_target_calories(tdee, goal)
        p, c, f = calculate_macro_targets(target, goal, weight)

        new_user = User(
            username=username, email=email,
            password_hash=generate_password_hash(password),
            height=height, weight=weight, age=age, gender=gender,
            goal=goal, activity_level=activity,
            target_calories=target,
            target_protein=p, target_carbs=c, target_fat=f,
            goal_weeks=goal_weeks,
            water_goal_ml=2500,
            onboarded=True
        )
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(request.args.get('next') or url_for('dashboard'))
        flash('Invalid username or password', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


# ─── Dashboard ────────────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    user  = current_user
    today = date.today()
    logs  = FoodLog.query.filter_by(user_id=user.id, date=today).all()

    total_calories = sum(l.calories for l in logs)
    total_protein  = sum(l.protein  for l in logs)
    total_carbs    = sum(l.carbs    for l in logs)
    total_fat      = sum(l.fat      for l in logs)
    remaining      = user.target_calories - total_calories

    water_logs = WaterLog.query.filter_by(user_id=user.id, date=today).all()
    total_water= sum(w.amount_ml for w in water_logs)
    water_goal = user.water_goal_ml or 2500

    streak      = get_streak(user.id)
    heatmap     = get_heatmap_data(user.id, 35)
    bmi, bmi_cat = bmi_info(user.weight or 70, user.height or 170)

    # Auto-calculate macros for existing users who have 0
    if not user.target_protein:
        p, c, f = calculate_macro_targets(user.target_calories or 2000, user.goal or 'maintain', user.weight or 70)
        user.target_protein, user.target_carbs, user.target_fat = p, c, f
        db.session.commit()
    tgt_p = user.target_protein or 0
    tgt_c = user.target_carbs   or 0
    tgt_f = user.target_fat     or 0

    return render_template('dashboard.html',
        user=user, now=datetime.now(),
        today_logs=logs,
        total_calories=total_calories, total_protein=total_protein,
        total_carbs=total_carbs,       total_fat=total_fat,
        remaining_calories=remaining,
        total_water_ml=total_water,    water_goal=water_goal,
        streak=streak,                 heatmap=heatmap,
        bmi=bmi,                       bmi_cat=bmi_cat,
        tgt_p=tgt_p, tgt_c=tgt_c,     tgt_f=tgt_f
    )


# ─── Food API ─────────────────────────────────────────────────────────────────

@app.route('/api/search_foods')
def search_foods():
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify([])
    url    = 'https://api.edamam.com/api/food-database/v2/parser'
    params = {'app_id': EDAMAM_APP_ID, 'app_key': EDAMAM_APP_KEY, 'ingr': query}
    res    = requests.get(url, params=params, timeout=6)
    if res.status_code != 200:
        return jsonify([])
    data    = res.json()
    results = []
    for item in data.get('hints', [])[:12]:
        food = item['food']
        n    = food.get('nutrients', {})
        # Build measures list (pieces / servings)
        measures = []
        for m in item.get('measures', []):
            label = m.get('label', '')
            weight = m.get('weight', 0)
            if label and weight and label.lower() not in ('gram', 'ounce', 'kilogram', 'pound'):
                measures.append({'label': label, 'weight': weight})
        results.append({
            'id':       food.get('foodId', ''),
            'name':     food['label'],
            'calories': round(n.get('ENERC_KCAL', 0), 1),
            'protein':  round(n.get('PROCNT', 0), 1),
            'carbs':    round(n.get('CHOCDF', 0), 1),
            'fat':      round(n.get('FAT', 0), 1),
            'measures': measures
        })
    return jsonify(results)


@app.route('/log_food', methods=['GET', 'POST'])
@login_required
def log_food():
    if request.method == 'POST':
        food_name = request.form.get('food_name', '').strip()
        qty_str   = request.form.get('quantity', '0').strip()
        unit      = request.form.get('unit', 'g')

        if not food_name or not qty_str:
            flash('Please select a food and enter quantity.', 'warning')
            return redirect(url_for('log_food'))

        try:
            quantity = float(qty_str)
        except ValueError:
            flash('Invalid quantity.', 'warning')
            return redirect(url_for('log_food'))

        def sf(v):
            try: return float(v)
            except: return 0.0

        # cal/protein/etc are already scaled to the entered quantity from JS
        calories = sf(request.form.get('final_calories'))
        protein  = sf(request.form.get('final_protein'))
        carbs    = sf(request.form.get('final_carbs'))
        fat      = sf(request.form.get('final_fat'))

        if calories == 0:
            fd = food_service.get_fallback_foods(food_name)
            if fd:
                f = fd[0]
                calories = f['calories'] * (quantity / 100)
                protein  = f['protein']  * (quantity / 100)
                carbs    = f['carbs']    * (quantity / 100)
                fat      = f['fat']      * (quantity / 100)
            else:
                flash('Food not found!', 'warning')
                return redirect(url_for('log_food'))

        log = FoodLog(
            user_id=current_user.id,
            food_name=food_name, quantity=quantity, unit=unit,
            calories=calories, protein=protein, carbs=carbs, fat=fat
        )
        db.session.add(log)
        db.session.commit()
        flash(f'Logged {quantity}{unit} of {food_name}! ({round(calories)} kcal)', 'success')
        return redirect(url_for('dashboard'))
    return render_template('log_food.html')


# ─── Water ────────────────────────────────────────────────────────────────────

@app.route('/log_water', methods=['POST'])
@login_required
def log_water():
    amount = request.form.get('amount_ml', type=int)
    if not amount or amount <= 0:
        return jsonify({'error': 'Invalid'}), 400
    db.session.add(WaterLog(user_id=current_user.id, amount_ml=amount, date=date.today()))
    db.session.commit()
    today = date.today()
    total = sum(w.amount_ml for w in WaterLog.query.filter_by(user_id=current_user.id, date=today).all())
    goal  = current_user.water_goal_ml or 2500
    return jsonify({'total_ml': total, 'goal_ml': goal,
                    'percent': min(round(total / goal * 100, 1), 100)})


# ─── Profile ──────────────────────────────────────────────────────────────────

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = current_user
    if request.method == 'POST':
        user.height         = float(request.form.get('height', user.height))
        user.weight         = float(request.form.get('weight', user.weight))
        user.age            = int(request.form.get('age', user.age))
        user.gender         = request.form.get('gender', user.gender)
        user.goal           = request.form.get('goal', user.goal)
        user.activity_level = request.form.get('activity_level', user.activity_level)
        user.goal_weeks     = int(request.form.get('goal_weeks', user.goal_weeks or 12))
        user.water_goal_ml  = int(request.form.get('water_goal_ml', user.water_goal_ml or 2500))

        bmr    = calculate_bmr(user.weight, user.height, user.age, user.gender)
        tdee   = calculate_tdee(bmr, user.activity_level)
        user.target_calories = calculate_target_calories(tdee, user.goal)
        p, c, f = calculate_macro_targets(user.target_calories, user.goal, user.weight)
        user.target_protein = p
        user.target_carbs   = c
        user.target_fat     = f
        db.session.commit()
        flash('Profile updated!', 'success')
        return redirect(url_for('profile'))

    bmi, bmi_cat = bmi_info(user.weight or 70, user.height or 170)
    # Auto-calculate macros for existing users who have 0
    if not user.target_protein:
        p, c, f = calculate_macro_targets(user.target_calories or 2000, user.goal or 'maintain', user.weight or 70)
        user.target_protein, user.target_carbs, user.target_fat = p, c, f
        db.session.commit()
    return render_template('profile.html', user=user, bmi=bmi, bmi_cat=bmi_cat)


# ─── Analytics ────────────────────────────────────────────────────────────────

@app.route('/analytics')
@login_required
def analytics():
    days = request.args.get('days', 7, type=int)
    start = datetime.now() - timedelta(days=days)

    daily = db.session.query(
        func.date(FoodLog.logged_at).label('date'),
        func.sum(FoodLog.calories).label('calories'),
        func.sum(FoodLog.protein).label('protein'),
        func.sum(FoodLog.carbs).label('carbs'),
        func.sum(FoodLog.fat).label('fat')
    ).filter(and_(FoodLog.user_id == current_user.id,
                  FoodLog.logged_at >= start)
    ).group_by(func.date(FoodLog.logged_at)).all()

    thirty_ago = datetime.now() - timedelta(days=30)
    avg_macros = db.session.query(
        func.avg(FoodLog.protein).label('protein'),
        func.avg(FoodLog.carbs).label('carbs'),
        func.avg(FoodLog.fat).label('fat'),
        func.avg(FoodLog.calories).label('calories')
    ).filter(and_(FoodLog.user_id == current_user.id,
                  FoodLog.logged_at >= thirty_ago)).first()

    target = current_user.target_calories
    days_on = sum(1 for d in daily if d.calories and abs(d.calories - target) <= 150)
    ach_rate = round(days_on / len(daily) * 100) if daily else 0

    bmi, bmi_cat = bmi_info(current_user.weight or 70, current_user.height or 170)

    # Goal projection
    goal = current_user.goal
    deficit = target - (avg_macros.calories or target) if avg_macros and avg_macros.calories else 0
    kg_per_week = round(deficit * 7 / 7700, 2) if deficit else 0

    import json
    daily_json = json.dumps([{
        'date': str(r.date),
        'calories': float(r.calories or 0),
        'protein':  float(r.protein  or 0),
        'carbs':    float(r.carbs    or 0),
        'fat':      float(r.fat      or 0)
    } for r in daily])

    # Auto-fix macro targets if 0 for existing users
    user = current_user
    if not user.target_protein:
        p, c, f = calculate_macro_targets(user.target_calories or 2000, user.goal or 'maintain', user.weight or 70)
        user.target_protein, user.target_carbs, user.target_fat = p, c, f
        db.session.commit()

    return render_template('analytics.html',
        daily_calories=daily,
        daily_json=daily_json,
        avg_macros=avg_macros,
        achievement_rate=ach_rate,
        target_calories=target,
        bmi=bmi, bmi_cat=bmi_cat,
        kg_per_week=kg_per_week,
        selected_days=days,
        user=current_user
    )


@app.route('/api/analytics_data')
@login_required
def analytics_data():
    days  = request.args.get('days', 7, type=int)
    start = datetime.now() - timedelta(days=days)
    rows  = db.session.query(
        func.date(FoodLog.logged_at).label('date'),
        func.sum(FoodLog.calories).label('calories'),
        func.sum(FoodLog.protein).label('protein'),
        func.sum(FoodLog.carbs).label('carbs'),
        func.sum(FoodLog.fat).label('fat')
    ).filter(and_(FoodLog.user_id == current_user.id,
                  FoodLog.logged_at >= start)
    ).group_by(func.date(FoodLog.logged_at)).all()
    return jsonify([{
        'date': r.date, 'calories': float(r.calories or 0),
        'protein': float(r.protein or 0), 'carbs': float(r.carbs or 0),
        'fat': float(r.fat or 0)
    } for r in rows])


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
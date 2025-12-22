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

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    height = db.Column(db.Float)  # cm
    weight = db.Column(db.Float)  # kg
    age = db.Column(db.Integer)
    goal = db.Column(db.String(20))  # 'lose', 'maintain', 'gain'
    target_calories = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    food_logs = db.relationship('FoodLog', backref='user', lazy=True)

class FoodLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, default=date.today)
    food_name = db.Column(db.String(200), nullable=False)
    calories = db.Column(db.Float, nullable=False)
    protein = db.Column(db.Float, default=0)
    carbs = db.Column(db.Float, default=0)
    fat = db.Column(db.Float, default=0)
    quantity = db.Column(db.Float, default=1)
    logged_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def calculate_bmr(weight, height, age, gender='male'):
    if gender.lower() == 'male':
        return 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)
    else:
        return 447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age)

def calculate_target_calories(bmr, goal, activity_level='moderate'):
    activity_multipliers = {
        'sedentary': 1.2,
        'light': 1.375,
        'moderate': 1.55,
        'active': 1.725,
        'very_active': 1.9
    }
    tdee = bmr * activity_multipliers.get(activity_level, 1.55)
    if goal == 'lose':
        return int(tdee - 500)
    elif goal == 'gain':
        return int(tdee + 500)
    else:
        return int(tdee)

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        height = float(request.form.get('height', 170))
        weight = float(request.form.get('weight', 70))
        age = int(request.form.get('age', 25))
        goal = request.form.get('goal', 'maintain')

        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'danger')
            return render_template('register.html')

        bmr = calculate_bmr(weight, height, age)
        target_calories = calculate_target_calories(bmr, goal)

        new_user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            height=height,
            weight=weight,
            age=age,
            goal=goal,
            target_calories=target_calories
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
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    user = current_user
    today = date.today()
    today_logs = FoodLog.query.filter_by(user_id=user.id, date=today).all()

    total_calories = sum(log.calories for log in today_logs)
    total_protein = sum(log.protein for log in today_logs)
    total_carbs = sum(log.carbs for log in today_logs)
    total_fat = sum(log.fat for log in today_logs)
    remaining_calories = user.target_calories - total_calories

    return render_template('dashboard.html', user=user, today_logs=today_logs,
                           total_calories=total_calories, total_protein=total_protein,
                           total_carbs=total_carbs, total_fat=total_fat, remaining_calories=remaining_calories)

@app.route('/api/search_foods')
def search_foods():
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify([])

    url = f'https://api.edamam.com/api/food-database/v2/parser'
    params = {
        'app_id': EDAMAM_APP_ID,
        'app_key': EDAMAM_APP_KEY,
        'ingr': query
    }
    res = requests.get(url, params=params)
    if res.status_code != 200:
        return jsonify([])

    data = res.json()
    results = []
    hints = data.get('hints', [])
    for item in hints:
        food = item['food']
        nutrients = food.get('nutrients', {})
        results.append({
            'name': food['label'],
            'calories': nutrients.get('ENERC_KCAL', 0),
            'protein': nutrients.get('PROCNT', 0),
            'carbs': nutrients.get('CHOCDF', 0),
            'fat': nutrients.get('FAT', 0)
        })
    return jsonify(results)

@app.route('/log_food', methods=['GET', 'POST'])
@login_required
def log_food():
    if request.method == 'POST':
        food_name = request.form.get('food_name', '').strip()
        quantity_str = request.form.get('quantity', '0').strip()

        if not food_name or not quantity_str:
            flash('Please select a food and enter quantity.', 'warning')
            return redirect(url_for('log_food'))

        try:
            quantity = float(quantity_str)
        except ValueError:
            flash('Invalid quantity value.', 'warning')
            return redirect(url_for('log_food'))

        def to_float_safe(value):
            try:
                return float(value)
            except (ValueError, TypeError):
                return 0.0
        
        calories_per_gram = to_float_safe(request.form.get('custom_calories'))
        protein_per_gram = to_float_safe(request.form.get('custom_protein'))
        carbs_per_gram = to_float_safe(request.form.get('custom_carbs'))
        fat_per_gram = to_float_safe(request.form.get('custom_fat'))

        if calories_per_gram == 0 and protein_per_gram == 0 and carbs_per_gram == 0 and fat_per_gram == 0:
            food_data = food_service.get_fallback_foods(food_name)
            if food_data:
                food = food_data[0]
                calories = food['calories'] * (quantity /100)
                protein = food['protein'] * (quantity /100)
                carbs = food['carbs'] * (quantity /100)
                fat = food['fat'] * (quantity /100)
            else:
                flash('Food not found!', 'warning')
                return redirect(url_for('log_food'))
        else:
            calories = calories_per_gram * (quantity/100)
            protein = protein_per_gram * (quantity/100)
            carbs = carbs_per_gram * (quantity/100)
            fat = fat_per_gram * (quantity/100)

        food_log = FoodLog(
            user_id=current_user.id,
            food_name=food_name,
            quantity=quantity,
            calories=calories,
            protein=protein,
            carbs=carbs,
            fat=fat
        )
        db.session.add(food_log)
        db.session.commit()
        flash(f'Logged {quantity}g of {food_name}!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('log_food.html')

@app.route('/profile')
@login_required
def profile():
    user = current_user
    return render_template('profile.html', user=user)

@app.route('/analytics')
@login_required
def analytics():
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    # Sum daily calories logged by user for last 30 days
    daily_calories = db.session.query(
        func.date(FoodLog.logged_at).label('date'),
        func.sum(FoodLog.calories).label('calories')
    ).filter(
        and_(FoodLog.user_id == current_user.id,
             FoodLog.logged_at >= thirty_days_ago)
    ).group_by(func.date(FoodLog.logged_at)).all()
    
    # Average macros over last 30 days
    weekly_macros = db.session.query(
        func.avg(FoodLog.protein).label('protein'),
        func.avg(FoodLog.carbs).label('carbs'),
        func.avg(FoodLog.fat).label('fat')
    ).filter(
        and_(FoodLog.user_id == current_user.id,
             FoodLog.logged_at >= thirty_days_ago)
    ).first()
    
    target_calories = current_user.target_calories
    days_on_target = sum(1 for day in daily_calories 
                        if abs(day.calories - target_calories) <= 100)
    achievement_rate = (days_on_target / len(daily_calories) * 100) if daily_calories else 0
    
    return render_template('analytics.html', 
                           daily_calories=daily_calories,
                           weekly_macros=weekly_macros,
                           achievement_rate=achievement_rate,
                           target_calories=target_calories)

@app.route('/api/analytics_data')
@login_required
def analytics_data():
    days = request.args.get('days', 7, type=int)
    start_date = datetime.now() - timedelta(days=days)
    
    daily_data = db.session.query(
        func.date(FoodLog.logged_at).label('date'),
        func.sum(FoodLog.calories).label('calories'),
        func.sum(FoodLog.protein).label('protein'),
        func.sum(FoodLog.carbs).label('carbs'),
        func.sum(FoodLog.fat).label('fat')
    ).filter(
        and_(FoodLog.user_id == current_user.id,
             FoodLog.logged_at >= start_date)
    ).group_by(func.date(FoodLog.logged_at)).all()
    
    result = [{
        'date': day.date,
        'calories': float(day.calories or 0),
        'protein': float(day.protein or 0),
        'carbs': float(day.carbs or 0),
        'fat': float(day.fat or 0)
    } for day in daily_data]
    
    return jsonify(result)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

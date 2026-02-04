
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os

# App initialization
app = Flask(__name__)
app.config['SECRET_KEY'] = 'a_secret_key' # Replace with a real secret key in production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    age = db.Column(db.Integer)
    weight = db.Column(db.Float)
    height = db.Column(db.Float)
    goal = db.Column(db.String(50))

class Workout(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    workout_type = db.Column(db.String(100))
    duration = db.Column(db.Integer) # in minutes
    intensity = db.Column(db.String(50))

class Meal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    meal_type = db.Column(db.String(100))
    description = db.Column(db.String(200))
    calories = db.Column(db.Integer)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create_profile', methods=['POST'])
def create_profile():
    # In a real app, you would associate this with the logged-in user
    # For now, we'll create a new user each time for simplicity
    new_user = User(
        name=request.form['name'],
        email=f"{request.form['name'].replace(' ', '.').lower()}@example.com", # Dummy email
        password=generate_password_hash('password', method='pbkdf2:sha256'), # Dummy password
        age=request.form['age'],
        weight=request.form['weight'],
        height=request.form['height'],
        goal=request.form['goal']
    )
    db.session.add(new_user)
    db.session.commit()
    login_user(new_user)
    return redirect(url_for('overview'))

@app.route('/overview')
@login_required
def overview():
    # Dummy data for demonstration
    return render_template('overview.html', user=current_user, calories_burned=1250, workout_count=3, meal_count=4, avg_intensity='Medium', progress_percentage=65, progress_message='You are doing great!')

@app.route('/workout')
@login_required
def workout():
    workouts = Workout.query.filter_by(user_id=current_user.id).all()
    return render_template('workout_tracker.html', workouts=workouts)

@app.route('/add_workout', methods=['POST'])
@login_required
def add_workout():
    new_workout = Workout(
        user_id=current_user.id,
        workout_type=request.form['workout-type'],
        duration=request.form['duration'],
        intensity=request.form['intensity']
    )
    db.session.add(new_workout)
    db.session.commit()
    return redirect(url_for('workout'))

@app.route('/meals')
@login_required
def meals():
    meals = Meal.query.filter_by(user_id=current_user.id).all()
    return render_template('meal_tracker.html', meals=meals)

@app.route('/add_meal', methods=['POST'])
@login_required
def add_meal():
    new_meal = Meal(
        user_id=current_user.id,
        meal_type=request.form['meal-type'],
        description=request.form['description'],
        calories=request.form['calories']
    )
    db.session.add(new_meal)
    db.session.commit()
    return redirect(url_for('meals'))

@app.route('/progress')
@login_required
def progress():
    return render_template('progress.html')

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    current_user.name = request.form['name']
    current_user.age = request.form['age']
    current_user.weight = request.form['weight']
    current_user.height = request.form['height']
    current_user.goal = request.form['goal']
    db.session.commit()
    return redirect(url_for('profile'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('overview'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        hashed_password = generate_password_hash(request.form['password'], method='pbkdf2:sha256')
        new_user = User(name=request.form['name'], email=request.form['email'], password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)

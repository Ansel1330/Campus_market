import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Change this to a secure random string in production

# --- FIXED RENDER STORAGE PATH CONFIGURATION ---
DATABASE_DIR = 'data'  # Removed the leading slash so it saves safely inside your project directory
if not os.path.exists(DATABASE_DIR):
    os.makedirs(DATABASE_DIR)

# Configure SQLite Database path inside the 'data' directory
db_path = os.path.join(os.getcwd(), DATABASE_DIR, 'market.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'auth'  # Redirects unauthorized users to the auth route

# ==========================================
# DATABASE MODELS
# ==========================================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    items = db.relationship('Item', backref='seller', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(255), nullable=True, default='default.jpg')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ==========================================
# ROUTES
# ==========================================

@app.route('/')
def home():
    return redirect(url_for('market'))

@app.route('/auth', methods=['GET', 'POST'])
def auth():
    if current_user.is_authenticated:
        return redirect(url_for('market'))
        
    if request.method == 'POST':
        action = request.form.get('action')
        
        # Handling Login
        if action == 'login':
            email = request.form.get('email')
            password = request.form.get('password')
            user = User.query.filter_by(email=email).first()
            
            if user and user.check_password(password):
                login_user(user)
                return redirect(url_for('market'))
            else:
                flash('Invalid email or password', 'error')
                
        # Handling Registration
        elif action == 'register':
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            
            if User.query.filter_by(email=email).first() or User.query.filter_by(username=username).first():
                flash('Username or Email already exists', 'error')
            else:
                new_user = User(username=username, email=email)
                new_user.set_password(password)
                db.session.add(new_user)
                db.session.commit()
                login_user(new_user)
                return redirect(url_for('market'))
                
    return render_template('auth.html')

@app.route('/market')
def market():
    items = Item.query.order_by(Item.created_at.desc()).all()
    return render_template('market.html', items=items)

@app.route('/item/add', methods=['POST'])
@login_required
def add_item():
    title = request.form.get('title')
    description = request.form.get('description')
    price = request.form.get('price')
    
    if not title or not description or not price:
        flash('All fields are required!', 'error')
        return redirect(url_for('market'))
        
    try:
        new_item = Item(
            title=title,
            description=description,
            price=float(price),
            seller_id=current_user.id
        )
        db.session.add(new_item)
        db.session.commit()
        flash('Item listed successfully!', 'success')
    except ValueError:
        flash('Invalid price format.', 'error')
        
    return redirect(url_for('market'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth'))

# Initialize Database tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)

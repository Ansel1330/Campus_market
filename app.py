import os
from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'super_secure_campus_key'

# --- RENDER STORAGE PATH CONFIGURATION ---
DATABASE_DIR = '/data'
if not os.path.exists(DATABASE_DIR):
    os.makedirs(DATABASE_DIR)

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(DATABASE_DIR, "campus_marketplace.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- DATABASE MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(10), default='student')

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    seller = db.relationship('User', backref=db.backref('products', lazy=True))

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    sender_name = db.Column(db.String(50), nullable=False)
    text = db.Column(db.Text, nullable=False)
    product = db.relationship('Product', backref=db.backref('messages', lazy=True))

# --- SYSTEM INITIALIZATION & OVERSEER CREATION ---
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        hashed_pw = generate_password_hash('overseer2026')
        admin_user = User(username='admin', phone='0500000000', password_hash=hashed_pw, role='admin')
        db.session.add(admin_user)
        db.session.commit()

# --- WEB APP LOGIC & ROUTING ---
@app.route('/campus_market')
def home():
    if not session.get('user'):
        return redirect('/auth')
    products = Product.query.all()
    return render_template('market.html', products=products)

@app.route('/auth')
def auth_page():
    return render_template('auth.html')

@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    phone = request.form['phone']
    password = request.form['password']
    
    if User.query.filter_by(username=username).first():
        return render_template('auth.html', msg="Username already taken!")
        
    hashed_password = generate_password_hash(password)
    new_user = User(username=username, phone=phone, password_hash=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    return render_template('auth.html', msg="Registration successful! Please login.")

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    
    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password_hash, password):
        session['user'] = user.username
        session['user_id'] = user.id
        session['role'] = user.role
        return redirect('/campus_market')
    
    return render_template('auth.html', msg="Invalid username or password.")

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/auth')

@app.route('/sell', methods=['POST'])
def sell_item():
    if not session.get('user'): 
        return redirect('/auth')
    
    new_item = Product(
        title=request.form['title'],
        price=float(request.form['price']),
        category=request.form['category'],
        description=request.form['description'],
        seller_id=session['user_id']
    )
    db.session.add(new_item)
    db.session.commit()
    return redirect('/campus_market')

@app.route('/message/<int:product_id>', methods=['POST'])
def send_message(product_id):
    if not session.get('user'): 
        return redirect('/auth')
    
    new_msg = Message(
        product_id=product_id,
        sender_name=session['user'],
        text=request.form['text']
    )
    db.session.add(new_msg)
    db.session.commit()
    return redirect('/campus_market')

@app.route('/admin/delete/<int:product_id>')
def admin_delete(product_id):
    if session.get('role') != 'admin':
        return "Access Denied: You are not the overseer.", 403
        
    item = Product.query.get(product_id)
    if item:
        Message.query.filter_by(product_id=product_id).delete()
        db.session.delete(item)
        db.session.commit()
    return redirect('/campus_market')
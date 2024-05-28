import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///orders.db'
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
app.config['SECRET_KEY'] = 'your_secret_key'  # Set a secret key for the session
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade="all, delete-orphan")
    payment_method = db.Column(db.String(20), nullable=False)
    paid = db.Column(db.Boolean, default=False)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item = db.Column(db.String(100), nullable=False)
    size = db.Column(db.String(10), nullable=False)
    price = db.Column(db.String(20), nullable=False)
    extra_wishes = db.Column(db.String(200), nullable=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)

class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price_small = db.Column(db.String(20), nullable=True)
    price_medium = db.Column(db.String(20), nullable=True)
    price_large = db.Column(db.String(20), nullable=True)

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ordering_enabled = db.Column(db.Boolean, default=True)
    order_deadline = db.Column(db.Time, nullable=True)

with app.app_context():
    db.create_all()
    if not Settings.query.first():
        db.session.add(Settings(ordering_enabled=True))
        db.session.commit()

@app.route('/')
def index():
    menu = MenuItem.query.all()
    settings = Settings.query.first()
    current_time = datetime.now().time()
    return render_template('index.html', menu=menu, settings=settings, now=current_time)

@app.route('/order', methods=['POST'])
def order():
    settings = Settings.query.first()
    current_time = datetime.now().time()
    
    if not settings.ordering_enabled or (settings.order_deadline and current_time > settings.order_deadline):
        return redirect(url_for('index'))
    
    name = request.form['name']
    items = request.form.getlist('item')
    sizes = request.form.getlist('size')
    extra_wishes_list = request.form.getlist('extra_wishes')
    payment_method = request.form['payment_method']

    new_order = Order(name=name, payment_method=payment_method)
    db.session.add(new_order)
    db.session.commit()

    for item, size, extra_wishes in zip(items, sizes, extra_wishes_list):
        menu_item = MenuItem.query.filter_by(name=item).first()
        if size == 'klein':
            price = menu_item.price_small
        elif size == 'mittel':
            price = menu_item.price_medium
        else:
            price = menu_item.price_large

        new_order_item = OrderItem(item=item, size=size, price=price, extra_wishes=extra_wishes, order_id=new_order.id)
        db.session.add(new_order_item)

    db.session.commit()
    return redirect(url_for('index'))

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        if request.form['password'] == 'azubi':
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin.html', error='Falsches Passwort')
    return render_template('admin.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))
    
    orders = Order.query.all()
    menu = MenuItem.query.all()
    settings = Settings.query.first()
    return render_template('admin_dashboard.html', orders=orders, menu=menu, settings=settings)

@app.route('/admin/mark_paid/<int:order_id>')
def mark_paid(order_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))
    
    order = Order.query.get(order_id)
    order.paid = True
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_order/<int:order_id>', methods=['POST'])
def delete_order(order_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))
    
    order = Order.query.get(order_id)
    db.session.delete(order)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_menu_item', methods=['POST'])
def add_menu_item():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))
    
    item_name = request.form['item_name']
    item_price_small = request.form['item_price_small']
    item_price_medium = request.form['item_price_medium']
    item_price_large = request.form['item_price_large']
    new_item = MenuItem(name=item_name, price_small=item_price_small, price_medium=item_price_medium, price_large=item_price_large)
    db.session.add(new_item)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/toggle_ordering', methods=['POST'])
def toggle_ordering():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))
    
    settings = Settings.query.first()
    settings.ordering_enabled = not settings.ordering_enabled
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/set_order_deadline', methods=['POST'])
def set_order_deadline():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))
    
    settings = Settings.query.first()
    order_deadline = request.form.get('order_deadline')
    if order_deadline:
        settings.order_deadline = datetime.strptime(order_deadline, '%H:%M').time()
    else:
        settings.order_deadline = None
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)

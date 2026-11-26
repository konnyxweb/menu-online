import os
import time
from functools import wraps
from flask import (
    Flask, render_template, request, jsonify, redirect,
    url_for, session, send_file, flash
)
from werkzeug.utils import secure_filename
import database
import pdf_generator

base_dir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__, template_folder=os.path.join(base_dir, 'templates'))
app.secret_key = os.environ.get('SECRET_KEY', 'menu-online-secret-key-2026')
application = app

UPLOAD_FOLDER = os.path.join(base_dir, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

database.init_db()


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': 'Sesión no autorizada'}), 401
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


# ==================== VISTA PÚBLICA ====================

@app.route('/')
def index():
    settings = database.get_settings()
    menu_grouped = database.get_menu_grouped(only_active=True)
    return render_template('index.html', settings=settings, menu=menu_grouped)


# ==================== AUTENTICACIÓN ADMIN ====================

@app.route('/login', methods=['GET', 'POST'])
def admin_login():
    settings = database.get_settings()
    if request.method == 'POST':
        password = request.form.get('password', '').strip()
        expected = settings.get('admin_password') or 'admin123'
        if password == expected:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_panel'))
        flash('Contraseña incorrecta. Intenta de nuevo.', 'error')
    return render_template('login.html', settings=settings)


@app.route('/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))


# ==================== PANEL DE ADMINISTRACIÓN ====================

@app.route('/admin')
@login_required
def admin_panel():
    settings = database.get_settings()
    categories = database.get_categories(only_active=False)
    products = database.get_products(only_active=False)
    return render_template(
        'admin.html',
        settings=settings,
        categories=categories,
        products=products,
        default_public_url=request.url_root
    )


# ==================== API RUBROS (CATEGORÍAS) ====================

@app.route('/api/categories', methods=['POST'])
@login_required
def api_create_category():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'success': False, 'error': 'El nombre del rubro es obligatorio'}), 400
    cat_id = database.create_category(name, data.get('description', ''))
    return jsonify({'success': True, 'id': cat_id, 'categories': database.get_categories(False)})


@app.route('/api/categories/<int:cat_id>', methods=['PUT'])
@login_required
def api_update_category(cat_id):
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'success': False, 'error': 'El nombre del rubro es obligatorio'}), 400
    ok = database.update_category(cat_id, name, data.get('description', ''), data.get('active', 1))
    return jsonify({'success': ok, 'categories': database.get_categories(False)})


@app.route('/api/categories/<int:cat_id>', methods=['DELETE'])
@login_required
def api_delete_category(cat_id):
    ok = database.delete_category(cat_id)
    return jsonify({
        'success': ok,
        'categories': database.get_categories(False),
        'products': database.get_products(False)
    })


# ==================== API PRODUCTOS ====================

@app.route('/api/products', methods=['POST'])
@login_required
def api_create_product():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    category_id = data.get('category_id')
    if not name or not category_id:
        return jsonify({'success': False, 'error': 'Rubro y nombre del producto son obligatorios'}), 400
    try:
        price = float(data.get('price', 0.0))
    except ValueError:
        return jsonify({'success': False, 'error': 'Precio inválido'}), 400

    prod_id = database.create_product(
        category_id=int(category_id),
        name=name,
        description=data.get('description', ''),
        price=price,
        active=int(data.get('active', 1))
    )
    return jsonify({'success': True, 'id': prod_id, 'products': database.get_products(False)})


@app.route('/api/products/<int:prod_id>', methods=['PUT'])
@login_required
def api_update_product(prod_id):
    data = request.get_json() or {}
    ok = database.update_product(
        prod_id=prod_id,
        category_id=data.get('category_id'),
        name=data.get('name'),
        description=data.get('description'),
        price=data.get('price'),
        active=data.get('active')
    )
    if not ok:
        return jsonify({'success': False, 'error': 'Producto no encontrado'}), 404
    return jsonify({'success': True, 'products': database.get_products(False)})


@app.route('/api/products/<int:prod_id>', methods=['DELETE'])
@login_required
def api_delete_product(prod_id):
    ok = database.delete_product(prod_id)
    return jsonify({'success': ok, 'products': database.get_products(False)})


# ==================== API CONFIGURACIÓN, LOGO Y QR ====================

@app.route('/api/settings', methods=['POST'])
@login_required
def api_update_settings():
    data = {}
    for field in [
        'restaurant_name', 'tagline', 'phone', 'whatsapp', 'address',
        'hours', 'instagram', 'currency_symbol', 'public_url',
        'admin_password', 'pdf_footer_note'
    ]:
        if field in request.form:
            data[field] = request.form.get(field, '')

    # Manejo de subida de Logo
    logo_file = request.files.get('logo_file')
    if logo_file and logo_file.filename:
        ext = os.path.splitext(secure_filename(logo_file.filename))[1].lower()
        if ext in {'.png', '.jpg', '.jpeg', '.webp'}:
            fname = f"logo_{int(time.time())}{ext}"
            logo_file.save(os.path.join(UPLOAD_FOLDER, fname))
            data['logo_path'] = f"/static/uploads/{fname}"

    # Manejo de subida de QR personalizado opcional
    qr_file = request.files.get('qr_file')
    if qr_file and qr_file.filename:
        ext = os.path.splitext(secure_filename(qr_file.filename))[1].lower()
        if ext in {'.png', '.jpg', '.jpeg', '.webp'}:
            fname = f"qr_{int(time.time())}{ext}"
            qr_file.save(os.path.join(UPLOAD_FOLDER, fname))
            data['qr_custom_path'] = f"/static/uploads/{fname}"

    if request.form.get('clear_custom_qr') == '1':
        data['qr_custom_path'] = ''

    updated = database.update_settings(data)
    return jsonify({'success': True, 'settings': updated})


# ==================== EXPORTACIÓN A PDF ====================

@app.route('/api/menu/pdf')
@login_required
def api_export_menu_pdf():
    settings = database.get_settings()
    menu_grouped = database.get_menu_grouped(only_active=True)
    fallback_url = request.url_root
    pdf_stream = pdf_generator.build_menu_pdf(settings, menu_grouped, base_dir, fallback_url=fallback_url)

    rest_slug = secure_filename(settings.get('restaurant_name') or 'Menu_Online')
    filename = f"Menu_{rest_slug}.pdf"
    return send_file(
        pdf_stream,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("===========================================================")
    print("🍽️  MENÚ ONLINE — Catálogo Digital & PDF para Imprimir")
    print(f"📍 Catálogo Público: http://localhost:{port}/")
    print(f"🔐 Panel Admin:      http://localhost:{port}/admin")
    print("===========================================================")
    app.run(host='0.0.0.0', port=port, debug=True)

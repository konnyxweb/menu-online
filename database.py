import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'menu.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_db():
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                order_index INTEGER DEFAULT 0,
                active INTEGER DEFAULT 1
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                price REAL NOT NULL DEFAULT 0.0,
                active INTEGER DEFAULT 1,
                order_index INTEGER DEFAULT 0,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                restaurant_name TEXT DEFAULT 'Brisa Marina',
                tagline TEXT DEFAULT 'Cocina Costera & Productos del Mar',
                phone TEXT DEFAULT '+58 (0414) 000-0000',
                whatsapp TEXT DEFAULT '',
                address TEXT DEFAULT 'Av. Principal, Local 4',
                hours TEXT DEFAULT 'Martes a Domingo · 12:00 PM - 10:00 PM',
                instagram TEXT DEFAULT '@brisamarina',
                currency_symbol TEXT DEFAULT '$',
                public_url TEXT DEFAULT '',
                logo_path TEXT DEFAULT '',
                qr_custom_path TEXT DEFAULT '',
                admin_password TEXT DEFAULT 'admin123',
                pdf_footer_note TEXT DEFAULT 'Escanea el código QR para consultar nuestro menú digital actualizado.'
            )
        ''')

        # Sembrar configuración por defecto si no existe
        cursor.execute('SELECT COUNT(*) as c FROM settings')
        if cursor.fetchone()['c'] == 0:
            cursor.execute('INSERT INTO settings (id) VALUES (1)')

        # Sembrar rubro inicial "Productos del Mar" si la base está vacía
        cursor.execute('SELECT COUNT(*) as c FROM categories')
        if cursor.fetchone()['c'] == 0:
            cursor.execute('''
                INSERT INTO categories (name, description, order_index, active)
                VALUES (?, ?, 1, 1)
            ''', ('Productos del Mar', 'Pesca fresca del día, ceviches, arroces y especialidades marinas.'))
            cat_id = cursor.lastrowid

            initial_products = [
                ('Ceviche Clásico de Corvina', 'Cubos de corvina fresca marinados en leche de tigre cítrica, cebolla morada, cilantro, maíz chulpi y batata glaseada.', 12.00),
                ('Ceviche Mixto del Puerto', 'Corvina, camarones y calamares frescos en emulsión de ají amarillo y limón, acompañado de tostones crujientes.', 15.50),
                ('Camarones al Ajillo', 'Salteados en mantequilla clarificada, láminas de ajo dorado, perejil fresco y un toque de vino blanco con pan artesanal.', 14.50),
                ('Calamares a la Romana', 'Anillos de calamar tiernos en rebozado ligero y crujiente, servidos con salsa tártara de la casa y gajos de limón.', 11.00),
                ('Pargo Rojo Frito Entero', 'Pargo fresco crocante por fuera y jugoso por dentro, acompañado de tostones, ensalada fresca y salsa guasacaca.', 18.00),
                ('Filete de Róbalo a la Plancha', 'Sellado a la plancha con hierbas finas y mantequilla de limón, servido sobre puré cremoso y vegetales salteados.', 17.50),
                ('Arroz a la Marinera', 'Arroz meloso cocido en fondo concentrado de mariscos con camarones, mejillones, calamares y pimentón asado.', 16.50),
                ('Parrilla Mar y Tierra (2 pers.)', 'Selección de langostinos, filete de pescado, calamares a la plancha y acompañantes de la casa.', 29.00),
                ('Sopa Marinera (Fosforera)', 'Caldo tradicional concentrado de pescado y mariscos con cangrejo, mejillones, camarones y cilantro fresco.', 13.50),
                ('Tostones Playeros con Camarones', 'Crujientes tostones de plátano verde coronados con camarones salteados en salsa rosada cítrica y queso rallado.', 10.50),
            ]
            for idx, (pname, pdesc, pprice) in enumerate(initial_products, start=1):
                cursor.execute('''
                    INSERT INTO products (category_id, name, description, price, active, order_index)
                    VALUES (?, ?, ?, ?, 1, ?)
                ''', (cat_id, pname, pdesc, pprice, idx))

        conn.commit()


# ==================== SETTINGS ====================

def get_settings():
    with get_db() as conn:
        row = conn.execute('SELECT * FROM settings WHERE id = 1').fetchone()
        return dict(row) if row else {}


def update_settings(data):
    allowed = [
        'restaurant_name', 'tagline', 'phone', 'whatsapp', 'address',
        'hours', 'instagram', 'currency_symbol', 'public_url',
        'logo_path', 'qr_custom_path', 'admin_password', 'pdf_footer_note'
    ]
    fields = []
    values = []
    for k in allowed:
        if k in data:
            fields.append(f"{k} = ?")
            values.append(str(data[k]).strip())
    if not fields:
        return get_settings()

    with get_db() as conn:
        conn.execute(f"UPDATE settings SET {', '.join(fields)} WHERE id = 1", values)
        conn.commit()
    return get_settings()


# ==================== RUBROS / CATEGORÍAS ====================

def get_categories(only_active=False):
    with get_db() as conn:
        sql = 'SELECT * FROM categories'
        if only_active:
            sql += ' WHERE active = 1'
        sql += ' ORDER BY order_index ASC, id ASC'
        rows = conn.execute(sql).fetchall()
        return [dict(r) for r in rows]


def create_category(name, description=''):
    with get_db() as conn:
        cur = conn.cursor()
        max_row = cur.execute('SELECT COALESCE(MAX(order_index), 0) as m FROM categories').fetchone()
        next_ord = (max_row['m'] or 0) + 1
        cur.execute('''
            INSERT INTO categories (name, description, order_index, active)
            VALUES (?, ?, ?, 1)
        ''', (name.strip(), description.strip(), next_ord))
        conn.commit()
        return cur.lastrowid


def update_category(cat_id, name, description='', active=1):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute('''
            UPDATE categories
            SET name = ?, description = ?, active = ?
            WHERE id = ?
        ''', (name.strip(), description.strip(), int(active), cat_id))
        conn.commit()
        return cur.rowcount > 0


def delete_category(cat_id):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute('DELETE FROM categories WHERE id = ?', (cat_id,))
        conn.commit()
        return cur.rowcount > 0


# ==================== PRODUCTOS ====================

def get_products(only_active=False, category_id=None):
    with get_db() as conn:
        sql = '''
            SELECT p.*, c.name as category_name
            FROM products p
            JOIN categories c ON p.category_id = c.id
            WHERE 1=1
        '''
        params = []
        if only_active:
            sql += ' AND p.active = 1 AND c.active = 1'
        if category_id is not None:
            sql += ' AND p.category_id = ?'
            params.append(category_id)
        sql += ' ORDER BY c.order_index ASC, c.id ASC, p.order_index ASC, p.id ASC'
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def get_menu_grouped(only_active=True):
    """Retorna lista de rubros, cada uno con su lista de productos anidada."""
    cats = get_categories(only_active=only_active)
    prods = get_products(only_active=only_active)
    prod_map = {}
    for p in prods:
        prod_map.setdefault(p['category_id'], []).append(p)

    grouped = []
    for c in cats:
        c['products'] = prod_map.get(c['id'], [])
        if only_active and not c['products']:
            continue
        grouped.append(c)
    return grouped


def create_product(category_id, name, description, price, active=1):
    with get_db() as conn:
        cur = conn.cursor()
        max_row = cur.execute('SELECT COALESCE(MAX(order_index), 0) as m FROM products WHERE category_id = ?', (category_id,)).fetchone()
        next_ord = (max_row['m'] or 0) + 1
        cur.execute('''
            INSERT INTO products (category_id, name, description, price, active, order_index)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (int(category_id), name.strip(), description.strip(), float(price), int(active), next_ord))
        conn.commit()
        return cur.lastrowid


def update_product(prod_id, category_id=None, name=None, description=None, price=None, active=None):
    with get_db() as conn:
        cur = conn.cursor()
        row = cur.execute('SELECT * FROM products WHERE id = ?', (prod_id,)).fetchone()
        if not row:
            return False
        d = dict(row)
        new_cat = d['category_id'] if category_id is None else int(category_id)
        new_name = d['name'] if name is None else name.strip()
        new_desc = d['description'] if description is None else description.strip()
        new_price = d['price'] if price is None else float(price)
        new_active = d['active'] if active is None else int(active)

        cur.execute('''
            UPDATE products
            SET category_id = ?, name = ?, description = ?, price = ?, active = ?
            WHERE id = ?
        ''', (new_cat, new_name, new_desc, new_price, new_active, prod_id))
        conn.commit()
        return True


def delete_product(prod_id):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute('DELETE FROM products WHERE id = ?', (prod_id,))
        conn.commit()
        return cur.rowcount > 0

from flask import render_template, flash, redirect, url_for, request, Blueprint, current_app, jsonify
from flask_login import login_required, current_user
from application.extensions import mysql
from ..forms import OrderForm
import logging

orders_bp = Blueprint('orders', __name__)
logger = logging.getLogger(__name__)


@orders_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_order():
    form = OrderForm()

    if len(form.items) == 0:
        form.items.append_entry()

    if request.method == 'POST':
        current_app.logger.info("Form submitted with data: %s", request.form)

        # Получаем shop_id из формы
        shop_id = request.form.get('shop_id')
        current_app.logger.info(f"Received shop_id: {shop_id}")

        # Если shop_id не получен, попробуем получить из другого источника
        if not shop_id:
            shop_id = request.form.get('selected-shop-id')
            current_app.logger.info(f"Trying alternative shop_id: {shop_id}")

        # Если все еще нет, создаем ошибку
        if not shop_id:
            flash('Магазин не выбран', 'danger')
            return render_template('orders/add.html', form=form, is_index=False)

        form.shop_id.data = shop_id

        items_data = []
        i = 0
        while True:
            product_id_key = f'items-{i}-product_id'
            quantity_key = f'items-{i}-quantity'

            if product_id_key not in request.form:
                break

            # Преобразуем количество в число
            try:
                quantity = int(request.form.get(quantity_key, 1))
            except (TypeError, ValueError):
                quantity = 1  # Значение по умолчанию при ошибке

            items_data.append({
                'product_id': request.form.get(product_id_key),
                'quantity': quantity
            })
            i += 1

        # Очищаем и перезаполняем элементы формы
        while len(form.items) > 0:
            form.items.pop_entry()

        for item_data in items_data:
            item_form = form.items.append_entry()
            item_form.product_id.data = item_data['product_id']
            item_form.quantity.data = item_data['quantity']  # Теперь это число

        if form.validate():
            try:
                with mysql.connection.cursor() as cur:
                    # Проверка магазина
                    cur.execute("SELECT id FROM shops WHERE id = %s", (form.shop_id.data,))
                    if not cur.fetchone():
                        flash('Выбранный магазин не существует', 'danger')
                        return render_template('orders/add.html', form=form)

                    # Создаем заказ
                    cur.execute("INSERT INTO orders (shop_id) VALUES (%s)", (form.shop_id.data,))
                    order_id = cur.lastrowid

                    # Добавляем товары
                    for item in form.items:
                        product_id = item.product_id.data
                        quantity = item.quantity.data

                        if product_id and quantity:
                            # Проверка товара
                            cur.execute("SELECT id FROM products WHERE id = %s", (product_id,))
                            if not cur.fetchone():
                                flash(f'Товар с ID {product_id} не существует', 'danger')
                                continue

                            cur.execute(
                                """INSERT INTO order_items 
                                   (order_id, product_id, quantity) 
                                   VALUES (%s, %s, %s)""",
                                (order_id, product_id, quantity)
                            )

                    mysql.connection.commit()
                    flash('Заказ успешно создан!', 'success')
                    return redirect(url_for('orders.list_orders'))

            except Exception as e:
                mysql.connection.rollback()
                error_msg = f'Ошибка создания заказа: {str(e)}'
                flash(error_msg, 'danger')
                current_app.logger.error(error_msg, exc_info=True)
        else:
            error_msg = f'Ошибка валидации формы: {form.errors}'
            flash(error_msg, 'danger')
            current_app.logger.error(error_msg)

    return render_template('orders/add.html', form=form, is_index=False)


@orders_bp.route('/list')
@login_required
def list_orders():
    try:
        with mysql.connection.cursor() as cur:
            cur.execute("""
                SELECT 
                    o.id, 
                    DATE_FORMAT(o.created_at, '%Y-%m-%d %H:%i') as order_date,
                    s.name AS shop_name,
                    COALESCE((
                        SELECT SUM(p.price * oi.quantity)
                        FROM order_items oi
                        JOIN products p ON oi.product_id = p.id
                        WHERE oi.order_id = o.id
                    ), 0) AS total_sum
                FROM 
                    orders o
                JOIN 
                    shops s ON o.shop_id = s.id
                ORDER BY 
                    o.created_at DESC
            """)
            orders = cur.fetchall()
            return render_template('orders/list.html', orders=orders, is_index=False)

    except Exception as e:
        current_app.logger.error(f"Error in list_orders: {str(e)}", exc_info=True)
        flash('Ошибка при загрузке списка заказов', 'danger')
        return redirect(url_for('main.dashboard'))


@orders_bp.route('/details/<int:order_id>')
@login_required
def order_details(order_id):
    if current_user.role not in ['admin', 'moderator', 'operator']:
        flash('У вас нет прав для просмотра деталей заказов', 'danger')
        return redirect(url_for('main.dashboard', is_index=False))

    try:
        with mysql.connection.cursor() as cur:
            query = """
                SELECT 
                    o.id,
                    DATE_FORMAT(o.created_at, %s) as order_date,
                    s.name AS shop_name,
                    s.address AS shop_address,
                    COALESCE((
                        SELECT SUM(p.price * oi.quantity)
                        FROM order_items oi
                        JOIN products p ON oi.product_id = p.id
                        WHERE oi.order_id = o.id
                    ), 0) AS total_sum
                FROM 
                    orders o
                JOIN 
                    shops s ON o.shop_id = s.id
                WHERE 
                    o.id = %s
            """
            date_format = '%Y-%m-%d %H:%i'
            cur.execute(query, (date_format, order_id))
            order = cur.fetchone()

            if not order:
                flash('Заказ не найден', 'danger')
                return redirect(url_for('orders.list_orders'))

            cur.execute("""
                SELECT 
                    p.name AS product_name,
                    p.manufacturer,
                    p.price,
                    oi.quantity,
                    (p.price * oi.quantity) AS item_total
                FROM 
                    order_items oi
                JOIN 
                    products p ON oi.product_id = p.id
                WHERE 
                    oi.order_id = %s
            """, (order_id,))
            items = cur.fetchall()

            return render_template('orders/details.html', order=order, items=items, is_index=False)

    except Exception as e:
        current_app.logger.error(f"Error in order_details: {str(e)}", exc_info=True)
        flash('Ошибка при загрузке деталей заказа', 'danger')
        return redirect(url_for('orders.list_orders', is_index=False))


@orders_bp.route('/edit/<int:order_id>', methods=['GET', 'POST'])
@login_required
def edit_order(order_id):
    if current_user.role not in ['admin', 'moderator', 'operator']:
        flash('У вас нет прав для редактирования заказов', 'danger')
        return redirect(url_for('main.dashboard', is_index=False))

    form = OrderForm()

    try:
        with mysql.connection.cursor() as cur:
            # Получаем информацию о заказе
            cur.execute("SELECT id, shop_id FROM orders WHERE id = %s", (order_id,))
            order = cur.fetchone()

            if not order:
                flash('Заказ не найден', 'danger')
                return redirect(url_for('orders.list_orders'))

            # Получаем текущие товары в заказе
            cur.execute("SELECT product_id, quantity FROM order_items WHERE order_id = %s", (order_id,))
            items = cur.fetchall()

            if request.method == 'POST':
                form.shop_id.data = request.form.get('shop_id')

                items_data = []
                i = 0
                while True:
                    product_id_key = f'items-{i}-product_id'
                    quantity_key = f'items-{i}-quantity'

                    if product_id_key not in request.form:
                        break

                    # Преобразуем количество в число
                    try:
                        quantity = int(request.form.get(quantity_key, 1))
                    except (TypeError, ValueError):
                        quantity = 1

                    items_data.append({
                        'product_id': request.form.get(product_id_key),
                        'quantity': quantity
                    })
                    i += 1

                # Очищаем и перезаполняем элементы формы
                while len(form.items) > 0:
                    form.items.pop_entry()

                for item_data in items_data:
                    item_form = form.items.append_entry()
                    item_form.product_id.data = item_data['product_id']
                    item_form.quantity.data = item_data['quantity']  # Теперь это число

                if form.validate():
                    try:
                        # Проверка магазина
                        cur.execute("SELECT id FROM shops WHERE id = %s", (form.shop_id.data,))
                        if not cur.fetchone():
                            flash('Выбранный магазин не существует', 'danger')
                            return render_template('orders/edit.html', form=form, order_id=order_id, is_index=False)

                        # Обновляем магазин заказа
                        cur.execute("UPDATE orders SET shop_id = %s WHERE id = %s", (form.shop_id.data, order_id))

                        # Удаляем все текущие товары из заказа
                        cur.execute("DELETE FROM order_items WHERE order_id = %s", (order_id,))

                        # Добавляем товары из формы
                        for item in form.items:
                            product_id = item.product_id.data
                            quantity = item.quantity.data

                            if product_id and quantity:
                                cur.execute("SELECT id FROM products WHERE id = %s", (product_id,))
                                if not cur.fetchone():
                                    flash(f'Товар с ID {product_id} не существует', 'danger')
                                    continue

                                cur.execute(
                                    """INSERT INTO order_items 
                                       (order_id, product_id, quantity) 
                                       VALUES (%s, %s, %s)""",
                                    (order_id, product_id, quantity)
                                )

                        mysql.connection.commit()
                        flash('Заказ успешно обновлён!', 'success')
                        return redirect(url_for('orders.order_details', order_id=order_id, is_index=False))

                    except Exception as e:
                        mysql.connection.rollback()
                        flash(f'Ошибка обновления заказа: {str(e)}', 'danger')
                else:
                    flash('Ошибка валидации формы. Проверьте введённые данные.', 'danger')

            # Заполняем названия для предзаполнения
            shop_name = ""
            product_names = {}

            # Название магазина
            cur.execute("SELECT name FROM shops WHERE id = %s", (order['shop_id'],))
            shop = cur.fetchone()
            shop_name = shop['name'] if shop else ""

            # Названия товаров
            for item in items:
                cur.execute("SELECT name FROM products WHERE id = %s", (item['product_id'],))
                product = cur.fetchone()
                if product:
                    product_names[item['product_id']] = product['name']

            # Заполняем форму данными
            form.shop_id.data = order['shop_id']

            # Очищаем и заполняем элементы товаров
            while len(form.items) > 0:
                form.items.pop_entry()

            for item in items:
                form.items.append_entry({
                    'product_id': item['product_id'],
                    'quantity': item['quantity']
                })

            return render_template('orders/edit.html',
                                   form=form,
                                   order_id=order_id,
                                   shop_name=shop_name,
                                   product_names=product_names,
                                   is_index=False)

    except Exception as e:
        current_app.logger.error(f"Error in edit_order: {str(e)}", exc_info=True)
        flash('Ошибка при загрузке страницы редактирования', 'danger')
        return redirect(url_for('orders.list_orders', is_index=False))


@orders_bp.route('/api/search/shops')
@login_required
def search_shops():
    query = request.args.get('q', '').strip()
    if len(query) < 1:
        return jsonify([])

    try:
        with mysql.connection.cursor() as cur:
            cur.execute("""
                SELECT id, name 
                FROM shops 
                WHERE name LIKE CONCAT(%s, '%%')
                ORDER BY name 
                LIMIT 5
            """, (query,))
            shops = cur.fetchall()
            return jsonify(shops)
    except Exception as e:
        current_app.logger.error(f"Ошибка поиска магазинов: {str(e)}", exc_info=True)
        return jsonify([])


@orders_bp.route('/api/search/products')
@login_required
def search_products():
    query = request.args.get('q', '').strip()
    if len(query) < 1:
        return jsonify([])

    try:
        with mysql.connection.cursor() as cur:
            cur.execute("""
                SELECT id, name 
                FROM products 
                WHERE name LIKE CONCAT(%s, '%%')
                ORDER BY name 
                LIMIT 5
            """, (query,))
            products = cur.fetchall()
            return jsonify(products)
    except Exception as e:
        current_app.logger.error(f"Ошибка поиска товаров: {str(e)}", exc_info=True)
        return jsonify([])
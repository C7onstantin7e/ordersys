from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from ..extensions import mysql

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/users')
@login_required
def manage_users():
    if current_user.role != 'admin':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('products.list_products'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT id, username, email, role, created_at FROM users")
    users = cur.fetchall()
    cur.close()
    return render_template('admin/users.html', users=users, is_index=True)
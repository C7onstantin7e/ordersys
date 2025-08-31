from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from ..extensions import mysql
from ..models import User
from ..forms import LoginForm, RegistrationForm

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s", (form.username.data,))
        user_data = cur.fetchone()
        cur.close()

        if user_data and check_password_hash(user_data['password'], form.password.data):
            user = User(
                id=user_data['id'],
                username=user_data['username'],
                email=user_data['email'],
                role=user_data['role']
            )
            login_user(user)
            flash('Вы успешно вошли!', 'success')
            return redirect(url_for('products.list_products'))
        flash('Неверный логин или пароль', 'danger')
    return render_template('auth/login.html', form=form, is_index=True)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        try:
            cur = mysql.connection.cursor()
            cur.execute("""
                INSERT INTO users (username, email, password, role)
                VALUES (%s, %s, %s, %s)
            """, (form.username.data, form.email.data, hashed_password, form.role.data))
            mysql.connection.commit()
            cur.close()
            flash('Регистрация успешна!', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Ошибка регистрации: {str(e)}', 'danger')
    return render_template('auth/register.html', form=form, is_index=True)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('auth.login', is_index=False))


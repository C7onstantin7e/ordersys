import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash


def init_remote_db(host, user, password, database):
    try:
        # Подключение к удаленной базе данных
        connection = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )

        if connection.is_connected():
            cursor = connection.cursor()

            print("Удаленное подключение к базе данных успешно установлено")

            # 1. Удаляем таблицы в правильном порядке (если они существуют)
            cursor.execute("DROP TABLE IF EXISTS order_items")
            cursor.execute("DROP TABLE IF EXISTS orders")
            cursor.execute("DROP TABLE IF EXISTS products")
            cursor.execute("DROP TABLE IF EXISTS shops")
            cursor.execute("DROP TABLE IF EXISTS users")

            # 2. Создаем таблицу пользователей
            cursor.execute("""
                CREATE TABLE users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    role ENUM('admin', 'moderator', 'operator') NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB
            """)

            # 3. Создаем таблицу магазинов (исправлено: в оригинале было дважды products)
            cursor.execute("""
                CREATE TABLE shops (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    address VARCHAR(255) NOT NULL
                ) ENGINE=InnoDB
            """)

            # 4. Создаем таблицу товаров
            cursor.execute("""
                CREATE TABLE products (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    manufacturer VARCHAR(100) NOT NULL,
                    price INT NOT NULL,
                    unit ENUM('кг', 'шт') NOT NULL DEFAULT 'шт'
                ) ENGINE=InnoDB
            """)

            # 5. Создаем таблицу заказов
            cursor.execute("""
                CREATE TABLE orders (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    shop_id INT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (shop_id) REFERENCES shops(id)
                ) ENGINE=InnoDB
            """)

            # 6. Создаем таблицу элементов заказа
            cursor.execute("""
                CREATE TABLE order_items (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    order_id INT NOT NULL,
                    product_id INT NOT NULL,
                    quantity INT NOT NULL,
                    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                    FOREIGN KEY (product_id) REFERENCES products(id)
                ) ENGINE=InnoDB
            """)

            # 7. Добавляем тестовые данные
            # Администратор
            hashed_pwd = generate_password_hash('admin123')
            cursor.execute("""
                INSERT INTO users (username, email, password, role)
                VALUES (%s, %s, %s, %s)
            """, ('admin', 'admin@example.com', hashed_pwd, 'admin'))

            # Магазины
            cursor.execute("""
                INSERT INTO shops (name, address)
                VALUES (%s, %s), (%s, %s)
            """, ('Главный магазин', 'ул. Центральная, 1', 'Филиал №2', 'ул. Заречная, 5'))

            # Товары
            cursor.execute("""
                INSERT INTO products (name, manufacturer, price, unit)
                VALUES (%s, %s, %s, %s), (%s, %s, %s, %s)
            """, ('Ноутбук', 'Lenovo', 45000, 'шт', 'Смартфон', 'Samsung', 32000, 'шт'))

            connection.commit()
            print("Таблицы успешно созданы и заполнены тестовыми данными!")

    except Error as e:
        print(f"Ошибка при подключении к MySQL: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("Соединение с MySQL закрыто")


if __name__ == '__main__':
    # Замените эти параметры на свои реальные данные для подключения
    DB_HOST = "192.168.0.158"
    DB_USER = "root"
    DB_PASSWORD = "300132"
    DB_NAME = "flask_auth"

    init_remote_db(DB_HOST, DB_USER, DB_PASSWORD, DB_NAME)
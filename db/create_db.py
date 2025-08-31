from application import create_app
from application.extensions import mysql
from werkzeug.security import generate_password_hash

app = create_app()

def init_db():
    with app.app_context():
        cur = mysql.connection.cursor()

        # 1. Удаляем таблицы в правильном порядке
        cur.execute("DROP TABLE IF EXISTS order_items")
        cur.execute("DROP TABLE IF EXISTS orders")
        cur.execute("DROP TABLE IF EXISTS products")
        cur.execute("DROP TABLE IF EXISTS shops")
        cur.execute("DROP TABLE IF EXISTS users")

        # 2. Создаем таблицу пользователей
        cur.execute("""
            CREATE TABLE users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                role ENUM('admin', 'moderator', 'operator') NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB
        """)

        # 3. Создаем таблицу магазинов
        cur.execute("""
            CREATE TABLE products (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                manufacturer VARCHAR(100) NOT NULL,
                price INT NOT NULL,
                unit ENUM('кг', 'шт') NOT NULL DEFAULT 'шт'
            ) ENGINE=InnoDB;
        """)

        # 4. Создаем таблицу товаров
        cur.execute("""
            CREATE TABLE products (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                manufacturer VARCHAR(100) NOT NULL,
                price INT NOT NULL
            ) ENGINE=InnoDB
        """)

        # 5. Создаем таблицу заказов
        cur.execute("""
            CREATE TABLE orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                shop_id INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (shop_id) REFERENCES shops(id)
            ) ENGINE=InnoDB
        """)

        # 6. Создаем таблицу элементов заказа
        cur.execute("""
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
        cur.execute("""
            INSERT INTO users (username, email, password, role)
            VALUES (%s, %s, %s, %s)
        """, ('admin', 'admin@example.com', hashed_pwd, 'admin'))

        # Магазины
        cur.execute("""
            INSERT INTO shops (name, address)
            VALUES (%s, %s), (%s, %s)
        """, ('Главный магазин', 'ул. Центральная, 1', 'Филиал №2', 'ул. Заречная, 5'))

        # Товары
        cur.execute("""
            INSERT INTO products (name, manufacturer, price)
            VALUES (%s, %s, %s), (%s, %s, %s)
        """, ('Ноутбук', 'Lenovo', 45000, 'Смартфон', 'Samsung', 32000))

        mysql.connection.commit()
        cur.close()
        print("База данных успешно инициализирована!")

if __name__ == '__main__':
    init_db()
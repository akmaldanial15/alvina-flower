import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'flower_shop.db')

def create_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create Tables
    cursor.execute('''
        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            price REAL NOT NULL,
            image TEXT NOT NULL,
            category TEXT NOT NULL,
            budget TEXT NOT NULL,
            use TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE orders (
            id TEXT PRIMARY KEY,
            total_amount REAL NOT NULL,
            status TEXT DEFAULT 'Processing',
            products TEXT NOT NULL,
            checkout_data TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE promotions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            discount TEXT,
            promo_code TEXT,
            discount_type TEXT DEFAULT 'percentage',
            discount_value REAL DEFAULT 0.0,
            start_date TEXT,
            end_date TEXT,
            applies_to TEXT DEFAULT 'all',
            target_categories TEXT,
            target_product_ids TEXT,
            banner_image TEXT,
            banner_color TEXT,
            max_uses INTEGER,
            times_used INTEGER DEFAULT 0,
            min_order_amount REAL DEFAULT 0.0,
            max_discount_amount REAL,
            sort_order INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT 1
        )
    ''')

    # Seed Data
    products = [
        ('Pastel Dream Bouquet', 'An extremely elegant and premium bouquet of pastel pink and white roses, softly lit. Perfect for an exquisite luxury gift.', 249.00, '/static/images/flower1.png', 'Bouquets', 'High', 'Anniversary'),
        ('Luxury Rose Box', 'A luxury white box containing perfect pastel pink roses and orchids, elegantly tied with a silk ribbon.', 189.00, '/static/images/flower2.png', 'Boxed Flowers', 'Medium', 'Birthday'),
        ('Spring Blossom Basket', 'A beautiful hand-woven basket filled with white and blush pink tulips, peonies, and subtle greenery.', 139.00, '/static/images/flower3.png', 'Baskets', 'Low', 'Get Well'),
        ('Alvina Signature Bloom', 'Our signature collection, an elegant mix of roses and delicate baby breath flowers in pastel pink wrap.', 299.00, '/static/images/flower1.png', 'Bouquets', 'High', 'Wedding'),
        ('Midnight Red Romance', 'A stunning classic bouquet of luxury deep red roses against an elegant studio background.', 329.00, '/static/images/mock_prod_1_1775095658176.png', 'Bouquets', 'High', 'Romance'),
        ('White Lily Elegance', 'A beautiful luxury boxed arrangement of pristine white lilies and purple orchids.', 189.00, '/static/images/mock_prod_2_1775095702622.png', 'Boxed Flowers', 'Medium', 'Anniversary'),
        ('Sunny Days Basket', 'A sunny, cheerful hand-woven basket filled with bright yellow sunflowers and white daisies.', 99.00, '/static/images/mock_prod_3_1775095820387.png', 'Baskets', 'Low', 'Get Well'),
        ('Pink Peony Delight', 'A romantic and elegant bouquet of soft pink peonies wrapped in premium korean-style floral paper.', 259.00, '/static/images/mock_prod_4_1775095851473.png', 'Bouquets', 'Medium', 'Birthday'),
        ('Vibrant Spring Mix', 'A vibrant mixed bouquet of bright orange tulips and yellow freesias, wrapped in rustic kraft paper.', 129.00, '/static/images/mock_prod_5_1775095868793.png', 'Bouquets', 'Low', 'Thank You'),
        ('Cool Blue Hydrangea', 'A delicate and elegant bouquet of pale blue hydrangeas and elegant white roses.', 219.00, '/static/images/mock_prod_6_1775095890913.png', 'Bouquets', 'Medium', 'New Baby'),
        ('Crimson Carnation Box', 'A dramatic and sophisticated arrangement of red carnations and dark greenery in an elegant black vase.', 149.00, '/static/images/mock_prod_1_1775095658176.png', 'Boxed Flowers', 'Medium', 'Anniversary'),
        ('Pure White Orchid Pot', 'A minimalist, elegant white phalaenopsis orchid plant in a modern dark grey ceramic pot.', 169.00, '/static/images/mock_prod_2_1775095702622.png', 'Plants', 'Low', 'Thank You'),
        ('Dreamy Peach Pastel', 'A dreamy, soft pastel bouquet featuring peach roses, dried lavender, and baby breath.', 189.00, '/static/images/mock_prod_3_1775095820387.png', 'Bouquets', 'Medium', 'Birthday'),
        ('Joyful Gerbera Mix', 'A cheerful and fun mix of bright pink gerbera daisies and yellow snapdragons.', 119.00, '/static/images/mock_prod_4_1775095851473.png', 'Baskets', 'Low', 'Get Well'),
        ('Classic Rose Basket', 'A basket filled with beautiful pink roses and fresh green eucalyptus leaves.', 149.00, '/static/images/flower3.png', 'Baskets', 'Low', 'Birthday'),
        ('Elegant Tulip Box', 'A luxurious white box showcasing a mix of pink and white tulips tied with a beautiful ribbon.', 179.00, '/static/images/mock_prod_5_1775095868793.png', 'Boxed Flowers', 'Medium', 'Anniversary'),
        ('Lively Sunflower Bouquet', 'A bouquet of pure sunshine featuring bright sunflowers, yellow roses, and daisies.', 109.00, '/static/images/mock_prod_6_1775095890913.png', 'Bouquets', 'Low', 'Graduation'),
        ('Pastel Paradise Box', 'A premium box of pastel-colored blooms perfectly curated for luxury gifting.', 199.00, '/static/images/flower2.png', 'Boxed Flowers', 'High', 'Romance'),
        ('Grand Anniversary Roses', 'A colossal bouquet of 50 red roses wrapped in elegant dark paper.', 499.00, '/static/images/mock_prod_1_1775095658176.png', 'Bouquets', 'High', 'Anniversary'),
        ('Rustic Wildflower Basket', 'A beautifully messy mix of wildflowers in a rustic basket, perfectly charming.', 89.00, '/static/images/mock_prod_3_1775095820387.png', 'Baskets', 'Low', 'Thank You'),
        ('Pure Love Orchids', 'Exquisite purple orchids delicately arranged in a modern vase for an elegant touch.', 159.00, '/static/images/mock_prod_2_1775095702622.png', 'Plants', 'Medium', 'Romance'),
        ('Golden Yellow Array', 'A vibrant burst of yellow tulips and yellow freesias, wrapped elegantly.', 129.00, '/static/images/mock_prod_4_1775095851473.png', 'Bouquets', 'Medium', 'Get Well'),
        ('Royal Purple Hydrangeas', 'Premium purple hydrangeas beautifully packed with white baby breath in a box.', 189.00, '/static/images/mock_prod_5_1775095868793.png', 'Boxed Flowers', 'High', 'Birthday'),
        ('Soft Pink Elegance', 'A perfectly balanced bouquet of pale pink roses and blue hydrangeas.', 239.00, '/static/images/mock_prod_6_1775095890913.png', 'Bouquets', 'High', 'Wedding')
    ]

    cursor.executemany('''
        INSERT INTO products (name, description, price, image, category, budget, use) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', products)

    import datetime
    today = datetime.date.today()
    next_month = today + datetime.timedelta(days=30)
    
    promotions = [
        (
            'Spring Special Sale!', 'Hand-picked beautiful blooms with limited time savings.', '15% OFF',
            'SPRING15', 'percentage', 15.0, str(today), str(next_month),
            'all', '', '', '', '#f8c8d8', 100, 0, 50.0, 50.0, 0, 1
        ),
        (
            'Luxury Rose Discount', 'Special RM50 off on our premium boxed arrangements.', 'RM50 OFF',
            'ROSE50', 'fixed', 50.0, str(today), str(next_month),
            'category', 'Boxed Flowers', '', '', '#d8a7b1', 50, 0, 150.0, 50.0, 1, 1
        )
    ]
    cursor.executemany('''
        INSERT INTO promotions (
            title, description, discount, promo_code, discount_type, discount_value, 
            start_date, end_date, applies_to, target_categories, target_product_ids, 
            banner_image, banner_color, max_uses, times_used, min_order_amount, 
            max_discount_amount, sort_order, is_active
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', promotions)

    conn.commit()
    conn.close()
    print("Database `flower_shop.db` created and seeded successfully!")

if __name__ == '__main__':
    create_db()

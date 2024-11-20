from flask import Flask, render_template, request, redirect, url_for
import requests
import mysql.connector
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import random
from decimal import Decimal
import math
import os
from flask import Flask, jsonify, request, render_template,redirect, url_for, session, request, jsonify, session
from mysql.connector import Error
import mysql.connector
from flask_session import Session
from datetime import date
from flask import Flask, render_template, request, redirect, url_for
import mysql.connector

app = Flask(__name__)
no_data = 0
app.config['SESSION_TYPE'] = 'filesystem'  # Or other storage like Redis
Session(app)

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'OOADP'
}
def get_db_connection():
    return mysql.connector.connect(
        host='localhost',      # Host where your database is running
        user='root',           # Your database username
        password='',  # Your database password
        database='OOADP'      # The database name
    )

#RECEIVE GOODS
class Meth:
    def __init__(self, order_id):
        self.order_id = order_id
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM ORDERS WHERE order_id = %s", (order_id,))
        self.order = cursor.fetchone()
        self.product_data = ''

    def update(self, order_id):
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        if request.method == 'POST' and self.order['status'] == 'Pending':
            cursor.execute("UPDATE ORDERS SET status = %s WHERE order_id = %s", ('Unloaded', order_id,))
            connection.commit()
            return redirect(url_for('order_details', order_id=order_id))
        
        if request.method == 'POST' and self.order['status'] == 'Unloaded':
            cursor.execute("UPDATE ORDERS SET status = %s WHERE order_id = %s", ('Assessed', order_id,))
            connection.commit()
            return redirect(url_for('order_details', order_id=order_id))
        
    def data(self, order_id):
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM ORDERITEMS WHERE order_id = %s", (order_id,))
        order_items = cursor.fetchall()
        # print(order_items)
        query = """
        SELECT *
        FROM ORDERITEMS oi
        JOIN PRODUCTS p ON oi.product_id = p.product_id
        WHERE oi.order_id = %s
        """

        cursor.execute(query, (order_id,))
        
        results = cursor.fetchall()

        query = """
        SELECT *
        FROM ORDERITEMS oi
        JOIN USER_PRODUCTS_DUP p ON oi.product_id = p.product_id
        WHERE oi.order_id = %s
        """

        cursor.execute(query, (order_id,))
        custom_results = cursor.fetchall()
        print("\n\nhi there\n\n")
        # print(custom_results)

        
        results = results + custom_results
        print(results)


        query = """
        SELECT p.product_name, p.product_id, p.category, p.price, oi.count AS total_quantity
        FROM ORDERITEMS oi
        JOIN PRODUCTS p ON oi.product_id = p.product_id
        WHERE oi.order_id = %s
        """
        cursor.execute(query, (order_id,))
        product_data = cursor.fetchall()

        query = """
        SELECT products.category, SUM(orderitems.count) AS total_quantity
        FROM orderitems
        JOIN products ON orderitems.product_id = products.product_id
        GROUP BY products.category;
        """
        
        cursor.execute(query)
        category = cursor.fetchall()  # Fetch the aggregated data

        self.order_items = order_items
        self.results = results
        self.product_data = product_data
        self.category = category

    def graph(self, order_id):
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        fixed_product_types = ['electronics', 'clothings', 'automobiles', 'staples']
        quantities = [0] * 4  # Initialize with zeros for each type

        for item in self.product_data:
            if item['category'] == 'electronics':
                quantities[0] = item['total_quantity']
            elif item['category'] == 'clothings':
                quantities[1] = item['total_quantity']
            elif item['category'] == 'automobiles':
                quantities[2] = item['total_quantity']
            elif item['category'] == 'staples':
                quantities[3] = item['total_quantity']

        graph_url = ''
        if self.order['status'] == 'Unloaded' or self.order['status'] == 'Assessed' or self.order['status'] == 'Approved' or self.order['status'] == 'Disapproved':
            plt.figure(figsize=(8, 6))
            plt.bar(fixed_product_types, quantities)
            plt.xlabel('Product Type')
            plt.ylabel('Quantity')
            plt.title('Quantity of Goods by Product Type')

            img = BytesIO()
            plt.savefig(img, format='png')
            img.seek(0)
            graph_url = base64.b64encode(img.getvalue()).decode('utf-8')
            img.close()
        self.graph_url = graph_url
        
    def defect(self, order_id):
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        cursor.execute('''
            SELECT COUNT(*) as c
            FROM final_product
            WHERE order_id = %s
        ''', (order_id,))
        count = cursor.fetchone()['c']
        damage_data = []
        ds = 0
        if count == 0:
            if self.order['status'] == 'Assessed' or self.order['status'] == 'Approved' or self.order['status'] == 'Disapproved':
                for product in self.product_data:
                    product_id = product['product_id']
                    product_name = product['product_name']
                    total_quantity = product['total_quantity']
                    total_price = product['total_quantity'] * product['price']
                    damaged_percent = random.randint(5, 11)
                    damaged_quantity = math.ceil(total_quantity * Decimal(damaged_percent) / Decimal(100))  # Convert damaged_percent to Decimal
                    damage_data.append({
                        'product_id' : product_id,
                        'product_name': product_name,
                        'total_quantity': total_quantity,
                        'total_price' : total_price,
                        'damaged_quantity': damaged_quantity,
                        'damaged_percent': round(damaged_percent, 2)
                    })
                    ds += damaged_percent

                for data in damage_data:
                    cursor.execute('''
                        INSERT INTO final_product (order_id, product_id, product_name, total_quantity, total_price, damaged_quantity, damaged_percent)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ''', (order_id, data['product_id'], data['product_name'], data['total_quantity'], data['total_price'], data['damaged_quantity'], data['damaged_percent']))

                if ds < 40:
                    cursor.execute("UPDATE ORDERS SET status = %s WHERE order_id = %s", ('Approved', order_id,))
                    connection.commit()
                else:
                    cursor.execute("UPDATE ORDERS SET status = %s WHERE order_id = %s", ('Disapproved', order_id,))
                    connection.commit()
        else:
            cursor.execute('''
            SELECT order_id, product_name, total_quantity, total_price, damaged_quantity, damaged_percent
            FROM final_product
            WHERE order_id = %s
        ''', (order_id,))
            rows = cursor.fetchall()
            for row in rows:
                damage_data.append({
                    'order_id': row['order_id'],
                    'product_name': row['product_name'],
                    'total_quantity': row['total_quantity'],
                    'total_price' : row['total_price'],
                    'damaged_quantity': row['damaged_quantity'],
                    'damaged_percent': row['damaged_percent']
                })

        self.damage_data = damage_data
        cursor.execute(''' select * from finAL_product join orders on orders.order_id = final_product.product_id;''')
        self.final_product = cursor.fetchall()
@app.route('/order/<int:order_id>', methods=['GET', 'POST'])
def order_details(order_id):
    obj = Meth(order_id)
    obj.update(order_id)
    obj.data(order_id)
    obj.graph(order_id)
    obj.defect(order_id)
    return render_template('order_details.html', order=obj.order, order_items=obj.order_items, results=obj.results, graph_url=obj.graph_url, damage_data=obj.damage_data)

#STORE INVENTORY
class BaseInventory:
    def __init__(self, db_connection):
        self.db_connection = db_connection
        self.cursor = db_connection.cursor(dictionary=True)

    def insert_order(self, order):
        raise NotImplementedError("Subclasses must implement this method")

    def get_data(self):
        raise NotImplementedError("Subclasses must implement this method")
class USAInventory(BaseInventory):
    def insert_order(self, order):
        query = """
        INSERT INTO USA_INV (CUSTOMER_ID, ORDER_ID, FROM_LOCATION, TO_LOCATION, ORDER_DATE, DELIVERY_DATE, PRODUCT_ID, PRODUCT_NAME, TOTAL_QUANTITY, DAMAGED_QUANTITY, COST) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.cursor.execute(query, (order['CUSTOMER_ID'], order['ORDER_ID'], order['FROM_LOCATION'], order['TO_LOCATION'], order['ORDER_DATE'], order['DELIVERY_DATE'], order['PRODUCT_ID'], order['PRODUCT_NAME'], order['TOTAL_QUANTITY'], order['DAMAGED_QUANTITY'], order['COST']))
    def get_data(self):
        query = "SELECT DISTINCT * FROM USA_INV"
        self.cursor.execute(query)
        return self.cursor.fetchall()  
class UKInventory(BaseInventory):
    def insert_order(self, order):
        query = """
        INSERT INTO UK_INV (CUSTOMER_ID, ORDER_ID, FROM_LOCATION, TO_LOCATION, ORDER_DATE, DELIVERY_DATE, PRODUCT_ID, PRODUCT_NAME, TOTAL_QUANTITY, DAMAGED_QUANTITY, COST) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.cursor.execute(query, (order['CUSTOMER_ID'], order['ORDER_ID'], order['FROM_LOCATION'], order['TO_LOCATION'], order['ORDER_DATE'], order['DELIVERY_DATE'], order['PRODUCT_ID'], order['PRODUCT_NAME'], order['TOTAL_QUANTITY'], order['DAMAGED_QUANTITY'], order['COST']))
    def get_data(self):
        query = "SELECT DISTINCT * FROM UK_INV"
        self.cursor.execute(query)
        return self.cursor.fetchall()
class FranceInventory(BaseInventory):
    def insert_order(self, order):
        query = """
        INSERT INTO FRANCE_INV (CUSTOMER_ID, ORDER_ID, FROM_LOCATION, TO_LOCATION, ORDER_DATE, DELIVERY_DATE, PRODUCT_ID, PRODUCT_NAME, TOTAL_QUANTITY, DAMAGED_QUANTITY, COST) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.cursor.execute(query, (order['CUSTOMER_ID'], order['ORDER_ID'], order['FROM_LOCATION'], order['TO_LOCATION'], order['ORDER_DATE'], order['DELIVERY_DATE'], order['PRODUCT_ID'], order['PRODUCT_NAME'], order['TOTAL_QUANTITY'], order['DAMAGED_QUANTITY'], order['COST']))

    def get_data(self):
        query = "SELECT DISTINCT * FROM FRANCE_INV"
        self.cursor.execute(query)
        return self.cursor.fetchall()   
class GermanyInventory(BaseInventory):
    def insert_order(self, order):
        query = """
        INSERT INTO GERMANY_INV (CUSTOMER_ID, ORDER_ID, FROM_LOCATION, TO_LOCATION, ORDER_DATE, DELIVERY_DATE, PRODUCT_ID, PRODUCT_NAME, TOTAL_QUANTITY, DAMAGED_QUANTITY, COST) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.cursor.execute(query, (order['CUSTOMER_ID'], order['ORDER_ID'], order['FROM_LOCATION'], order['TO_LOCATION'],  order['ORDER_DATE'], order['DELIVERY_DATE'], order['PRODUCT_ID'], order['PRODUCT_NAME'], order['TOTAL_QUANTITY'], order['DAMAGED_QUANTITY'], order['COST']))

    def get_data(self):
        query = "SELECT DISTINCT * FROM GERMANY_INV"
        self.cursor.execute(query)
        return self.cursor.fetchall() 
class RussiaInventory(BaseInventory):
    def insert_order(self, order):
        query = """
        INSERT INTO RUSSIA_INV (CUSTOMER_ID, ORDER_ID, FROM_LOCATION, TO_LOCATION, ORDER_DATE, DELIVERY_DATE, PRODUCT_ID, PRODUCT_NAME, TOTAL_QUANTITY, DAMAGED_QUANTITY, COST) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.cursor.execute(query, (order['CUSTOMER_ID'], order['ORDER_ID'], order['FROM_LOCATION'], order['TO_LOCATION'], order['ORDER_DATE'], order['DELIVERY_DATE'], order['PRODUCT_ID'], order['PRODUCT_NAME'], order['TOTAL_QUANTITY'], order['DAMAGED_QUANTITY'], order['COST']))

    def get_data(self):
        query = "SELECT DISTINCT * FROM RUSSIA_INV"
        self.cursor.execute(query)
        return self.cursor.fetchall() 
class ChennaiInventory(BaseInventory):
    def insert_order(self, order):
        query = """
        INSERT INTO CHENNAI_INV (CUSTOMER_ID, ORDER_ID, FROM_LOCATION, TO_LOCATION, ORDER_DATE, DELIVERY_DATE, PRODUCT_ID, PRODUCT_NAME, TOTAL_QUANTITY, DAMAGED_QUANTITY, COST) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.cursor.execute(query, (order['CUSTOMER_ID'], order['ORDER_ID'], order['FROM_LOCATION'], order['TO_LOCATION'], order['ORDER_DATE'], order['DELIVERY_DATE'], order['PRODUCT_ID'], order['PRODUCT_NAME'], order['TOTAL_QUANTITY'], order['DAMAGED_QUANTITY'], order['COST']))

    def get_data(self):
        query = "SELECT DISTINCT * FROM CHENNAI_INV"
        self.cursor.execute(query)
        return self.cursor.fetchall()
class MumbaiInventory(BaseInventory):
    def insert_order(self, order):
        query = """
        INSERT INTO MUMBAI_INV (CUSTOMER_ID, ORDER_ID, FROM_LOCATION, TO_LOCATION, ORDER_DATE, DELIVERY_DATE, PRODUCT_ID, PRODUCT_NAME, TOTAL_QUANTITY, DAMAGED_QUANTITY, COST) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.cursor.execute(query, (order['CUSTOMER_ID'], order['ORDER_ID'], order['FROM_LOCATION'], order['TO_LOCATION'], order['ORDER_DATE'], order['DELIVERY_DATE'], order['PRODUCT_ID'], order['PRODUCT_NAME'], order['TOTAL_QUANTITY'], order['DAMAGED_QUANTITY'], order['COST']))

    def get_data(self):
        query = "SELECT DISTINCT * FROM MUMBAI_INV"
        self.cursor.execute(query)
        return self.cursor.fetchall()   
class DelhiInventory(BaseInventory):
    def insert_order(self, order):
        query = """
        INSERT INTO DELHI_INV (CUSTOMER_ID, ORDER_ID, FROM_LOCATION, TO_LOCATION, ORDER_DATE, DELIVERY_DATE, PRODUCT_ID, PRODUCT_NAME, TOTAL_QUANTITY, DAMAGED_QUANTITY, COST) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.cursor.execute(query, (order['CUSTOMER_ID'], order['ORDER_ID'], order['FROM_LOCATION'], order['TO_LOCATION'], order['ORDER_DATE'], order['DELIVERY_DATE'], order['PRODUCT_ID'], order['PRODUCT_NAME'], order['TOTAL_QUANTITY'], order['DAMAGED_QUANTITY'], order['COST']))

    def get_data(self):
        query = "SELECT DISTINCT  * FROM DELHI_INV"
        self.cursor.execute(query)
        return self.cursor.fetchall()  
class KolkataInventory(BaseInventory):
    def insert_order(self, order):
        query = """
        INSERT INTO KOLKATA_INV (CUSTOMER_ID, ORDER_ID, FROM_LOCATION, TO_LOCATION, ORDER_DATE, DELIVERY_DATE, PRODUCT_ID, PRODUCT_NAME, TOTAL_QUANTITY, DAMAGED_QUANTITY, COST) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.cursor.execute(query, (order['CUSTOMER_ID'], order['ORDER_ID'], order['FROM_LOCATION'], order['TO_LOCATION'], order['ORDER_DATE'], order['DELIVERY_DATE'], order['PRODUCT_ID'], order['PRODUCT_NAME'], order['TOTAL_QUANTITY'], order['DAMAGED_QUANTITY'], order['COST']))
    def get_data(self):
        query = "SELECT DISTINCT * FROM KOLKATA_INV"
        self.cursor.execute(query)
        return self.cursor.fetchall() 
class BangaloreInventory(BaseInventory):
    def insert_order(self, order):
        query = """
        INSERT INTO BANGALORE_INV (CUSTOMER_ID, ORDER_ID, FROM_LOCATION, TO_LOCATION, ORDER_DATE, DELIVERY_DATE, PRODUCT_ID, PRODUCT_NAME, TOTAL_QUANTITY, DAMAGED_QUANTITY, COST) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.cursor.execute(query, (order['CUSTOMER_ID'], order['ORDER_ID'], order['FROM_LOCATION'], order['TO_LOCATION'], order['ORDER_DATE'], order['DELIVERY_DATE'], order['PRODUCT_ID'], order['PRODUCT_NAME'], order['TOTAL_QUANTITY'], order['DAMAGED_QUANTITY'], order['COST']))

    def get_data(self):
        query = "SELECT DISTINCT * FROM BANGALORE_INV"
        self.cursor.execute(query)
        return self.cursor.fetchall()   
class InventoryManager:
    def __init__(self, db_config):
        self.db_connection = mysql.connector.connect(**db_config)
        self.cursor = self.db_connection.cursor(dictionary=True)

    def fetch_orders(self):
        query = """
        SELECT 
            CUSTOMERS.CUSTOMER_ID, 
            ORDERS.ORDER_ID, 
            ORDERS.FROM_LOCATION, 
            ORDERS.TO_LOCATION, 
            ORDERS.ORDER_DATE, 
            ORDERS.DELIVERY_DATE, 
            FINAL_PRODUCT.PRODUCT_ID, 
            FINAL_PRODUCT.PRODUCT_NAME, 
            FINAL_PRODUCT.TOTAL_QUANTITY,
            FINAL_PRODUCT.DAMAGED_QUANTITY, 
            FINAL_PRODUCT.TOTAL_PRICE AS COST
        FROM CUSTOMERS
        JOIN ORDERS ON CUSTOMERS.CUSTOMER_ID = ORDERS.CUSTOMER_ID
        JOIN FINAL_PRODUCT ON ORDERS.ORDER_ID = FINAL_PRODUCT.ORDER_ID
        WHERE ORDERS.STATUS = 'Approved';
        """
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def insert_into_inventory(self, order):
        # Dynamically choose the correct inventory subclass based on the `TO_LOCATION`
        inventory_classes = {
            'USA': USAInventory,
            'UK': UKInventory,
            'FRANCE': FranceInventory,
            'GERMANY': GermanyInventory,
            'RUSSIA': RussiaInventory,
            'CHENNAI': ChennaiInventory,
            'MUMBAI': MumbaiInventory,
            'DELHI': DelhiInventory,
            'KOLKATA': KolkataInventory,
            'BANGALORE': BangaloreInventory
        }
        
        # Select the correct subclass based on the order's destination (TO_LOCATION)
        inventory_class = inventory_classes.get(order['TO_LOCATION'])
        if inventory_class:
            inventory = inventory_class(self.db_connection)
            inventory.insert_order(order)

    def get_inventory_data(self):
        # Collect data from all inventories (regions)
        inventory_classes = {
            'USA': USAInventory,
            'UK': UKInventory,
            'FRANCE': FranceInventory,
            'GERMANY': GermanyInventory,
            'RUSSIA': RussiaInventory,
            'CHENNAI': ChennaiInventory,
            'MUMBAI': MumbaiInventory,
            'DELHI': DelhiInventory,
            'KOLKATA': KolkataInventory,
            'BANGALORE': BangaloreInventory
        }

        data = {}
        for region, inventory_class in inventory_classes.items():
            inventory = inventory_class(self.db_connection)
            data[region] = inventory.get_data()

        return data

    def commit_changes(self):
        self.db_connection.commit()

    def close_connection(self):
        self.cursor.close()
        self.db_connection.close()
@app.route('/inventory', methods=['GET', 'POST'])
def inventory():
    db_config = {
        'host': 'localhost',
        'user': 'root',
        'password': '',
        'database': 'OOADP'
    }    
    inventory_manager = InventoryManager(db_config)

    try:
        orders_data = inventory_manager.fetch_orders()
        for order in orders_data:
            inventory_manager.insert_into_inventory(order)
        inventory_manager.commit_changes()
        data = inventory_manager.get_inventory_data()

    finally:
        inventory_manager.close_connection()

    return render_template('inventory.html', data=data)

class InventoryMonitor(Meth):
    def __init__(self, db_config):
        self.db_config = db_config
        inventory_tables = [
            'USA_INV', 'UK_INV', 'FRANCE_INV', 'RUSSIA_INV',
            'GERMANY_INV', 'CHENNAI_INV', 'MUMBAI_INV', 'DELHI_INV',
            'KOLKATA_INV', 'BANGALORE_INV'
        ]

        connection = mysql.connector.connect(**self.db_config)
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT ORDER_ID FROM ORDERS;")
        ids =  cursor.fetchall()
        self.t = []
        self.u = []
        for i in ids:
            order_id = i['ORDER_ID']
            super().__init__(order_id)   
            self.data(order_id)
            self.defect(order_id)
            self.t.append(self.category)    
            self.u.append(self.final_product)       

    def fetch_inventory_data(self):
        connection = mysql.connector.connect(**self.db_config)
        cursor = connection.cursor(dictionary=True)
        inventory_tables = [
            'USA_INV', 'UK_INV', 'FRANCE_INV', 'RUSSIA_INV',
            'GERMANY_INV', 'CHENNAI_INV', 'MUMBAI_INV', 'DELHI_INV',
            'KOLKATA_INV', 'BANGALORE_INV'
        ]
        inventory_data = {}
        for table in inventory_tables:
            query = f"SELECT SUM(TOTAL_QUANTITY) AS total_quantity FROM {table};"
            cursor.execute(query)
            result = cursor.fetchone()
            total_quantity = result['total_quantity'] if result['total_quantity'] else 0
            inventory_data[table] = total_quantity
        cursor.close()
        connection.close()
        return inventory_data

    def generate_bar_graph(self, inventory_data):
        inventories = list(inventory_data.keys())
        quantities = list(inventory_data.values())
        plt.figure(figsize=(10, 6))
        plt.bar(inventories, quantities, color='skyblue')
        plt.xlabel('Inventory Location')
        plt.ylabel('Total Product Quantity')
        plt.title('Product Quantities in Each Inventory')
        plt.xticks(rotation=45, ha='right')
        img = BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        plot_url = base64.b64encode(img.getvalue()).decode('utf8')
        return plot_url
    
    def plot_inventory_pie(self):
        category_data = self.t[-1]
        categories = [item['category'] for item in category_data]
        quantities = [item['total_quantity'] for item in category_data]
        fig, ax = plt.subplots()
        ax.pie(quantities, labels=categories, autopct='%1.1f%%', startangle=90)
        ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
        static_folder = os.path.join(os.getcwd(), 'static')  # Get the path to the static folder
        if not os.path.exists(static_folder):  # Ensure the static folder exists
            os.makedirs(static_folder)
        
        image_path = os.path.join(static_folder, 'inventory_pie_chart.png')  # Full path to save image
        plt.savefig(image_path)
        plt.close()
        return image_path
@app.route('/monitoring', methods=['GET'])
def monitoring():
    monitor = InventoryMonitor(db_config)
    inventory_data = monitor.fetch_inventory_data()
    plot_url = monitor.generate_bar_graph(inventory_data)
    image_path = monitor.plot_inventory_pie()
    return render_template('monitor.html', k = monitor.product_data, plot_url=plot_url, image_path=image_path)

class Shipment():
    def __init__(self, db_config):
        self.db_config = db_config
        self.location_table_map = {
            "CHENNAI": "CHENNAI_INV",
            "MUMBAI": "MUMBAI_INV",
            "DELHI": "DELHI_INV",
            "KOLKATA": "KOLKATA_INV",
            "BANGALORE": "BANGALORE_INV",
            "USA" : "USA_INV",
            "UK" : "UK_INV",
            "FRANCE" : "FRANCE_INV",
            "GERMANY" : "GERMANY_INV",
            "RUSSIA" : "RUSSIA_INV"
        }
        connection = mysql.connector.connect(**self.db_config)
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM ORDERS")
        orders = cursor.fetchall()
        cursor.close()
        connection.close()
        self.orders = orders

    def fetch(self, floc, tloc, date):
        connection = mysql.connector.connect(**self.db_config)
        cursor = connection.cursor(dictionary=True)
        table_name = self.location_table_map.get(tloc.upper())
        if not table_name:
            return f"Error: No inventory table found for location '{tloc}'"

        connection = mysql.connector.connect(**self.db_config)
        cursor = connection.cursor(dictionary=True)

        try:
            query = f"""
                SELECT DISTINCT * 
                FROM {table_name} WHERE FROM_LOCATION = '{floc}'
            """
            cursor.execute(query)
            results = cursor.fetchall()
            return results

        except mysql.connector.Error as err:
            print(f"Error: {err}")
            return []

        finally:
            cursor.close()
            connection.close()

    def veh(self, floc, tloc, date):
        connection = mysql.connector.connect(**self.db_config)
        cursor = connection.cursor(dictionary=True)
        try:
            query = """
            SELECT *
            FROM vehicles
            WHERE FROM_LOCATION = %s
              AND TO_LOCATION = %s
            """
            cursor.execute(query, (floc, tloc, ))
            v = cursor.fetchall()
            for i in v:
                print(i, i['OCCUPIED'])
                if i['OCCUPIED'] == 'OCCUPIED':
                    print(1)
                    query = """
                        SELECT *
                        FROM vehicles
                        WHERE FROM_LOCATION = %s
                        AND TO_LOCATION = %s AND OCCUPIED = %s
                        """
                    cursor.execute(query, (floc, tloc, "OCCUPIED", ))
                    return cursor.fetchall()
            return v
        except mysql.connector.Error as e:
            print(f"Error: {e}")
            return []
        finally:
            cursor.close()
            connection.close()

@app.route('/shipping', methods=['GET'])
def shipping():
    ship = Shipment(db_config)
    return render_template('shipping.html', orders=ship.orders)

@app.route('/locaction/<string:floc>/<string:tloc>/<string:date>', methods=['GET'])
def location(floc, tloc, date):
    # Create an instance of Shipment
    ship = Shipment(db_config)
    session['floc'] = floc
    session['tloc'] = tloc
    session['date'] = date
    print(session.get('floc'), session.get('tloc'), session.get('date'))
    res = ship.fetch(floc, tloc, date)
    vd = ship.veh(floc, tloc, date)
    # Render the template with the results
    return render_template('location.html', res=res, vd = vd)

class assign():
    def __init__(self, db_config, vehicle_id):
        self.db_config = db_config
        self.vehicle_id = vehicle_id
    
    def assign_func(self):
        connection = mysql.connector.connect(**self.db_config)
        cursor = connection.cursor(dictionary=True)
        query = """
            UPDATE vehicles SET OCCUPIED = %s
            WHERE VEHICLE_ID = %s
            """
        cursor.execute(query, ("OCCUPIED", self.vehicle_id, ))
        connection.commit()

        ship = Shipment(db_config)
        floc = session.get('floc')
        tloc = session.get('tloc')
        date = session.get('date')
        res = ship.fetch(floc, tloc, date)
        vd = ship.veh(floc, tloc, date)
        cursor.close()
        connection.close()

        return res, vd
    
    def map(self):
        floc = session.get('floc')
        tloc = session.get('tloc')
        image_filename = f"{floc}_{tloc}.png"
        return image_filename
    
    def weat(self):
        weather_api_key = '2f44aef9a2277fe209f75cfbaa66025a'  # Replace with your OpenWeatherMap API key

        locations_dict = {
            "CHENNAI": "Chennai, India",
            "MUMBAI": "Mumbai, India",
            "DELHI": "New Delhi, India",
            "BANGALORE": "Bangalore, India",
            "KOLKATA": "Kolkata, India",
            "USA": "New York, USA",
            "UK": "London, UK",
            "FRANCE": "Paris, France",
            "GERMANY": "Berlin, Germany",
            "RUSSIA": "Moscow, Russia"
        }

        def fetch_weather_data(location):
            weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={weather_api_key}&units=metric"
            response = requests.get(weather_url)

            if response.status_code != 200:
                print(f"Error fetching weather data for {location}: {response.status_code}")
                return None
            else:
                return response.json()

        floc = session.get('floc').strip()
        tloc = session.get('tloc').strip()
        print(floc, tloc)
        
        from_location = floc  # Replace with dynamic input if needed
        to_location = tloc   # Replace with dynamic input if needed
        from_location_str = locations_dict.get(from_location)
        to_location_str = locations_dict.get(to_location)

        if not from_location_str or not to_location_str:
            print("One of the locations is not in the dictionary.")
        else:
            from_weather_data = fetch_weather_data(from_location_str)
            to_weather_data = fetch_weather_data(to_location_str)

            if from_weather_data and to_weather_data:
                # Extract weather data for the 'from' location
                from_temp = from_weather_data['main']['temp']
                from_humidity = from_weather_data['main']['humidity']
                from_rain = from_weather_data.get('rain', {}).get('1h', 0)  # Default to 0 if no rain
                from_cloud_coverage = from_weather_data['clouds'].get('all', 0)  # Cloud coverage in percentage
                from_weather_status = from_weather_data['weather'][0]['description']  # Weather status

                # Extract weather data for the 'to' location
                to_temp = to_weather_data['main']['temp']
                to_humidity = to_weather_data['main']['humidity']
                to_rain = to_weather_data.get('rain', {}).get('1h', 0)  # Default to 0 if no rain
                to_cloud_coverage = to_weather_data['clouds'].get('all', 0)  # Cloud coverage in percentage
                to_weather_status = to_weather_data['weather'][0]['description']  # Weather status

                # Calculate averages
                avg_temp = (from_temp + to_temp) / 2
                avg_humidity = (from_humidity + to_humidity) / 2
                avg_rain = (from_rain + to_rain) / 2
                avg_cloud_coverage = (from_cloud_coverage + to_cloud_coverage) / 2

                # Combine the weather statuses from both locations into a single summary
                combined_weather_status = f"From: {from_weather_status}, To: {to_weather_status}"

                # Final output
                t = avg_temp
                h = avg_humidity
                r = avg_rain
                cc = avg_cloud_coverage
                ws = combined_weather_status  # Return weather status summary

                return t, h, r, cc, ws



@app.route('/assign_vehicle', methods=['POST'])
def assign_vehicle():
    vehicle_id = request.form.get('vehicle_id')
    obj = assign(db_config, vehicle_id)
    res, vd = obj.assign_func()    
    ifn = obj.map()
    weather = obj.weat()
    print(weather)
    return render_template('location.html', res = res, vd = vd, ifn = ifn, weather = weather)

@app.route('/admin')
def home():
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM ORDERS")
    orders = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('admin.html', orders=orders)

# USER USER USER USER USER USER USER USERUSER USERUSER USERUSER USERUSER USERUSER USERUSER USERUSER USERUSER USERUSER USERUSER USERUSER USERUSER USERUSER USERUSER USERUSER USER

@app.route('/')
def index():
    return render_template('index.html')  # Renders an HTML page


@app.route('/about')
def about():
    return render_template('about.html') 

# ORDER PRODUCT CLICKING.

@app.route("/yourDetails", methods=["POST"])
def yourDetails():
    if request.method == "POST":
        # Get JSON data from the request
        form_data = request.get_json()

        # Extract data from the JSON object
        from_location = form_data.get("from")
        to_location = form_data.get("to")
        delivery_date = form_data.get("deliverydate")
        price = form_data.get("total_price")
        order_date = form_data.get("today_date")
        user_id = session.get('user_id')
        pending = "Pending"

        connection = get_db_connection()
        cursor = connection.cursor()

        # INSERT the data into the Orders table

        insert_order_query = """
            INSERT INTO Orders (from_location, to_location, delivery_date, price, order_date, customer_id, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_order_query, (from_location, to_location, delivery_date, price, order_date, user_id, "Pending"))
        connection.commit()

        order_id = cursor.lastrowid

        # SELECT ALL ITEMS IN THE CART
        cursor.execute("""
        SELECT p.product_id, c.count
        FROM Cart c
        JOIN Products p ON c.product_id = p.product_id
        WHERE c.user_id = %s
        
        """, (user_id,))
        
        cart_items = cursor.fetchall()

        # Then, get the user-submitted products from the user_products table
        cursor.execute("""
            SELECT up.product_id, up.count
            FROM user_products up
            WHERE up.user_id = %s
        """, (user_id,))

        user_products = cursor.fetchall()
        combined_products = cart_items + user_products
        
        # Insert order items into OrderItems table

        insert_order_items_query = """
        INSERT INTO OrderItems (order_id, product_id, count)
        VALUES (%s, %s, %s)
        """
        for product in combined_products:
            cursor.execute(insert_order_items_query, (order_id, product[0], product[1]))
        
        connection.commit()

        #DELETE THE CART

        delete_query = """
        DELETE FROM cart  WHERE user_id = %s 
        """
        cursor.execute(delete_query, (user_id, ))
        connection.commit()
        delete_query = """
        DELETE FROM user_products  WHERE user_id = %s 
        """
        cursor.execute(delete_query, (user_id, ))
        connection.commit()

        

        cursor.close()
        connection.close()

        # Log received data for debugging
        print(f"From: {from_location}, To: {to_location}, Delivery Date: {delivery_date}, Total Price: {price}, Today's Date: {order_date}")

        # You can process the data and perform necessary operations like database queries
        # For now, just return a success message
        return jsonify({'success': True})

# UPDATE THE CART TABLE'S COUNT ON EVERY PLUS OR MINUS
@app.route('/update-count', methods=['POST'])
def update_count():
    try:
        # Parse the incoming data
        data = request.json
        product_id = data.get('product_id')
        count = data.get('count')
        user_id = session.get('user_id')  # Ensure the user ID is stored in the session

        if not user_id:
            return jsonify({'error': 'User not logged in'}), 401

        # Get a database connection and cursor
        connection = get_db_connection()
        cursor = connection.cursor()

        # Check if the cart entry exists for the user and product
        select_query = """
        SELECT cart_id FROM cart  WHERE user_id = %s AND product_id = %s
        """
        cursor.execute(select_query, (user_id, product_id))
        cart_item = cursor.fetchone()
        
        # Check if the product in user_products
        select_query = """
        SELECT product_id FROM user_products  WHERE user_id = %s AND product_id = %s
        """
        cursor.execute(select_query, (user_id, product_id))
        user_item = cursor.fetchone()
        print(cart_item)
        print(user_item)
        if cart_item:
            # Update the quantity if the entry exists
            update_query = """
            UPDATE cart SET count =  %s WHERE user_id = %s AND product_id = %s
            """
            cursor.execute(update_query, (count, user_id, product_id))
            connection.commit()
            return jsonify({'success': True}), 200
        elif user_item:
            update_query = """
            UPDATE user_products SET count =  %s WHERE user_id = %s AND product_id = %s
            """
            cursor.execute(update_query, (count, user_id, product_id))
            connection.commit()

            update_query = """
            UPDATE user_products_dup SET count =  %s WHERE user_id = %s AND product_id = %s
            """
            cursor.execute(update_query, (count, user_id, product_id))
            connection.commit()

            return jsonify({'success': True}), 200

        else:
            # If no entry exists, return an error
            return jsonify({'error': 'Cart item not found'}), 404
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': 'An error occurred while updating the cart'}), 500
    finally:
        # Always close the connection
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()

# CUSTOM PRODUCT SUBMISSION
@app.route('/submit_product', methods=['POST'])
def submit_product():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401  # Return an error if not logged in

    user_id = session['user_id']
    product_name = request.form.get('product_name')
    category = request.form.get('category')
    count = request.form.get('product_count')
    image = request.files['image']
    
    print(category)
    # Define the default prices based on categories
    category_price_map = {
        'automobiles': 12500,  # Middle of 10000 - 15000
        'clothings': 750,      # Middle of 500 - 1000
        'electronics': 3500,  # Middle of 2000 - 5000
        'staples': 125        # Middle of 50 - 200
    }
    print(category_price_map)
    # Check if the category is valid and assign a price
    if category not in category_price_map:
        return jsonify({'error': 'Invalid category'}), 400
    
    price = category_price_map[category.lower()]
    print(count)
    # Save the image to the static directory (or wherever you handle uploads)
    image_filename = f"static/img/{category}/{image.filename}"
    image.save(image_filename)

    try:
        # Insert the submitted product into the user_products table
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO user_products (user_id, product_name, category, price, image, count)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, product_name, category, price, image_filename, count))

        # INSERT INTO USER_PRODUCTS DUPLICATE TABLE
        cursor.execute("""
            INSERT INTO user_products_dup (user_id, product_name, category, price, image, count)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, product_name, category, price, image_filename, count))
        print(product_name)
        # Select the product id
        cursor.execute("""
                    SELECT * 
        FROM user_products
        ORDER BY product_id DESC
        LIMIT 1;""")
        product_id = cursor.fetchone()
        
        cursor.execute("""
            INSERT INTO products (product_id, customer_id, product_name, category, price, image)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (int(product_id[0]), user_id, product_name, category, price, image_filename))

        connection.commit()
        cursor.close()
        connection.close()

        return jsonify({'success': True}), 200  # Return success response

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': 'An error occurred while submitting your product'}), 500


# TO DISPLAY THE CART PAGE WHEN IT IS LOADED 
@app.route('/cart')
def cart():
    user_id = session.get('user_id')  # Assuming user_id is stored in the session

    if not user_id:
        return redirect(url_for('login'))  # Redirect to login if the user is not logged in

    connection = get_db_connection()
    cursor = connection.cursor()

    # Remove items with count = 0 from the cart
    cursor.execute("""
        DELETE FROM Cart 
        WHERE user_id = %s AND count = 0
    """, (user_id,))
    connection.commit()  # Commit the changes to remove the items

    # Remove items with count = 0 from the user_products
    cursor.execute("""
        DELETE FROM user_products
        WHERE user_id = %s AND count = 0
    """, (user_id,))
    connection.commit()  # Commit the changes to remove the items

    # Remove items with count = 0 from the user_products_dup
    cursor.execute("""
        DELETE FROM user_products_dup
        WHERE user_id = %s AND count = 0
    """, (user_id,))
    connection.commit()  # Commit the changes to remove the items

    # Fetch items in the cart for the logged-in user and also fetch user products
    cursor.execute("""
        SELECT p.product_id, p.product_name, p.price, p.image, c.count
        FROM Cart c
        JOIN Products p ON c.product_id = p.product_id
        WHERE c.user_id = %s
        
    """, (user_id,))
    
    cart_items = cursor.fetchall()

    # Then, get the user-submitted products from the user_products table
    cursor.execute("""
        SELECT up.product_id, up.product_name, up.price, up.image, up.count
        FROM user_products up
        WHERE up.user_id = %s
    """, (user_id,))

    user_products = cursor.fetchall()
    combined_products = cart_items + user_products
    print(combined_products)
    cursor.close()
    connection.close()

    # Prepare data for the template
    products_in_cart = [
        {
            "product_id": item[0],
            "product_name": item[1],
            "price": item[2],
            "image": item[3],
            "count": item[4]
        }
        for item in combined_products
    ]

    return render_template('cart.html', products=products_in_cart)




# ADD TO CART FUNCTIONALITY
@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    data = request.get_json()
    product_id = data.get('product_id')
    count = data.get('count')
    user_id = session.get('user_id')  # Assuming user is logged in and their user_id is stored in session
    if not user_id:
        return jsonify({"error": "User is not logged in"}), 401  # Return an error if the user is not logged in

    # Connect to the database
    connection = get_db_connection()
    cursor = connection.cursor()

   
    # Check if the product is already in the user's cart
    cursor.execute("SELECT count FROM Cart WHERE user_id = %s AND product_id = %s", (user_id, product_id))
    existing_cart_item = cursor.fetchone()

    if existing_cart_item:
        # If the product is already in the cart, update the count
        new_count = existing_cart_item[0] + count  # Add the new count to the existing count
        cursor.execute(
            "UPDATE Cart SET count = %s WHERE user_id = %s AND product_id = %s", 
            (new_count, user_id, product_id)
        )
    else:
        # If the product is not in the cart, insert a new record
        cursor.execute(
            "INSERT INTO Cart (user_id, product_id, count) VALUES (%s, %s, %s)", 
            (user_id, product_id, count)
        )
    
    connection.commit()
    cursor.close()
    connection.close()

    return jsonify({"success": True}), 200


# TO RENDER THE SHOP PAGE WHEN IT IS LOADED
@app.route('/shop')
def shop():
    # Fetch product data from the database
    connection = get_db_connection()
    cursor = connection.cursor()
    user_id = session.get('user_id')  
    cursor.execute("SELECT product_id, product_name, price, image FROM Products where customer_id = %s or customer_id is NULL", (user_id, ))

    
    # Fetch all rows from the query
    products = [
        {
            "product_id": row[0],
            "product_name": row[1],
            "price": row[2],
            "image": row[3]  # Assuming images are in static/img
        }
        for row in cursor.fetchall()
    ]
    
    # Print the products
    print(products)

    # No need to call fetchall() again here, since we've already fetched all rows.
    # Instead, you can just iterate over the `products` list
    for product in products:
        print(product["product_name"])

    cursor.close()
    
    # Render the template with the fetched products
    return render_template('shop.html', products=products)


# TO RENDER THE CONTACT PAGE WHEN IT IS LOADED
@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        # Handle form data here
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')
        
        # Send email or process the form data
        return jsonify({'success': True})  # Or process your email sending
    return render_template('contact.html')

# RENDER SIGNUP PAGE
@app.route('/signupPage')
def signupPage():
    return render_template('signup.html') 

# RENDER SIGNUP PAGE ON WRONG SIGNIN
@app.route('/reEnter', methods=['GET'])
def reEnter():
    # Render the Sign In form (could be a template)
    return render_template('signup.html')

# RENDER THE USER PROFILE PAGE
@app.route('/user', methods=['GET'])
def user():
    # Assuming the user is logged in and user_id is available in the session
    user_id = session.get('user_id')  

    if not user_id:
        return redirect(url_for('signupPage'))  # Redirect to login if user is not logged in
    
    # Connect to the database and fetch user details
    connection = get_db_connection()  # Replace with your DB connection method
    cursor = connection.cursor()
    print(user_id)
    # Query to fetch user data from the database
    cursor.execute("""
        SELECT customer_id, customer_name, email, phone_number, address, created_at, gender
        FROM customers
        WHERE customer_id = %s
    """, (user_id,))

    user_data = cursor.fetchone()  # Fetch the user's data
    print(user_data)
    # Close the cursor and connection
    cursor.close()
    connection.close()

    # If no user data found, redirect to login
    if not user_data:
        return redirect(url_for('login'))

    # Send the data to the template
    return render_template('user.html', user=user_data)


# FOR LOGOUT
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# PUTS THE USER DETAILS IN USERS TABLE ON SIGNUP
@app.route('/signup', methods=['POST'])
def signup():
    # Get data from the form
    username = request.form.get('user')
    email = request.form.get('email')
    password = request.form.get('password')
    gender = request.form.get('gender')
    phone = request.form.get('phone')
    address = request.form.get('address')

    # Print the received data for debugging
    print(f"Username: {username}, Email: {email}, Password: {password}, Phone: {phone}, Address: {address}")

    if not username or not email or not password:
        return "Error: Missing form data", 400  # Return a 400 error if any field is missing

    try:
        # Establish database connection
        connection = get_db_connection()
        cursor = connection.cursor()

        # Prepare the SQL query to insert data into the users table
        insert_query = """
        INSERT INTO customers (customer_name, email, password, phone_number, address, gender)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (username, email, password, phone, address, gender))

        # Commit the transaction to the database
        connection.commit()

        # Close the cursor and connection
        cursor.close()
        connection.close()

        # After successfully signing up, redirect to the Sign In form
        return redirect(url_for('reEnter'))

    except Error as e:
        print(f"Error: {e}")
        return "An error occurred while processing your request", 500

# ON CORRECT SIGNIN, GOES TO THE INDEX PAGE
@app.route('/signin', methods=['POST'])
def signin():
    # Get the data entered in the form
    email = request.form.get('email')
    password = request.form.get('password')

    # Print the received data for debugging
    print(f"Email: {email}, Password: {password}")

    if not password or not email:
        print("Password and Email are required.")
        return redirect(url_for('reEnter'))  # Redirect back to the Sign In page if input is missing

    try:
        # Establish database connection
        connection = get_db_connection()
        cursor = connection.cursor()

        # Prepare the SQL query to check if the user exists
        select_query = "SELECT * FROM customers WHERE email = %s AND password = %s"
        cursor.execute(select_query, (email, password))

        user = cursor.fetchone()  # Fetch the first matching result
        print(user)

        # If user exists, proceed to index page
        if user:
            # Store user details in the session
            session['user_id'] = user[0]
            print(session['user_id'])
            session['email'] = user[2]   # Assuming the email is at index 1
            session['name'] = user[1]  # Assuming the username is at index 0
            session['phone'] = user[3]
            session['address'] = user[4]
            session['logged_in'] = True
            cursor.close()
            connection.close()
            return redirect(url_for('index'))  # Redirect to the index page if credentials match
        else:
            print("Invalid credentials. Please try again.")
            cursor.close()
            connection.close()
            return 'Invalid credentials', 401  # Send 401 Unauthorized error if credentials don't match

    except Error as e:
        print(f"Error: {e}")
        return "An error occurred while processing your request", 500
    
# FOR EMAIL
from flask import Flask,render_template
from flask_mail import Mail,Message



app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'skshakith@gmail.com'  # Replace with your email
app.config['MAIL_PASSWORD'] = 'nads hthl mhuw hxxg'  # Replace with your app password
app.config['MAIL_DEFAULT_SENDER'] = 'vetrimaran@gmail.com'  # Replace with your email

mail = Mail(app)

# Route to send email
@app.route("/send_email", methods=["POST"])
def send_email():
    # Retrieve the JSON data from the request
    data = request.get_json()

    if not data or 'order_id' not in data:
        return jsonify({"status": 400, "message": "Invalid request, 'order_id' is missing"}), 400

    order_id = data.get('order_id')
    
    # Connect to the database
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()

    try:
        # Fetch recipient email
        cursor.execute("select email from customers where customer_id = (SELECT customer_id FROM orders WHERE order_id = %s)", (order_id,))

        recipient_email = cursor.fetchone()
        recipient_email = recipient_email[0]
        
        if not recipient_email:
            return jsonify({"status": 400, "message": "Recipient email not found in the database"}), 400
       # Fetch product details
        cursor.execute("SELECT product_id, total_quantity FROM final_product WHERE order_id = %s", (order_id,))
        products = cursor.fetchall()  # List of dictionaries [{'product_id': 1, 'total_quantity': 10}, ...]

        # Extract product_ids into a tuple
        product_ids = tuple(product[0] for product in products)
        print(product_ids)
        # Ensure product_ids is not empty to avoid SQL syntax errors
        if not product_ids:
            return jsonify({"status": 400, "message": "No products found for this order"}), 400

        # Fetch product names using the product_ids tuple
        placeholders = ', '.join(['%s'] * len(product_ids))
        query = f"SELECT product_name FROM products WHERE product_id IN ({placeholders})"

        # Execute the query with product_ids unpacked
        cursor.execute(query, product_ids)
        product_names = cursor.fetchall()  # List of tuples [('Product1',), ('Product2',), ...]
        print(product_names)
        # Map product names to their quantities
        string = ""
        for i in range(len(products)):
            string += " The Product " + str([product_names[i][0]]) +  " of count " + str(products[i][1]) + "\n" # product_names[i][0] is the product_name
        
        
        # Email content
        subject = "From Zay Logistics"
        body = f"Your orders of \n\n {string} \nhave been delivered successfully."
        print(body)
        # Create and send the email
        msg = Message(subject, recipients=[recipient_email])
        msg.body = body

        mail.send(msg)
        # STORE IN THE EMAIL_SENT_ORDERS TABLE
        # Fetch the order to be deleted
        cursor.execute("SELECT * FROM orders WHERE order_id = %s", (order_id,))
        delete_orders = cursor.fetchone()
        # cursor.execute("SELECT * FROM orderitems WHERE order_id = %s", (order_id,))
        # delete_order_items = cursor.fetchone()

        print(delete_orders)
        # Ensure the order exists before proceeding
        if delete_orders:
            # Prepare the insert query for email_sent_orders
            insert_query = """
                INSERT INTO email_sent_orders (
                    order_id, customer_id, from_location, to_location, order_date, status, DELIVERY_DATE, PRICE
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """

            # Extract the values from the delete_orders record
            values = (
                delete_orders[0],
                delete_orders[1],
                delete_orders[2],
                delete_orders[3],
                delete_orders[4],
                delete_orders[5],
                delete_orders[6],
                delete_orders[7]
            )

            # Insert the record into email_sent_orders
            cursor.execute(insert_query, values)
            
            # Commit the changes
            connection.commit()
            cursor.execute("SELECT * FROM orderitems WHERE order_id = %s", (order_id,))
            delete_order_items = cursor.fetchall()  # Use fetchall() to retrieve multiple rows

            for item in delete_order_items:
                cursor.execute("""
                    INSERT INTO email_sent_orderitems (order_id, product_id, COUNT)
                    VALUES (%s, %s, %s)
                """, (item[1], item[2], item[3]))  # Access the tuple elements using indexing

            print("Order inserted into email_sent_orders successfully.")
        else:
            print("Order not found in orders table.")

        print("Deleting order_id:", order_id[0])
        #Deleting after the email is sent
        # Need to create a duplicate orders table for analytic purpose
        cursor.execute("DELETE FROM ORDERITEMS WHERE order_id = %s", (order_id,))
        connection.commit()
        cursor.execute("DELETE FROM ORDERS WHERE order_id = %s", (order_id,))
        connection.commit()
        return jsonify({"status": 200, "message": "Email sent successfully!"}), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": 500, "message": "Failed to send email"}), 500

    finally:
        cursor.close()
        connection.close()


# Temporary route to set session email (for testing)
@app.route("/set_email/<email>")
def set_email(email):
    session["email"] = email
    return f"Email set to session: {email}"

# FOR SENDING EMAIL
@app.route('/email', methods=['GET'])
def email():
    # Render the Sign In form (could be a template)
    return render_template('email.html')

# FOR NOTIFICATION PAGE
@app.route('/notification', methods=['GET'])
def notification():
    # Render the Sign In form (could be a template)
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM ORDERS where status = 'Approved' ")
    orders = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('notification.html', orders=orders)


if __name__ == '__main__':
    app.run(debug=True)


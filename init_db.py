"""Seed an entirely fictional pizza delivery database. No network, no external dependencies."""
from __future__ import annotations
import os, sqlite3, hashlib, secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB = ROOT / 'data' / 'shoh_pizza_demo.db'
SCHEMA = ROOT / 'schema.sql'

PIZZAS = [
 (1,'Margherita','Klassika','Mozzarella, pomidor, rayhon',79000,'pizza_margarita.png','Mashhur'),
 (2,'Pepperoni','Go‘shtli','Pepperoni, mozzarella, pomidor sousi',99000,'pizza_pepperoni.png','TOP 1'),
 (3,'BBQ Chicken','Maxsus','Tovuq, BBQ sous, qizil piyoz',109000,'pizza_bbq.png','Yangi'),
 (4,'4 Cheese','Pishloqli','Mozzarella, cheddar, dorblu, parmesan',119000,'pizza_cheese.png','Premium'),
 (5,'Vegetarian','Yengil','Qo‘ziqorin, bulg‘or qalampiri, zaytun',89000,'pizza_veggie.png','Veggie'),
 (6,'Mexicana','Achchiq','Tovuq, jalapeño, makkajo‘xori, chili',115000,'pizza_mexicana.png','Spicy'),
]

def password_hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 180_000).hex()

def create_user(db, name: str, email: str, password: str, role: str, code: str):
    salt = secrets.token_hex(16)
    db.execute('INSERT INTO users(full_name,email,password_salt,password_hash,role,mfa_code) VALUES(?,?,?,?,?,?)',
               (name, email, salt, password_hash(password,salt), role, code))

def init_database(reset=False):
    DB.parent.mkdir(parents=True, exist_ok=True)
    if reset and DB.exists(): DB.unlink()
    with sqlite3.connect(DB) as db:
        db.executescript(SCHEMA.read_text(encoding='utf-8'))
        if not db.execute('SELECT COUNT(*) FROM users').fetchone()[0]:
            create_user(db,'Aziza Karimova','student@shohpizza.test','Pizza2026!','customer','246810')
            create_user(db,'Shoh Pizza Manager','manager@shohpizza.test','Manager2026!','manager','864200')
        if not db.execute('SELECT COUNT(*) FROM pizzas').fetchone()[0]:
            db.executemany('INSERT INTO pizzas(id,name,category,ingredients,price_sum,image,badge) VALUES(?,?,?,?,?,?,?)',PIZZAS)
        db.commit()
    return DB

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(); p.add_argument('--reset',action='store_true')
    args=p.parse_args(); print('Shoh Pizza demo DB:',init_database(args.reset))

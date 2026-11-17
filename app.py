"""Shoh Pizza: intentionally flawed offline training restaurant; fictional customers only."""
from __future__ import annotations
import hmac, json, os, secrets, sqlite3, time, hashlib, mimetypes, re, urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie
from pathlib import Path
from collections import defaultdict
from init_db import DB, ROOT, init_database, password_hash

HOST='127.0.0.1'
PORT=int(os.environ.get('SHOH_PIZZA_PORT', '8770'))
STATIC=ROOT/'static'
VULNERABLE=True  # --secure starts comparison mode; always loopback-only
FAILS=defaultdict(list)
LAB_COUNTER=defaultdict(int)

def dbconn():
    db=sqlite3.connect(DB, timeout=5)
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    return db

def sha(s): return hashlib.sha256(s.encode()).hexdigest()

def json_bytes(data): return json.dumps(data,ensure_ascii=False).encode('utf-8')

class Handler(BaseHTTPRequestHandler):
    server_version='ShohPizzaLocalLab/1.0'
    def log_message(self, fmt, *a): print('[Shoh Pizza]',self.address_string(),fmt%a)

    def reply(self, status, data, cookies=()):
        body=json_bytes(data)
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; script-src 'self'; connect-src 'self'; base-uri 'none'; object-src 'none'; frame-ancestors 'none'")
        for cookie in cookies: self.send_header('Set-Cookie',cookie)
        self.end_headers(); self.wfile.write(body)

    def cookie_str(self, name, value, max_age=None):
        part=f'{name}={value}; Path=/; HttpOnly; SameSite=Lax'
        if max_age is not None: part+=f'; Max-Age={max_age}'
        return part

    def cookies(self):
        c=SimpleCookie()
        try:c.load(self.headers.get('Cookie',''))
        except Exception:pass
        return c

    def get_cookie(self, name):
        c=self.cookies(); return c[name].value if name in c else None

    def session(self, db):
        token=self.get_cookie('sp_session')
        if not token:return None
        return db.execute('''SELECT u.id,u.full_name,u.email,u.role,s.csrf,s.mfa_verified
                             FROM sessions s JOIN users u ON u.id=s.user_id
                             WHERE s.token_hash=? AND s.expires_at>?''',(sha(token),int(time.time()))).fetchone()

    def need_auth(self,db,manager=False,csrf=False):
        user=self.session(db)
        if not user:
            self.reply(401,{'ok':False,'error':'Avval tizimga kiring.'});return None
        if (not VULNERABLE or manager) and not user['mfa_verified']:
            self.reply(401,{'ok':False,'error':'Tasdiqlash tugallanmagan.'});return None
        if manager and user['role']!='manager':
            self.reply(403,{'ok':False,'error':'Bu bo‘limga ruxsat yo‘q.'});return None
        if csrf and not hmac.compare_digest(str(user['csrf']),str(self.headers.get('X-CSRF-Token',''))):
            self.reply(403,{'ok':False,'error':'CSRF tekshiruvi bajarilmadi.'});return None
        return user

    def data(self):
        length=int(self.headers.get('Content-Length','0'))
        if length<0 or length>20000: raise ValueError('Request juda katta')
        return json.loads(self.rfile.read(length).decode('utf-8')) if length else {}

    def q(self): return urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query,keep_blank_values=True)
    def url(self):return urllib.parse.urlsplit(self.path).path

    def do_GET(self):
        route=self.url()
        if route=='/api/bootstrap':
            with dbconn() as db:
                user=self.session(db)
                pizzas=[dict(r) for r in db.execute('SELECT * FROM pizzas ORDER BY id')]
                info={k:user[k] for k in ('id','full_name','email','role')} if user else None
                self.reply(200,{'ok':True,'pizzas':pizzas,'user':info,'csrf':user['csrf'] if user else None,'demo':True});return
        if route=='/api/orders':
            with dbconn() as db:
                user=self.need_auth(db)
                if not user:return
                orders=[dict(r) for r in db.execute('SELECT id,total_sum,status,created_at FROM orders WHERE user_id=? ORDER BY id DESC',(user['id'],))]
                for order in orders:
                    order['items']=[dict(r) for r in db.execute('''SELECT p.name,i.qty,i.price_sum FROM order_items i JOIN pizzas p ON i.pizza_id=p.id WHERE i.order_id=?''',(order['id'],))]
                self.reply(200,{'ok':True,'orders':orders});return
        if route=='/api/manager/orders':
            with dbconn() as db:
                user=self.need_auth(db,manager=True)
                if not user:return
                orders=[dict(r) for r in db.execute('''SELECT o.id,o.total_sum,o.status,o.created_at,u.full_name
                         FROM orders o JOIN users u ON u.id=o.user_id ORDER BY o.id DESC LIMIT 40''')]
                self.reply(200,{'ok':True,'orders':orders});return
        if route=='/api/local-mailbox':
            email=self.q().get('email',[''])[0].strip().lower()
            if not email.endswith('@shohpizza.test'):
                self.reply(400,{'ok':False,'error':'Faqat o‘quv .test email.'});return
            with dbconn() as db:
                mail=[dict(r) for r in db.execute('SELECT subject,demo_link,created_at FROM demo_mailbox WHERE to_email=? ORDER BY id DESC LIMIT 3',(email,))]
            self.reply(200,{'ok':True,'mail':mail});return
        if route.startswith('/api/'):
            self.reply(404,{'ok':False,'error':'API topilmadi.'});return
        self.static(route)

    def static(self,route):
        if route in ('/','/reset','/login'): route='/index.html'
        try:
            name=urllib.parse.unquote(route).lstrip('/')
            f=(STATIC/name).resolve()
            if STATIC.resolve() not in f.parents or not f.is_file():raise ValueError()
            content=f.read_bytes()
            mime=mimetypes.guess_type(str(f))[0] or 'application/octet-stream'
            self.send_response(200);self.send_header('Content-Type',mime+'; charset=utf-8' if mime.startswith('text/') or mime in ('application/javascript','image/svg+xml') else mime)
            self.send_header('Content-Length',str(len(content)))
            self.send_header('X-Content-Type-Options','nosniff')
            self.end_headers();self.wfile.write(content)
        except (ValueError,OSError):
            self.reply(404,{'ok':False,'error':'Fayl topilmadi.'})

    def do_POST(self):
        route=self.url()
        try:p=self.data()
        except (ValueError,TypeError,json.JSONDecodeError) as exc:
            self.reply(400,{'ok':False,'error':'JSON noto‘g‘ri.'});return
        now=int(time.time())
        if route=='/api/auth/login':
            email=str(p.get('email','')).lower().strip()[:180]
            password=str(p.get('password',''))[:250]
            remember=bool(p.get('remember',False))
            key=(self.client_address[0],email)
            FAILS[key]=[x for x in FAILS[key] if now-x<90]
            if not VULNERABLE and len(FAILS[key])>=5:
                self.reply(429,{'ok':False,'error':'Ko‘p urinish. Keyinroq qaytadan urinib ko‘ring.'});return
            with dbconn() as db:
                user=db.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
                if user is None:
                    password_hash(password,'a1'*16)
                    FAILS[key].append(now)
                    self.reply(401,{'ok':False,'error':'Bunday email topilmadi.' if VULNERABLE else 'Email yoki parol xato.'});return
                valid=hmac.compare_digest(password_hash(password,user['password_salt']),user['password_hash'])
                if not valid:
                    FAILS[key].append(now)
                    self.reply(401,{'ok':False,'error':'Parol noto‘g‘ri.' if VULNERABLE else 'Email yoki parol xato.'});return
                FAILS.pop(key,None)
                pretoken=secrets.token_urlsafe(32)
                db.execute('INSERT INTO pending_mfa(token_hash,user_id,expires_at,remember) VALUES(?,?,?,?)',
                           (sha(pretoken),user['id'],now+300,int(remember)))
                cookies=[self.cookie_str('sp_mfa',pretoken,300)]
                if VULNERABLE:
                    # Teaching flaw: a PRE-MFA customer session is accepted by the orders API.
                    # Manager endpoints ALWAYS require MFA, even here.
                    premature=secrets.token_urlsafe(32)
                    csrf=secrets.token_urlsafe(20)
                    db.execute('INSERT INTO sessions(token_hash,user_id,csrf,expires_at,mfa_verified) VALUES(?,?,?,?,0)',
                               (sha(premature),user['id'],csrf,now+300))
                    cookies.append(self.cookie_str('sp_session',premature,300))
                db.commit()
            self.reply(202,{'ok':True,'mfa_required':True},cookies);return
        if route=='/api/auth/mfa':
            code=str(p.get('code','')).strip()[:30]
            pretoken=self.get_cookie('sp_mfa')
            if not pretoken:
                self.reply(401,{'ok':False,'error':'Avval parol bosqichidan o‘ting.'});return
            with dbconn() as db:
                record=db.execute('''SELECT m.*,u.mfa_code FROM pending_mfa m JOIN users u ON u.id=m.user_id
                                      WHERE m.token_hash=?''',(sha(pretoken),)).fetchone()
                if not record or record['expires_at']<now or record['attempts']>=5:
                    self.reply(401,{'ok':False,'error':'2FA tasdiqlash muddati tugagan.'},[self.cookie_str('sp_mfa','',0)]);return
                if not hmac.compare_digest(code,str(record['mfa_code'])):
                    db.execute('UPDATE pending_mfa SET attempts=attempts+1 WHERE token_hash=?',(sha(pretoken),));db.commit()
                    self.reply(401,{'ok':False,'error':'Tasdiqlash kodi noto‘g‘ri.'});return
                db.execute('DELETE FROM pending_mfa WHERE token_hash=?',(sha(pretoken),))
                old_session=self.get_cookie('sp_session')
                if old_session:
                    db.execute('DELETE FROM sessions WHERE token_hash=?',(sha(old_session),))
                sess=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(20)
                age=7*86400 if record['remember'] else 8*3600
                db.execute('INSERT INTO sessions(token_hash,user_id,csrf,expires_at,mfa_verified) VALUES(?,?,?,?,1)',(sha(sess),record['user_id'],csrf,now+age))
                db.commit()
            self.reply(200,{'ok':True,'authenticated':True},[self.cookie_str('sp_mfa','',0), self.cookie_str('sp_session',sess,age if record['remember'] else None)]);return
        if route=='/api/auth/logout':
            with dbconn() as db:
                user=self.session(db)
                if user and not VULNERABLE and hmac.compare_digest(str(user['csrf']),str(self.headers.get('X-CSRF-Token',''))):
                    tok=self.get_cookie('sp_session');db.execute('DELETE FROM sessions WHERE token_hash=?',(sha(tok),));db.commit()
            self.reply(200,{'ok':True},[self.cookie_str('sp_session','',0),self.cookie_str('sp_mfa','',0)]);return
        if route=='/api/orders':
            with dbconn() as db:
                user=self.need_auth(db,csrf=True)
                if not user:return
                items=p.get('items')
                if not isinstance(items,list) or not items or len(items)>12:
                    self.reply(400,{'ok':False,'error':'Savatcha bo‘sh yoki noto‘g‘ri.'});return
                lines=[];total=0
                for entry in items:
                    if not isinstance(entry,dict):
                        self.reply(400,{'ok':False,'error':'Noto‘g‘ri mahsulot.'});return
                    try: pizza_id=int(entry.get('id'));qty=int(entry.get('qty'))
                    except (TypeError,ValueError):
                        self.reply(400,{'ok':False,'error':'Noto‘g‘ri son.'});return
                    if qty<1 or qty>8:
                        self.reply(400,{'ok':False,'error':'Miqdor 1–8 oralig‘ida bo‘lishi kerak.'});return
                    piz=db.execute('SELECT id,price_sum FROM pizzas WHERE id=?',(pizza_id,)).fetchone()
                    if not piz:
                        self.reply(400,{'ok':False,'error':'Mahsulot topilmadi.'});return
                    total+=piz['price_sum']*qty;lines.append((pizza_id,qty,piz['price_sum']))
                db.execute('INSERT INTO orders(user_id,total_sum) VALUES(?,?)',(user['id'],total))
                oid=db.execute('SELECT last_insert_rowid()').fetchone()[0]
                db.executemany('INSERT INTO order_items(order_id,pizza_id,qty,price_sum) VALUES(?,?,?,?)',[(oid,*it) for it in lines]);db.commit()
            self.reply(201,{'ok':True,'order_id':oid,'total_sum':total,'message':'Demo buyurtma qabul qilindi. Haqiqiy to‘lov yo‘q.'});return
        if route=='/api/auth/reset/request':
            email=str(p.get('email','')).lower().strip()[:180]
            with dbconn() as db:
                user=db.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone()
                if user:
                    token=secrets.token_urlsafe(26)
                    db.execute('INSERT INTO password_resets(token_hash,user_id,expires_at) VALUES(?,?,?)',(sha(token),user['id'],now+600))
                    db.execute('INSERT INTO demo_mailbox(to_email,subject,demo_link) VALUES(?,?,?)',(email,'Parolni tiklash — Shoh Pizza',f'/reset?token={token}'))
                    db.commit()
            if VULNERABLE and not user:
                self.reply(404,{'ok':False,'error':'Bunday email bilan hisob mavjud emas.'});return
            self.reply(200,{'ok':True,'message':'Tiklash uchun xat yuborildi.' if VULNERABLE else 'Agar email mavjud bo‘lsa, havola yuboriladi.'});return
        if route=='/api/auth/reset/confirm':
            token=str(p.get('token',''))[:150];new=str(p.get('password',''))[:250]
            if len(new)<8 or len(new)>128:
                self.reply(400,{'ok':False,'error':'Parol kamida 8 ta belgi bo‘lsin.'});return
            with dbconn() as db:
                row=db.execute('SELECT * FROM password_resets WHERE token_hash=? AND used=0 AND expires_at>?',(sha(token),now)).fetchone()
                if not row:
                    self.reply(400,{'ok':False,'error':'Havola yaroqsiz yoki muddati tugagan.'});return
                salt=secrets.token_hex(16);h=password_hash(new,salt)
                db.execute('UPDATE users SET password_salt=?,password_hash=? WHERE id=?',(salt,h,row['user_id']))
                if not VULNERABLE:
                    db.execute('UPDATE password_resets SET used=1 WHERE token_hash=?',(sha(token),))
                    db.execute('DELETE FROM sessions WHERE user_id=?',(row['user_id'],))
                db.commit()
            self.reply(200,{'ok':True,'message':'Parol yangilandi. Endi yangi parol bilan kiring.'});return
        self.reply(404,{'ok':False,'error':'API topilmadi.'})

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument('--reset',action='store_true')
    p.add_argument('--secure',action='store_true',help='Run the same website with protection enabled')
    p.add_argument('--port',type=int,default=PORT)
    args=p.parse_args()
    VULNERABLE=not args.secure
    init_database(args.reset)
    mode='VULNERABLE (educational)' if VULNERABLE else 'SECURE (comparison)'
    print(f'\nShoh Pizza | {mode}\nhttp://{HOST}:{args.port}\nFictional customers only; NEVER expose outside localhost.\n')
    server=ThreadingHTTPServer((HOST,args.port),Handler)
    try:server.serve_forever()
    except KeyboardInterrupt:print('Stopped.')
    finally:server.server_close()

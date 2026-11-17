"""Local functional checks for Shoh Pizza's two deliberately different modes."""
from __future__ import annotations
import json, os, subprocess, sys, time, http.client, urllib.parse
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def fetch(port, path, method='GET', data=None, cookie='', csrf=''):
    conn=http.client.HTTPConnection('127.0.0.1',port,timeout=6)
    body=json.dumps(data).encode() if data is not None else None
    headers={'Content-Type':'application/json'} if body else {}
    if cookie:headers['Cookie']=cookie
    if csrf:headers['X-CSRF-Token']=csrf
    conn.request(method,path,body=body,headers=headers)
    r=conn.getresponse();raw=r.read();status=r.status;cookies=r.getheaders();conn.close()
    return status,json.loads(raw.decode()),[v for k,v in cookies if k.lower()=='set-cookie']

def get_cookie(headers,name):
    for c in headers:
        if c.startswith(name+'='):return c.split(';',1)[0]
    return ''

def launch(port,secure=False):
    args=[sys.executable,'app.py','--reset','--port',str(port)]+(['--secure'] if secure else [])
    proc=subprocess.Popen(args,cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    for _ in range(40):
        try:fetch(port,'/api/bootstrap');return proc
        except (OSError,TimeoutError):time.sleep(.15)
    proc.kill();raise RuntimeError('server did not start')

def test_vuln(port):
    print('VULNERABLE MODE')
    st,body,_=fetch(port,'/api/auth/login','POST',{'email':'absent@shohpizza.test','password':'wrong'})
    assert st==401 and 'topilmadi' in body['error'],(st,body)
    for i in range(7):
        st,body,_=fetch(port,'/api/auth/login','POST',{'email':'student@shohpizza.test','password':'wrong'})
        assert st==401 and 'noto‘g‘ri' in body['error'],(st,body)
    st,body,cookies=fetch(port,'/api/auth/login','POST',{'email':'student@shohpizza.test','password':'Pizza2026!'})
    assert st==202 and body['mfa_required'],(st,body)
    pm=get_cookie(cookies,'sp_mfa');sc=get_cookie(cookies,'sp_session')
    assert pm and sc, cookies
    st,body,_=fetch(port,'/api/orders',cookie=sc)
    assert st==200 and body['ok'],(st,body)
    st,body,_=fetch(port,'/api/manager/orders',cookie=sc)
    assert st==401,(st,body)
    st,body,cookies=fetch(port,'/api/auth/mfa','POST',{'code':'246810'},cookie=f'{pm}; {sc}')
    assert st==200 and body['authenticated'],(st,body)
    sc=get_cookie(cookies,'sp_session')
    st,body,_=fetch(port,'/api/bootstrap',cookie=sc)
    assert st==200 and body['user'],(st,body)
    csrf=body['csrf']
    st,body,_=fetch(port,'/api/orders','POST',{'items':[{'id':2,'qty':1}]},cookie=sc,csrf=csrf)
    assert st==201,(st,body)
    st,body,_=fetch(port,'/api/auth/logout','POST',{},cookie=sc,csrf=csrf)
    assert st==200,(st,body)
    st,body,_=fetch(port,'/api/orders',cookie=sc)
    assert st==200,(st,body)
    st,body,_=fetch(port,'/api/auth/reset/request','POST',{'email':'absent@shohpizza.test'})
    assert st==404,(st,body)
    st,body,_=fetch(port,'/api/auth/reset/request','POST',{'email':'student@shohpizza.test'})
    assert st==200,(st,body)
    st,body,_=fetch(port,'/api/local-mailbox?email=student%40shohpizza.test')
    assert st==200 and body['mail'],(st,body)
    token=urllib.parse.parse_qs(urllib.parse.urlsplit(body['mail'][0]['demo_link']).query)['token'][0]
    for _ in range(2):
        st,body,_=fetch(port,'/api/auth/reset/confirm','POST',{'token':token,'password':'AnySafeDemo2026!'})
        assert st==200,(st,body)
    print(' PASS: real login enumeration / unlimited attempts / pre-MFA customer access / logout reuse / recovery')

def test_safe(port):
    print('SAFE COMPARISON MODE')
    st,absent,_=fetch(port,'/api/auth/login','POST',{'email':'absent@shohpizza.test','password':'wrong'})
    st2,known,_=fetch(port,'/api/auth/login','POST',{'email':'student@shohpizza.test','password':'wrong'})
    assert st==st2==401 and absent['error']==known['error'],(absent,known)
    for _ in range(4):fetch(port,'/api/auth/login','POST',{'email':'student@shohpizza.test','password':'wrong'})
    st,body,_=fetch(port,'/api/auth/login','POST',{'email':'student@shohpizza.test','password':'wrong'})
    assert st==429,(st,body)
    st,body,cookies=fetch(port,'/api/auth/login','POST',{'email':'manager@shohpizza.test','password':'Manager2026!'})
    assert st==202 and get_cookie(cookies,'sp_mfa') and not get_cookie(cookies,'sp_session'),(st,cookies)
    pm=get_cookie(cookies,'sp_mfa')
    st,body,_=fetch(port,'/api/orders',cookie=pm)
    assert st==401,(st,body)
    st,body,cookies=fetch(port,'/api/auth/mfa','POST',{'code':'864200'},cookie=pm)
    assert st==200,(st,body)
    sc=get_cookie(cookies,'sp_session')
    st,body,_=fetch(port,'/api/bootstrap',cookie=sc)
    csrf=body['csrf']; assert csrf
    st,body,_=fetch(port,'/api/manager/orders',cookie=sc)
    assert st==200,(st,body)
    st,body,_=fetch(port,'/api/auth/logout','POST',{},cookie=sc,csrf=csrf)
    assert st==200,(st,body)
    st,body,_=fetch(port,'/api/orders',cookie=sc)
    assert st==401,(st,body)
    st1,body1,_=fetch(port,'/api/auth/reset/request','POST',{'email':'absent@shohpizza.test'})
    st2,body2,_=fetch(port,'/api/auth/reset/request','POST',{'email':'student@shohpizza.test'})
    assert st1==st2==200 and body1['message']==body2['message']
    st,body,_=fetch(port,'/api/local-mailbox?email=student%40shohpizza.test')
    assert st==200 and body['mail'],(st,body)
    token=urllib.parse.parse_qs(urllib.parse.urlsplit(body['mail'][0]['demo_link']).query)['token'][0]
    assert fetch(port,'/api/auth/reset/confirm','POST',{'token':token,'password':'AnySafeDemo2026!'})[0]==200
    assert fetch(port,'/api/auth/reset/confirm','POST',{'token':token,'password':'AnySafeDemo2026!'})[0]==400
    print(' PASS: generic errors / rate limit / strict MFA / manager control / logout invalidation / single-use reset')

def main():
    for port,secure,fn in [(8870,False,test_vuln),(8871,True,test_safe)]:
        proc=launch(port,secure)
        try:fn(port)
        finally:
            proc.terminate()
            try:proc.wait(timeout=3)
            except subprocess.TimeoutExpired:proc.kill()
    print('ALL TESTS PASSED')
if __name__=='__main__':main()

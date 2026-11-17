'use strict';
const $=(q)=>document.querySelector(q);
const $$=(q)=>[...document.querySelectorAll(q)];
const state={pizzas:[],user:null,csrf:null,cart:new Map(),page:'home',filter:'Hammasi',mfaPending:false};
const money=(n)=>Number(n).toLocaleString('ru-RU')+' so‘m';
let toastTimeout;
function toast(s){const t=$('#toast');t.textContent=s;t.classList.add('show');clearTimeout(toastTimeout);toastTimeout=setTimeout(()=>t.classList.remove('show'),3300)}
function esc(x){return String(x).replace(/[&<>"']/g,s=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[s]))}
async function api(path,method='GET',body){
 let options={method,credentials:'same-origin',headers:{}};
 if(method!=='GET'){
  options.headers['Content-Type']='application/json';
  if(state.csrf)options.headers['X-CSRF-Token']=state.csrf;
  options.body=JSON.stringify(body??{});
 }
 try{let res=await fetch(path,options);let json=await res.json();return {status:res.status,...json}}catch(e){return{ok:false,status:0,error:'Serverga ulanib bo‘lmadi. python3 app.py ishlayotganini tekshiring.'}}
}
async function refresh(){const r=await api('/api/bootstrap');if(!r.ok){toast(r.error||'Server topilmadi');return}
 state.pizzas=r.pizzas;state.user=r.user;state.csrf=r.csrf;
 $('#openAuth').innerHTML=state.user?`${esc(state.user.full_name.split(' ')[0])} <span>⌄</span>`:'Kirish <span>↗</span>';
 $('#navManager').hidden=!state.user||state.user.role!=='manager';
 renderMenu();renderCart();
}
function cardHTML(p){return `<article class="pizza-card"><div class="pizza-image"><img loading="lazy" src="/assets/${esc(p.image)}" alt="${esc(p.name)} pitsa"><span class="pizza-badge">${esc(p.badge)}</span></div><div class="pizza-body"><div class="pizza-line"><h3>${esc(p.name)}</h3><span class="tag">${esc(p.category)}</span></div><p>${esc(p.ingredients)}</p><div class="pizza-foot"><div class="price">${money(p.price_sum)} <small>/ 32 sm</small></div><button class="add-button" data-add="${p.id}" aria-label="${esc(p.name)} savatchaga qo‘shish">+ Qo‘shish</button></div></div></article>`}
function renderMenu(){
 $('#homeCards').innerHTML=state.pizzas.slice(0,3).map(cardHTML).join('');
 const filtered=state.filter==='Hammasi'?state.pizzas:state.pizzas.filter(p=>p.category===state.filter);
 $('#menuCards').innerHTML=filtered.map(cardHTML).join('');
}
function navigate(view){
 const allowed=['home','menu','orders','about','recover','manager','reset'];if(!allowed.includes(view))return;
 if(view==='manager'&&(!state.user||state.user.role!=='manager')){toast('Manager paneliga ruxsat yo‘q');return}
 state.page=view;
 $$('.view').forEach(el=>el.hidden=el.dataset.page!==view);
 $$('.navlink').forEach(el=>el.classList.toggle('active',el.dataset.view===view));
 window.scrollTo({top:0,behavior:'smooth'});
 if(view==='orders')loadOrders();if(view==='manager')loadManager();
}
function openAuth(){if(state.user){navigate('orders');return}$('#authBackdrop').hidden=false;$('#authModal').hidden=false;$('#authFeedback').textContent='';setTimeout(()=>$('#loginForm [name=email]').focus(),60)}
function closeAuth(){$('#authBackdrop').hidden=true;$('#authModal').hidden=true;$('#authFeedback').textContent=''}
function loginState(stage){state.mfaPending=(stage==='mfa');$('#loginForm').hidden=(stage==='mfa');$('#mfaForm').hidden=(stage!=='mfa');$('#authTitle').innerHTML=stage==='mfa'?'Yana bir <em>qadam!</em>':'Yana <em>xush kelibsiz!</em>';$('#authDesc').textContent=stage==='mfa'?'Endi tasdiqlash kodini kiriting.':'Sevimli pitsalaringizga bir qadam qoldi.'}
async function submitLogin(e){e.preventDefault();const data=new FormData(e.currentTarget);const r=await api('/api/auth/login','POST',{email:data.get('email'),password:data.get('password'),remember:data.get('remember')==='on'});
 if(r.status===202&&r.mfa_required){loginState('mfa');$('#authFeedback').textContent='Parol qabul qilindi. Tasdiqlash kodini kiriting.';return}
 $('#authFeedback').textContent=r.error||'Kirish amalga oshmadi.';
}
async function submitMFA(e){e.preventDefault();const r=await api('/api/auth/mfa','POST',{code:$('#mfaCode').value});
 if(r.ok){loginState('login');closeAuth();$('#loginForm').reset();$('#mfaForm').reset();await refresh();toast('2FA tasdiqlandi. Xush kelibsiz!');if(state.page==='orders')loadOrders();return}
 $('#authFeedback').textContent=r.error||'Tasdiqlash bajarilmadi.';
}
async function logout(){await api('/api/auth/logout','POST',{});await refresh();navigate('home');toast('Hisobdan chiqdingiz')}
function addCart(id){id=Number(id);state.cart.set(id,Math.min(8,(state.cart.get(id)||0)+1));renderCart();toast('Pitsa savatchaga qo‘shildi 🍕')}
function qty(id,delta){id=Number(id);const n=(state.cart.get(id)||0)+delta;if(n<=0)state.cart.delete(id);else state.cart.set(id,Math.min(8,n));renderCart()}
function renderCart(){let n=0,total=0,rows=[];for(const [id,q] of state.cart){const p=state.pizzas.find(p=>p.id===id);if(!p)continue;n+=q;total+=p.price_sum*q;rows.push(`<div class="cart-item"><img src="/assets/${esc(p.image)}" alt="${esc(p.name)}"><div><strong>${esc(p.name)}</strong><p>${money(p.price_sum)}</p><div class="qty-row"><button data-qty="${id}" data-change="-1" aria-label="Kamaytirish">−</button><span>${q}</span><button data-qty="${id}" data-change="1" aria-label="Ko‘paytirish">+</button></div></div></div>`)}
 $('#cartCount').textContent=n;$('#cartTotal').textContent=money(total);$('#cartItems').innerHTML=rows.length?rows.join(''):'<div class="empty-state"><div class="empty-icon">🍕</div><h3>Hali bo‘sh</h3><p>Avval menyudan biror pitsa tanlang.</p></div>';$('#checkout').disabled=!n;
}
function openCart(){$('#cartBackdrop').hidden=false;$('#cartDrawer').hidden=false}
function closeCart(){$('#cartBackdrop').hidden=true;$('#cartDrawer').hidden=true}
async function checkout(){if(!state.user){closeCart();openAuth();toast('Buyurtma berish uchun tizimga kiring');return}
 let items=[...state.cart].map(([id,qty])=>({id,qty}));const r=await api('/api/orders','POST',{items});if(!r.ok){toast(r.error||'Xatolik');return}
 state.cart.clear();renderCart();closeCart();toast(`Buyurtma №${r.order_id} qabul qilindi!`);navigate('orders')}
function ordersHTML(orders,manager=false){if(!orders?.length)return '<div class="empty-state"><div class="empty-icon">🧾</div><h3>Hozircha buyurtmalar yo‘q</h3><p>Menyudan pitsa tanlang va demo buyurtmani rasmiylashtiring.</p><button class="button primary" data-view="menu">Menyuga o‘tish →</button></div>';
 return orders.map(o=>`<article class="order-box"><header><div><h3>Buyurtma №${o.id} ${manager?'• '+esc(o.full_name):''}</h3><p>${esc(o.created_at)} • ${esc(o.status)}</p></div><div class="order-total">${money(o.total_sum)}</div></header>${o.items?`<ul>${o.items.map(p=>`<li>${esc(p.name)} × ${p.qty}</li>`).join('')}</ul>`:''}</article>`).join('')}
async function loadOrders(){if(!state.user){$('#ordersList').innerHTML='<div class="empty-state"><div class="empty-icon">🔐</div><h3>Avval tizimga kiring</h3><p>Buyurtmalarni ko‘rish uchun login va 2FA kerak.</p><button class="button primary" id="ordersLogin">Login →</button></div>';return}
 let r=await api('/api/orders');$('#ordersList').innerHTML=r.ok?ordersHTML(r.orders):`<p>${esc(r.error)}</p>`}
async function loadManager(){const r=await api('/api/manager/orders');$('#managerOrders').innerHTML=r.ok?ordersHTML(r.orders,true):`<div class="empty-state"><h3>HTTP ${r.status}: ${esc(r.error||'Ruxsat yo‘q')}</h3></div>`}
async function requestReset(e){
 e.preventDefault();
 const email=$('#recoverEmail').value.trim();
 const r=await api('/api/auth/reset/request','POST',{email});
 const msg=$('#recoverFeedback');
 msg.textContent=r.message||r.error||'Xatolik yuz berdi.';
 msg.classList.toggle('success',!!r.ok);
}
async function resetConfirm(e){e.preventDefault();const token=new URLSearchParams(location.search).get('token')||'';const r=await api('/api/auth/reset/confirm','POST',{token,password:$('#newPassword').value});$('#resetFeedback').textContent=r.message||r.error;$('#resetFeedback').classList.toggle('success',!!r.ok);if(r.ok)setTimeout(()=>{history.pushState({},'', '/');navigate('home');openAuth()},1700)}
function bind(){
 document.addEventListener('click',e=>{
  let view=e.target.closest('[data-view]');if(view){navigate(view.dataset.view);return}
  let add=e.target.closest('[data-add]');if(add){addCart(add.dataset.add);return}
  let qt=e.target.closest('[data-qty]');if(qt){qty(qt.dataset.qty,Number(qt.dataset.change));return}
  let ft=e.target.closest('[data-filter]');if(ft){state.filter=ft.dataset.filter;$$('[data-filter]').forEach(x=>x.classList.toggle('active',x===ft));renderMenu();return}
  if(e.target.closest('#ordersLogin'))openAuth();
 });
 $('#openAuth').onclick=()=>state.user?logout():openAuth();
 $('#forgotLink').onclick=()=>{closeAuth();navigate('recover');setTimeout(()=>$('#recoverEmail').focus(),180)};
 $('#authClose').onclick=$('#authBackdrop').onclick=closeAuth;
 $('#cartOpen').onclick=openCart;$('#cartClose').onclick=$('#cartBackdrop').onclick=closeCart;
 $('#checkout').onclick=checkout;$('#loginForm').onsubmit=submitLogin;$('#mfaForm').onsubmit=submitMFA;
 $('#backToLogin').onclick=()=>{loginState('login');$('#authFeedback').textContent='Kirishni qayta boshlang.'};
 $('#recoverForm').onsubmit=requestReset;
 $('#recoverToLogin').onclick=()=>{navigate('home');openAuth()};
 $('#resetConfirmForm').onsubmit=resetConfirm;
 document.addEventListener('keydown',e=>{if(e.key==='Escape'){closeAuth();closeCart()}});
}
async function main(){bind();await refresh();if(location.pathname==='/reset'&&new URLSearchParams(location.search).has('token'))navigate('reset');else if(location.pathname==='/login'){navigate('home');openAuth()}else navigate('home')}
main();


import streamlit as st
import streamlit.components.v1 as components
import pymysql
import io
from datetime import date, datetime, time
from collections import defaultdict
import re
from zoneinfo import ZoneInfo
def now_wib(): return datetime.now(ZoneInfo('Asia/Jakarta'))
def today_wib(): return now_wib().date()

# === DB CONFIG AMAN - pakai Secrets Streamlit, TIDAK ada password di file ini ===
try:
    DB = {"host": st.secrets["mysql"]["host"], "port": st.secrets["mysql"]["port"], "user": st.secrets["mysql"]["user"], "password": st.secrets["mysql"]["password"], "database": st.secrets["mysql"]["database"], "charset": "utf8mb4", "ssl": {"ssl_mode": "REQUIRED"}, "connect_timeout": 10}
    LOGIN_USER = st.secrets["auth"]["username"]; LOGIN_PASS = st.secrets["auth"]["password"]
except Exception:
    st.error("Secrets belum diisi! Manage app > Settings > Secrets, lalu Reboot."); st.stop()

# === BASE DATA ===
SUMBER_PEMASUKAN_BASE = ["Bayar Hutang", "Bonus", "Komisi Jual Barang", "Ongkos Kerja", "Ongkos Kerja Lembur", "THR", "Tips Beliin sesuatu", "Unit 05GC", "Unit 07GP", "Unit 08AB", "Unit 10GF", "Unit 11GF", "Unit 20GA", "Dll/ Lainnya"]
JENIS_PENGELUARAN_BASE = ["Beli Obat", "Beli Pertalite", "Beli Pertamax", "Ganti Oli Mesin & Oli Gardan", "Jajan", "Kasih ke Istri", "Makan di luar", "Parkir", "Dll/ Lainnya"]
NOMINAL = ["Rp5.000,00", "Rp10.000,00", "Rp15.000,00", "Rp20.000,00", "Rp25.000,00", "Rp50.000,00", "Rp75.000,00", "Rp100.000,00", "Dll / Lainnya"]
HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]

BUDGET_JAJAN = 25000
BUDGET_MAKAN_LUAR = 50000
CONTROLLABLE = ["Jajan", "Makan di luar"]
UNCONTROLLABLE = ["Beli Pertalite", "Beli Pertamax", "Parkir", "Kasih ke Istri", "Beli Obat", "Ganti Oli Mesin & Oli Gardan"]

def parse_nominal(s):
    if not s:
        return 0
    # Ambil angka
    try:
        # Format Rp4.567.000,00
        clean = re.sub(r'[^0-9]', '', str(s))
        if not clean:
            return 0
        # Kalau ada ,00 di akhir, clean sudah tanpa titik koma, jadi misal 456700000 -> bagi 100?
        # Sederhananya: jika string ada ,00, anggap 2 digit terakhir desimal
        # Tapi di data kamu Rp4.000,00 -> 4000
        # Kita coba parse dengan logika: hapus titik, ganti koma jadi titik
        t = str(s).replace("Rp", "").replace(" ", "").strip()
        t = t.replace(".", "").replace(",", ".")
        val = float(t)
        return int(val)
    except:
        digits = re.sub(r'[^0-9]', '', str(s))
        return int(digits) if digits else 0

def format_rp_id(n):
    try:
        n = int(n)
        return f"Rp{n:,}".replace(",", ".") + ",00"
    except:
        return str(n)

def plot_3d_bar(data, title):
    try:
        import matplotlib.pyplot as plt
        import numpy as np
        fig = plt.figure(figsize=(10, 5))
        ax = fig.add_subplot(111, projection='3d')
        labels = [d.get("Sumber") or d.get("Jenis") for d in data]
        values = [d["Nominal"] for d in data]
        x = np.arange(len(labels))
        y = np.zeros(len(labels))
        z = np.zeros(len(labels))
        dx = 0.5
        dy = 0.5
        dz = values
        colors = plt.cm.Greens(np.linspace(0.3, 0.9, len(values))) if "PEMASUKAN" in title else plt.cm.Reds(np.linspace(0.3, 0.9, len(values)))
        ax.bar3d(x, y, z, dx, dy, dz, color=colors, edgecolor='black', alpha=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=20, fontsize=7)
        ax.set_title(title)
        ax.view_init(elev=25, azim=45)
        plt.tight_layout()
        return fig, None
    except Exception as e:
        return None, None

def plot_controllable_3d(controllable_dict, uncontrollable_dict):
    try:
        import matplotlib.pyplot as plt
        import numpy as np
        fig = plt.figure(figsize=(10,5))
        ax = fig.add_subplot(111, projection='3d')
        all_data = {**controllable_dict, **uncontrollable_dict}
        labels = list(all_data.keys())
        values = list(all_data.values())
        x = np.arange(len(labels))
        y = np.zeros(len(labels))
        z = np.zeros(len(labels))
        dx = 0.5
        dy = 0.5
        dz = values
        colors = []
        for k in labels:
            if k=="Jajan":
                colors.append('orange')
            elif k=="Makan di luar":
                colors.append('gold')
            else:
                colors.append('steelblue')
        ax.bar3d(x, y, z, dx, dy, dz, color=colors, edgecolor='black', alpha=0.9)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=15, fontsize=8)
        ax.set_title('CONTROLLABLE vs UNCONTROLLABLE 3D')
        ax.view_init(elev=25, azim=45)
        plt.tight_layout()
        return fig
    except:
        return None

st.set_page_config(page_title="Keuangan MySQL - BUDGET 3D", layout="wide")
st.markdown("""
<style>
.stApp { background: linear-gradient(135deg, #e0f7fa 0%, #e8f5e9 50%, #fff9c4 100%); }
label, div[data-testid="stWidgetLabel"], p { background: transparent !important; border: none !important; box-shadow: none !important; }
div[data-testid="stTextInput"] > div > div,
div[data-testid="stDateInput"] > div > div,
div[data-testid="stTimeInput"] > div > div,
div[data-testid="stSelectbox"] > div > div,
div[data-testid="stTextArea"] > div,
div[data-baseweb="select"] > div,
div[data-baseweb="input"] { background-color: white !important; border: 2px solid #80cbc4 !important; border-radius: 12px !important; }
div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea,
div[data-testid="stSelectbox"] input,
div[data-testid="stDateInput"] input,
div[data-testid="stTimeInput"] input { background-color: white !important; color: black !important; }
.stButton>button { border-radius: 15px !important; padding: 12px !important; font-weight: bold !important; border: none !important; background: linear-gradient(180deg, #4db6ac 0%, #00796b 100%) !important; color: white !important; }
.edit-box { background: white; border: 3px solid #ff9800; border-radius: 15px; padding: 15px; box-shadow: 2px 2px 10px rgba(0,0,0,0.1); }
</style>
""", unsafe_allow_html=True)

def apply_beda_warna():
    components.html("""
    <script>
    function bedainBatang() {
        try {
            const parentDoc = window.parent.document;
            const allBtns = parentDoc.querySelectorAll('button');
            allBtns.forEach(btn => {
                const txt = (btn.innerText || '').toUpperCase();
                if (txt.includes('BUKA PEMASUKAN') || txt.includes('SIMPAN PEMASUKAN') || (txt.includes('PEMASUKAN') && !txt.includes('PENGELUARAN'))) {
                    btn.style.setProperty('background', 'linear-gradient(180deg, #66bb6a 0%, #2e7d32 100%)', 'important');
                } else if (txt.includes('BUKA PENGELUARAN') || txt.includes('SIMPAN PENGELUARAN') || txt.includes('PENGELUARAN')) {
                    btn.style.setProperty('background', 'linear-gradient(180deg, #ef5350 0%, #b71c1c 100%)', 'important');
                }
            });
        } catch(e) {}
    }
    bedainBatang(); setTimeout(bedainBatang, 200); setTimeout(bedainBatang, 800); 
    </script>
    """, height=0)

def play_success_sound(msg="Berhasil tersimpan!"):
    safe = str(msg).replace("✅", "").replace('"', "").replace("'", "").strip() or "Berhasil tersimpan"
    components.html(f"""
    <script>
    try {{
        var u = new SpeechSynthesisUtterance("{safe}"); u.lang = "id-ID"; u.rate = 1.0;
        window.speechSynthesis.cancel(); window.speechSynthesis.speak(u);
    }} catch(e) {{}}
    </script>
    """, height=0)

def get_conn(): return pymysql.connect(**DB)

def init_tables():
    try:
        conn=get_conn(); cur=conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS pemasukan (id INT AUTO_INCREMENT PRIMARY KEY, hari VARCHAR(20), tanggal DATE, jam TIME, sumber VARCHAR(100), nominal VARCHAR(50), keterangan TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        cur.execute("CREATE TABLE IF NOT EXISTS pengeluaran (id INT AUTO_INCREMENT PRIMARY KEY, hari VARCHAR(20), tanggal DATE, jam TIME, kategori VARCHAR(100), nominal VARCHAR(50), keterangan TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        cur.execute("CREATE TABLE IF NOT EXISTS custom_nominal (id INT AUTO_INCREMENT PRIMARY KEY, jenis VARCHAR(20), nominal VARCHAR(50), UNIQUE KEY uniq (jenis, nominal))")
        cur.execute("CREATE TABLE IF NOT EXISTS custom_sumber (id INT AUTO_INCREMENT PRIMARY KEY, jenis VARCHAR(20), sumber VARCHAR(100), UNIQUE KEY uniq_sumber (jenis, sumber))")
        conn.commit(); conn.close()
    except Exception as e: st.error(f"MySQL init error: {e}")

def get_sumber_list(custom_sumber_rows):
    base=SUMBER_PEMASUKAN_BASE[:-1]; extras=[r[1] for r in custom_sumber_rows if r[0]=="pemasukan"]; merged=[]; seen=set()
    for x in base+extras:
        if x not in seen: merged.append(x); seen.add(x)
    merged=sorted(merged, key=lambda x: x.lower())
    merged.append("Dll/ Lainnya"); return merged

def get_jenis_pengeluaran_list(custom_sumber_rows):
    base=JENIS_PENGELUARAN_BASE[:-1]; extras=[r[1] for r in custom_sumber_rows if r[0]=="pengeluaran"]; merged=[]; seen=set()
    for x in base+extras:
        if x not in seen: merged.append(x); seen.add(x)
    merged=sorted(merged, key=lambda x: x.lower())
    merged.append("Dll/ Lainnya"); return merged

def _nom_key(x):
    d=re.sub(r"[^0-9]", "", str(x))
    return int(d) if d else 999999999

def get_nom_list(custom_rows, jenis):
    base=NOMINAL[:-1]; extras=[r[1] for r in custom_rows if r[0]==jenis]; merged=[]; seen=set()
    for x in base+extras:
        if x not in seen: merged.append(x); seen.add(x)
    merged=sorted(merged, key=_nom_key)
    merged.append("Dll / Lainnya"); return merged

def load_mysql():
    try:
        conn=get_conn(); cur=conn.cursor()
        cur.execute("SELECT id, hari, tanggal, jam, sumber, nominal, keterangan FROM pemasukan ORDER BY id DESC"); pem=cur.fetchall()
        cur.execute("SELECT id, hari, tanggal, jam, kategori, nominal, keterangan FROM pengeluaran ORDER BY id DESC"); peng=cur.fetchall()
        cur.execute("SELECT jenis, nominal FROM custom_nominal"); custom=cur.fetchall()
        try: cur.execute("SELECT jenis, sumber FROM custom_sumber"); custom_sumber=cur.fetchall()
        except: custom_sumber=[]
        conn.close(); return pem, peng, custom, custom_sumber
    except: return [], [], [], []

def buat_xlsx(rows, is_masuk=True):
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        if not rows: return None
        wb=Workbook(); ws=wb.active; ws.title="Pemasukan" if is_masuk else "Pengeluaran"
        datas=[]
        for idx,r in enumerate(rows): datas.append({"No":idx,"Hari":str(r[1]),"Tanggal":str(r[2]),"Jam":str(r[3]),"Sumber/Jenis":str(r[4]),"Nominal":str(r[5]),"Keterangan":str(r[6])})
        headers=list(datas[0].keys())
        for col_idx,h in enumerate(headers,1):
            cell=ws.cell(row=1,column=col_idx,value=h); cell.font=Font(bold=True,color="FFFFFF",size=12); cell.fill=PatternFill(start_color="00796B",end_color="00796B",fill_type="solid"); cell.alignment=Alignment(horizontal="center",vertical="center")
        for r_idx,row in enumerate(datas,2):
            for c_idx,h in enumerate(headers,1): ws.cell(row=r_idx,column=c_idx,value=str(row.get(h,"")))
        ws.freeze_panes="A2"; ws.auto_filter.ref=ws.dimensions
        thin=Side(style="thin",color="B2DFDB"); border=Border(left=thin,right=thin,top=thin,bottom=thin)
        for r in range(1,len(datas)+2):
            for c in range(1,len(headers)+1): ws.cell(row=r,column=c).border=border
        bio=io.BytesIO(); wb.save(bio); bio.seek(0); return bio.getvalue()
    except Exception as e: st.error(f"Gagal XLSX: {e}"); return None

# === BARU: FUNGSI CARRYOVER ===
def get_sisa_bulan(pem_rows, peng_rows, bulan, tahun):
    total_masuk = 0
    total_keluar = 0
    for r in pem_rows:
        try:
            y,m,d=map(int,str(r[2]).split("-")[:3])
            if y==tahun and m==bulan:
                total_masuk += parse_nominal(r[5])
        except: pass
    for r in peng_rows:
        try:
            y,m,d=map(int,str(r[2]).split("-")[:3])
            if y==tahun and m==bulan:
                total_keluar += parse_nominal(r[5])
        except: pass
    return total_masuk - total_keluar, total_masuk, total_keluar

def buat_xlsx_rekap_bulanan(pem_rows, peng_rows, bulan_pilih, tahun_pilih):
    """
    LOGIKA BARU SESUAI REQUEST:
    Sisa bulan sebelumnya ditambah ke pemasukan bulan berikutnya
    Pemasukan Efektif = Pemasukan Bulan Ini + Sisa Akumulasi Bulan Lalu
    Sisa Akhir = Pemasukan Efektif - Pengeluaran Bulan Ini
    """
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    import io

    # 1. Hitung sisa akumulasi dari semua bulan sebelum bulan_pilih (lintas tahun)
    sisa_bulan_lalu = 0
    for th in range(2024, tahun_pilih+1):
        batas_bulan = (bulan_pilih-1) if th==tahun_pilih else 12
        for b in range(1, batas_bulan+1):
            sisa_b, _, _ = get_sisa_bulan(pem_rows, peng_rows, b, th)
            sisa_bulan_lalu += sisa_b

    # 2. Data bulan yang dipilih
    _, total_masuk_murni, total_keluar = get_sisa_bulan(pem_rows, peng_rows, bulan_pilih, tahun_pilih)

    # 3. Rumus baru
    total_masuk_efektif = total_masuk_murni + sisa_bulan_lalu
    sisa_akhir = total_masuk_efektif - total_keluar

    jml_masuk = sum(1 for r in pem_rows if str(r[2]).startswith(f"{tahun_pilih}-{bulan_pilih:02d}"))
    jml_keluar = sum(1 for r in peng_rows if str(r[2]).startswith(f"{tahun_pilih}-{bulan_pilih:02d}"))

    # 4. Buat Excel
    wb = Workbook()
    ws = wb.active
    ws.title = f"Rekap {bulan_pilih:02d}-{tahun_pilih}"

    ws.append(["Keterangan", "Nominal Rp", "Detail"])
    ws.append([f"Sisa Akumulasi s/d {bulan_pilih-1:02d}/{tahun_pilih}", sisa_bulan_lalu, f"Total sisa bulan-bulan sebelumnya"])
    ws.append([f"Pemasukan Murni {bulan_pilih:02d}/{tahun_pilih}", total_masuk_murni, f"{jml_masuk} transaksi"])
    ws.append([f"Pemasukan Efektif = Murni + Sisa Lalu", total_masuk_efektif, f"{total_masuk_murni} + {sisa_bulan_lalu}"])
    ws.append([f"Pengeluaran {bulan_pilih:02d}/{tahun_pilih}", total_keluar, f"{jml_keluar} transaksi"])
    ws.append([f"SISA UANG AKHIR {bulan_pilih:02d}/{tahun_pilih}", sisa_akhir, f"{total_masuk_efektif} - {total_keluar}"])

    # Sheet detail
    ws2 = wb.create_sheet(f"Detail {bulan_pilih:02d}-{tahun_pilih}")
    ws2.append(["Tipe", "Hari", "Tanggal", "Jam", "Sumber/Jenis", "Nominal", "Keterangan"])
    for r in pem_rows:
        try:
            if str(r[2]).startswith(f"{tahun_pilih}-{bulan_pilih:02d}"):
                ws2.append(["Pemasukan", r[1], str(r[2]), str(r[3]), r[4], r[5], r[6]])
        except: pass
    for r in peng_rows:
        try:
            if str(r[2]).startswith(f"{tahun_pilih}-{bulan_pilih:02d}"):
                ws2.append(["Pengeluaran", r[1], str(r[2]), str(r[3]), r[4], r[5], r[6]])
        except: pass

    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio.getvalue(), total_masuk_efektif, total_keluar, sisa_akhir, jml_masuk, jml_keluar, sisa_bulan_lalu, total_masuk_murni

# === SESSION STATE INIT ===
if "logged" not in st.session_state: st.session_state.logged = False
if "page" not in st.session_state: st.session_state.page = "home"
if "just_saved" not in st.session_state: st.session_state.just_saved = False
if "saved_msg" not in st.session_state: st.session_state.saved_msg = ""
if "form_key" not in st.session_state: st.session_state.form_key = 0
if "edit_lock_id" not in st.session_state: st.session_state.edit_lock_id = None
if "rekap_data" not in st.session_state: st.session_state.rekap_data = None

init_tables()

# === LOGIN TENGAH + ENTER + PERINGATAN SALAH ===
if not st.session_state.logged:
    _, col_login, _ = st.columns([1, 1, 1])
    with col_login:
        st.title("Login Keuangan MySQL")
        with st.form("login_form", clear_on_submit=False):
            u = st.text_input("Username"); p = st.text_input("Password", type="password")
            login_klik = st.form_submit_button("Login", use_container_width=True)
        if login_klik:
            if u == LOGIN_USER and p == LOGIN_PASS: st.session_state.logged = True; st.rerun()
            else: st.error("Username atau Password salah, silahkan ulangi kembali")
    st.stop()

# === HOME ===
if st.session_state.page=="home":
    if st.session_state.just_saved: st.balloons(); st.success(st.session_state.saved_msg); st.toast(st.session_state.saved_msg, icon="🎉"); play_success_sound(st.session_state.saved_msg); st.session_state.just_saved=False
    pem_rows, peng_rows, _, _ = load_mysql()
    st.markdown("<h1 style='text-align:center'>💰 Pemasukan dan Pengeluaran - MySQL + BUDGET 3D</h1>", unsafe_allow_html=True)
    st.success(f"✅ MySQL Connected! - {len(pem_rows)} Pemasukan, {len(peng_rows)} Pengeluaran - BUDGET 3D")
    apply_beda_warna()
    c1,c2 = st.columns(2)
    with c1:
        if st.button("🟢 BUKA PEMASUKAN 3D", use_container_width=True): st.session_state.page="pemasukan"; st.rerun()
    with c2:
        if st.button("🔴 BUKA PENGELUARAN 3D", use_container_width=True): st.session_state.page="pengeluaran"; st.rerun()
    if st.button("📊 BUKA DASHBOARD BUDGET 3D", use_container_width=True): st.session_state.page="dashboard"; st.rerun()
    if st.button("🚪 LOGOUT 3D", use_container_width=True): st.session_state.logged=False; st.rerun()
    col1,col2=st.columns(2)
    with col1:
        st.markdown(f"#### 💚 Pemasukan Terbaru - {len(pem_rows)} Data (Scroll)")
        if pem_rows: 
            st.dataframe([{"No":i,"Sumber":r[4],"Nominal":r[5],"Tanggal":str(r[2])} for i,r in enumerate(pem_rows)], use_container_width=True, height=350)
            st.caption(f"📜 Scroll: {len(pem_rows)} data, tinggi tetap 10 baris")
        else: st.info("Belum ada data")
    with col2:
        st.markdown(f"#### ❤️ Pengeluaran Terbaru - {len(peng_rows)} Data (Scroll)")
        if peng_rows: 
            st.dataframe([{"No":i,"Kategori":r[4],"Nominal":r[5],"Tanggal":str(r[2])} for i,r in enumerate(peng_rows)], use_container_width=True, height=350)
            st.caption(f"📜 Scroll: {len(peng_rows)} data, tinggi tetap 10 baris")
        else: st.info("Belum ada data")
    st.divider()
    ex1, ex2 = st.columns(2)
    with ex1:
        if pem_rows:
            xlsx_masuk = buat_xlsx(pem_rows, True)
            if xlsx_masuk: st.download_button(f"📥 Excel Pemasukan ({len(pem_rows)})", xlsx_masuk, f"pemasukan_{today_wib()}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="home_xlsx_masuk2")
    with ex2:
        if peng_rows:
            xlsx_keluar = buat_xlsx(peng_rows, False)
            if xlsx_keluar: st.download_button(f"📥 Excel Pengeluaran ({len(peng_rows)})", xlsx_keluar, f"pengeluaran_{today_wib()}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="home_xlsx_keluar2")
    st.divider()
    st.markdown("### 📅 REKAP BULANAN - Sisa Uang (Carryover)")
    c_bulan, c_tahun, c_btn = st.columns([1,1,2])
    with c_bulan: bulan_pilih = st.selectbox("Bulan", list(range(1,13)), index=now_wib().month-1, format_func=lambda x: f"{x:02d} - {['Jan','Feb','Mar','Apr','Mei','Jun','Jul','Ags','Sep','Okt','Nov','Des'][x-1]}")
    with c_tahun: tahun_pilih = st.selectbox("Tahun", list(range(2024,2030)), index=2)
    with c_btn:
        st.write(""); st.write("")
        if st.button("📊 HITUNG REKAP BULANAN 3D", use_container_width=True):
            xlsx_bytes, total_masuk_efektif, total_keluar, sisa, jml_masuk, jml_keluar, sisa_lalu, total_masuk_murni = buat_xlsx_rekap_bulanan(pem_rows, peng_rows, bulan_pilih, tahun_pilih)
            st.session_state.rekap_data = (xlsx_bytes, total_masuk_efektif, total_keluar, sisa, jml_masuk, jml_keluar, bulan_pilih, tahun_pilih, sisa_lalu, total_masuk_murni)
    if st.session_state.rekap_data is not None:
        xlsx_bytes, total_masuk_efektif, total_keluar, sisa, jml_masuk, jml_keluar, bulan_pilih, tahun_pilih, sisa_lalu, total_masuk_murni = st.session_state.rekap_data
        if xlsx_bytes:
            m1,m2,m3 = st.columns(3)
            with m1: st.metric(f"Pemasukan {bulan_pilih:02d}/{tahun_pilih} (Efektif)", f"{format_rp_id(total_masuk_efektif)}", f"{jml_masuk} trx | Murni {format_rp_id(total_masuk_murni)} + Sisa lalu {format_rp_id(sisa_lalu)}")
            with m2: st.metric(f"Pengeluaran {bulan_pilih:02d}/{tahun_pilih}", f"{format_rp_id(total_keluar)}", f"{jml_keluar} transaksi")
            with m3: st.metric(f"SISA UANG {bulan_pilih:02d}/{tahun_pilih}", f"{format_rp_id(sisa)}", f"{sisa}")
            if sisa >=0: st.success(f"✅ SISA UANG BULAN {bulan_pilih:02d}/{tahun_pilih}: {format_rp_id(sisa)} = ({format_rp_id(total_masuk_murni)} + Sisa lalu {format_rp_id(sisa_lalu)}) - {format_rp_id(total_keluar)} | Pemasukan Efektif {format_rp_id(total_masuk_efektif)} - Pengeluaran {format_rp_id(total_keluar)}")
            else: st.error(f"⚠️ SISA MINUS: {format_rp_id(sisa)} = ({format_rp_id(total_masuk_murni)} + {format_rp_id(sisa_lalu)}) - {format_rp_id(total_keluar)}")
            st.markdown('---')
            st.info('🔍 DEBUG: Grafik akan muncul di bawah ini - Scroll ke bawah!')
            st.download_button(f"📥 Download REKAP BULANAN {bulan_pilih:02d}-{tahun_pilih} XLSX - Sisa {format_rp_id(sisa)}", xlsx_bytes, file_name=f"rekap_bulanan_{bulan_pilih:02d}_{tahun_pilih}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="rekap_bulanan")

            # === GRAFIK SMOOTH - TANPA PLOTLY, PAKAI MATPLOTLIB + NATIVE CHART ===
            st.divider()
            st.markdown(f"### 📈 TREND SALDO SMOOTH - Carryover s/d {bulan_pilih:02d}/{tahun_pilih}")
            trend_data = []
            sisa_akum = 0
            for th in range(2024, tahun_pilih+1):
                batas = (bulan_pilih if th==tahun_pilih else 12)
                for b in range(1, batas+1):
                    sisa_b, masuk_b, keluar_b = get_sisa_bulan(pem_rows, peng_rows, b, th)
                    if masuk_b==0 and keluar_b==0:
                        if not (th==tahun_pilih and b==bulan_pilih):
                            if len(trend_data)==0:
                                continue
                            continue
                    efektif_b = masuk_b + sisa_akum
                    sisa_akhir_b = efektif_b - keluar_b
                    trend_data.append({"Bulan": f"{th}-{b:02d}", "Murni": masuk_b, "Sisa Lalu": sisa_akum, "Efektif": efektif_b, "Keluar": keluar_b, "Sisa Akhir": sisa_akhir_b})
                    sisa_akum = sisa_akhir_b

            if trend_data:
                st.dataframe([{"Bulan": d["Bulan"], "Murni": format_rp_id(d["Murni"]), "Sisa Lalu": format_rp_id(d["Sisa Lalu"]), "Efektif": format_rp_id(d["Efektif"]), "Keluar": format_rp_id(d["Keluar"]), "Sisa Akhir": format_rp_id(d["Sisa Akhir"])} for d in trend_data], use_container_width=True)
                
                # 1. Native Streamlit chart - pasti muncul tanpa plotly
                chart_data = {d["Bulan"]: d["Sisa Akhir"] for d in trend_data}
                st.markdown("#### 💙 Grafik Sisa Akhir - Native (Tanpa Plotly)")
                st.line_chart(chart_data, height=300)
                st.area_chart(chart_data, height=250)

                # 2. Matplotlib smooth dengan gradient
                try:
                    import matplotlib.pyplot as plt
                    import numpy as np
                    labels = [d["Bulan"] for d in trend_data]
                    sisa_vals = [d["Sisa Akhir"] for d in trend_data]
                    efektif_vals = [d["Efektif"] for d in trend_data]
                    keluar_vals = [d["Keluar"] for d in trend_data]
                    
                    fig, ax = plt.subplots(figsize=(12, 5))
                    x = np.arange(len(labels))
                    
                    # Smooth dengan spline jika ada scipy, kalau tidak pakai linear
                    try:
                        from scipy.interpolate import make_interp_spline
                        x_new = np.linspace(x.min(), x.max(), 300)
                        if len(x) > 2:
                            spl_sisa = make_interp_spline(x, sisa_vals, k=2)
                            sisa_smooth = spl_sisa(x_new)
                            spl_ef = make_interp_spline(x, efektif_vals, k=2)
                            ef_smooth = spl_ef(x_new)
                            spl_kel = make_interp_spline(x, keluar_vals, k=2)
                            kel_smooth = spl_kel(x_new)
                        else:
                            x_new = x
                            sisa_smooth = sisa_vals
                            ef_smooth = efektif_vals
                            kel_smooth = keluar_vals
                    except:
                        x_new = x
                        sisa_smooth = sisa_vals
                        ef_smooth = efektif_vals
                        kel_smooth = keluar_vals

                    # Gradient area
                    ax.fill_between(x_new, sisa_smooth, alpha=0.25, color='dodgerblue', label='Sisa Akhir Area')
                    ax.fill_between(x_new, ef_smooth, alpha=0.15, color='green', label='Efektif Area')
                    ax.plot(x_new, sisa_smooth, color='dodgerblue', linewidth=3, marker='o', markersize=6, label='SISA AKHIR Smooth', markerfacecolor='white', markeredgewidth=2)
                    ax.plot(x_new, ef_smooth, color='green', linewidth=2, linestyle='--', alpha=0.8, label='Efektif')
                    ax.plot(x_new, kel_smooth, color='red', linewidth=2, linestyle=':', alpha=0.7, label='Pengeluaran')

                    # Label nilai
                    for i, (lbl, val) in enumerate(zip(labels, sisa_vals)):
                        ax.text(x[i], val + max(sisa_vals)*0.05, format_rp_id(val), ha='center', fontsize=8, color='darkblue', fontweight='bold')

                    ax.set_xticks(x)
                    ax.set_xticklabels(labels, rotation=25, fontsize=9)
                    ax.set_ylabel('Rupiah')
                    ax.set_title(f'💎 TREND CARRYOVER SMOOTH - {trend_data[0]["Bulan"]} s/d {trend_data[-1]["Bulan"]}', fontsize=14, fontweight='bold', pad=20)
                    ax.grid(True, alpha=0.3)
                    ax.legend()
                    plt.tight_layout()
                    st.pyplot(fig, use_container_width=True)
                    plt.close()
                    st.success(f"✅ Grafik smooth muncul! Oktober {format_rp_id(trend_data[-2]['Sisa Akhir']) if len(trend_data)>=2 else '-'} → November {format_rp_id(trend_data[-1]['Sisa Akhir'])} - Biru gradient profesional!")
                except Exception as e:
                    st.warning(f"Matplotlib error: {e}")
                    # Fallback tetap native chart di atas sudah muncul

                # 3. Coba Plotly jika ada, tanpa error
                try:
                    import plotly.graph_objects as go
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=[d["Bulan"] for d in trend_data], y=[d["Efektif"] for d in trend_data], mode='lines', name='Efektif', line=dict(color='rgba(46,213,115,0.8)', width=2, shape='spline', smoothing=1.3), fill='tozeroy', fillcolor='rgba(46,213,115,0.15)'))
                    fig.add_trace(go.Scatter(x=[d["Bulan"] for d in trend_data], y=[d["Keluar"] for d in trend_data], mode='lines', name='Keluar', line=dict(color='rgba(255,71,87,0.9)', width=2, shape='spline', smoothing=1.3, dash='dot')))
                    fig.add_trace(go.Scatter(x=[d["Bulan"] for d in trend_data], y=[d["Sisa Akhir"] for d in trend_data], mode='lines+markers+text', name='SISA', line=dict(color='rgba(30,144,255,1)', width=4, shape='spline', smoothing=1.3), marker=dict(size=10, color='white', line=dict(color='dodgerblue', width=3)), text=[format_rp_id(d["Sisa Akhir"]) for d in trend_data], textposition="top center", fill='tozeroy', fillcolor='rgba(30,144,255,0.12)'))
                    fig.update_layout(height=550, hovermode='x unified')
                    st.plotly_chart(fig, use_container_width=True)
                except:
                    st.caption("ℹ️ Plotly tidak terinstall, pakai grafik matplotlib di atas (sudah smooth). Install dengan: pip install plotly")
    st.stop()


# === DASHBOARD ===
if st.session_state.page=="dashboard":
    pem_rows, peng_rows, _, _ = load_mysql()
    st.markdown("<h1 style='text-align:center'>📊 DASHBOARD BUDGET 3D - Jajan 25k + Makan Luar 50k</h1>", unsafe_allow_html=True)
    apply_beda_warna()
    d1,d2,d3,d4 = st.columns(4)
    with d1:
        if st.button("🏠 HOME 3D", use_container_width=True, key="dash_home"): st.session_state.page="home"; st.rerun()
    with d2:
        if st.button("🟢 Pemasukan 3D", use_container_width=True, key="dash_masuk"): st.session_state.page="pemasukan"; st.rerun()
    with d3:
        if st.button("🔴 Pengeluaran 3D", use_container_width=True, key="dash_keluar"): st.session_state.page="pengeluaran"; st.rerun()
    with d4:
        if st.button("🚪 LOGOUT 3D", use_container_width=True, key="dash_logout"): st.session_state.logged=False; st.session_state.page="home"; st.rerun()
    
    total_masuk = sum(parse_nominal(r[5]) for r in pem_rows); total_keluar = sum(parse_nominal(r[5]) for r in peng_rows); sisa = total_masuk - total_keluar

    st.markdown("### 📅 PILIH BULAN BUDGET - Data Lama Tetap Ada!")
    col_b1, col_b2, col_b3 = st.columns([1,1,2])
    with col_b1:
        bulan_budget = st.selectbox("Bulan Budget", list(range(1,13)), index=now_wib().month-1, format_func=lambda x: f"{x:02d}", key="bulan_budget")
    with col_b2:
        tahun_budget = st.selectbox("Tahun Budget", list(range(2024,2030)), index=2, key="tahun_budget")
    with col_b3:
        st.info(f"💾 Data Oktober tetap aman! Filter hanya untuk hitung budget bulan {bulan_budget:02d}/{tahun_budget}")
    
    def match_bulan_budget(r):
        try:
            y,m,d=map(int,str(r[2]).split("-")[:3])
            return y==tahun_budget and m==bulan_budget
        except: return False
    
    peng_rows_bulan = [r for r in peng_rows if match_bulan_budget(r)]
    pem_rows_bulan = [r for r in pem_rows if match_bulan_budget(r)]
    
    agg_all = defaultdict(int)
    for r in peng_rows_bulan: agg_all[str(r[4]).strip()] += parse_nominal(r[5])
    jajan_total = agg_all.get("Jajan", 0)
    makan_luar_total = agg_all.get("Makan di luar", 0)
    controllable_total = jajan_total + makan_luar_total
    total_keluar_bulan = sum(parse_nominal(r[5]) for r in peng_rows_bulan)
    uncontrollable_total = total_keluar_bulan - controllable_total
    jajan_sisa = BUDGET_JAJAN - jajan_total
    makan_sisa = BUDGET_MAKAN_LUAR - makan_luar_total
    
    agg_all_time = defaultdict(int)
    for r in peng_rows: agg_all_time[str(r[4]).strip()] += parse_nominal(r[5])
    st.caption(f"📊 Data total semua bulan: {len(pem_rows)} pemasukan, {len(peng_rows)} pengeluaran | Filter bulan {bulan_budget:02d}/{tahun_budget}: {len(pem_rows_bulan)} pemasukan, {len(peng_rows_bulan)} pengeluaran")
    
    st.markdown(f"### 🚨 BATAS BUDGET CONTROLLABLE - {bulan_budget:02d}/{tahun_budget} - Anti Boros! (Data lama tetap ada)")
    b1,b2,b3,b4 = st.columns(4)
    with b1:
        if jajan_total <= BUDGET_JAJAN:
            st.metric("🍿 Jajan", format_rp_id(jajan_total), f"Sisa {format_rp_id(jajan_sisa)} dari {format_rp_id(BUDGET_JAJAN)}")
            st.progress(min(jajan_total / BUDGET_JAJAN, 1.0))
        else:
            st.error(f"🍿 Jajan OVER! {format_rp_id(jajan_total)} / {format_rp_id(BUDGET_JAJAN)} OVER {format_rp_id(-jajan_sisa)}")
            st.progress(1.0)
    with b2:
        if makan_luar_total <= BUDGET_MAKAN_LUAR:
            st.metric("🍜 Makan di luar", format_rp_id(makan_luar_total), f"Sisa {format_rp_id(makan_sisa)} dari {format_rp_id(BUDGET_MAKAN_LUAR)}")
            st.progress(min(makan_luar_total / BUDGET_MAKAN_LUAR, 1.0))
        else:
            st.error(f"🍜 Makan di luar OVER! {format_rp_id(makan_luar_total)} / {format_rp_id(BUDGET_MAKAN_LUAR)} OVER {format_rp_id(-makan_sisa)}")
            st.progress(1.0)
    with b3:
        st.metric("🎛️ Controllable", format_rp_id(controllable_total), f"{len(CONTROLLABLE)} jenis")
        if controllable_total > (BUDGET_JAJAN + BUDGET_MAKAN_LUAR):
            st.warning(f"OVER BUDGET! {format_rp_id(controllable_total)} > {format_rp_id(BUDGET_JAJAN + BUDGET_MAKAN_LUAR)}")
    with b4:
        st.metric("🔒 Uncontrollable", format_rp_id(uncontrollable_total), f"Wajib - {len(UNCONTROLLABLE)} jenis")
    
    if jajan_total > BUDGET_JAJAN or makan_luar_total > BUDGET_MAKAN_LUAR:
        st.error(f"🚨 ALERT: Budget {bulan_budget:02d}/{tahun_budget} controllable jebol! Kurangi jajan / makan di luar atau pakai dana darurat sakit! (Data bulan lain tetap aman)")
    else:
        if len(peng_rows_bulan) == 0:
            st.info(f"📭 Belum ada data pengeluaran bulan {bulan_budget:02d}/{tahun_budget}. Mulai kontrol full bulan ini bro! Data Oktober tetap ada di database.")
        else:
            st.success(f"✅ Aman bulan {bulan_budget:02d}/{tahun_budget}! Controllable masih dalam batas. Sisa budget jajan {format_rp_id(jajan_sisa)} + makan luar {format_rp_id(makan_sisa)} = {format_rp_id(jajan_sisa + makan_sisa)} bisa buat dana darurat sakit!")
    
    st.info("💡 Antisipasi sakit: Walaupun bawa bekal, budget makan luar Rp50k disisakan Rp10k-15k untuk warteg kalau sakit / gak sempat masak. Jajan Rp25k untuk obat ringan / teh hangat.")
    
    st.markdown("### 📊 GRAFIK CONTROLLABLE vs UNCONTROLLABLE")
    cc1, cc2 = st.columns(2)
    with cc1:
        try:
            import plotly.express as px
            data_ctrl = [{"Kategori": "Controllable (Jajan+Makan Luar)", "Nominal": controllable_total}, {"Kategori": "Uncontrollable (Wajib)", "Nominal": uncontrollable_total}]
            fig_ctrl = px.pie(data_ctrl, values="Nominal", names="Kategori", title="Controllable vs Uncontrollable", color_discrete_sequence=["orange", "steelblue"])
            st.plotly_chart(fig_ctrl, use_container_width=True)
        except: st.bar_chart({"Controllable": controllable_total, "Uncontrollable": uncontrollable_total})
        fig_3d_ctrl = plot_controllable_3d({"Jajan": jajan_total, "Makan di luar": makan_luar_total}, {k: v for k,v in agg_all.items() if k not in CONTROLLABLE})
        if fig_3d_ctrl:
            st.pyplot(fig_3d_ctrl, use_container_width=True)
    with cc2:
        try:
            import plotly.graph_objects as go
            fig = go.Figure()
            fig.add_trace(go.Bar(x=["Jajan", "Makan di luar"], y=[jajan_total, makan_luar_total], name="Controllable", marker_color=["orange", "gold"], text=[format_rp_id(jajan_total), format_rp_id(makan_luar_total)], textposition='outside'))
            fig.add_trace(go.Bar(x=["Jajan Budget", "Makan Luar Budget"], y=[BUDGET_JAJAN, BUDGET_MAKAN_LUAR], name="Budget Max", marker_color=["lightgreen", "lightblue"], text=[format_rp_id(BUDGET_JAJAN), format_rp_id(BUDGET_MAKAN_LUAR)], textposition='outside'))
            fig.update_layout(title="Budget vs Realisasi - Controllable", barmode='group', height=400)
            st.plotly_chart(fig, use_container_width=True)
        except: pass
        st.dataframe([{"Jenis": k, "Total": format_rp_id(v), "Kategori": "Controllable" if k in CONTROLLABLE else "Uncontrollable", "Budget": format_rp_id(BUDGET_JAJAN) if k=="Jajan" else format_rp_id(BUDGET_MAKAN_LUAR) if k=="Makan di luar" else "-", "Sisa": format_rp_id(jajan_sisa) if k=="Jajan" else format_rp_id(makan_sisa) if k=="Makan di luar" else "-"} for k,v in sorted(agg_all.items(), key=lambda x: x[1], reverse=True)], use_container_width=True)
    
    st.divider()
    m1,m2,m3 = st.columns(3)
    with m1: st.metric("💚 Total Pemasukan", format_rp_id(total_masuk), f"{len(pem_rows)} transaksi")
    with m2: st.metric("❤️ Total Pengeluaran", format_rp_id(total_keluar), f"{len(peng_rows)} transaksi")
    with m3: st.metric("💰 Sisa Uang Real-Time", format_rp_id(sisa), f"{len(pem_rows)+len(peng_rows)} data")
    st.divider()
    c_left, c_right = st.columns(2)
    with c_left:
        st.markdown("### 🟢 Grafik Sumber Pemasukan 3D")
        if pem_rows:
            agg = defaultdict(int)
            for r in pem_rows: agg[str(r[4]).strip() or "Tanpa Sumber"] += parse_nominal(r[5])
            data_pem = [{"Sumber": k, "Nominal": v} for k,v in agg.items()]; data_pem = sorted(data_pem, key=lambda x: x["Nominal"], reverse=True)
            st.dataframe(data_pem, use_container_width=True)
            fig_mpl, fig_plotly = plot_3d_bar(data_pem, "🔥 PEMASUKAN 3D - per Sumber")
            if fig_mpl: st.pyplot(fig_mpl, use_container_width=True)
            elif fig_plotly: st.plotly_chart(fig_plotly, use_container_width=True)
            try:
                import plotly.express as px
                fig = px.bar(data_pem, x="Sumber", y="Nominal", color="Sumber", title="Pemasukan per Sumber (2D)", text="Nominal"); fig.update_layout(height=400); st.plotly_chart(fig, use_container_width=True)
                fig2 = px.pie(data_pem, values="Nominal", names="Sumber", title="Distribusi Pemasukan"); st.plotly_chart(fig2, use_container_width=True)
            except: st.bar_chart({d["Sumber"]: d["Nominal"] for d in data_pem})
        else: st.info("Belum ada data pemasukan")
    with c_right:
        st.markdown("### 🔴 Grafik Jenis Pengeluaran 3D")
        if peng_rows:
            agg2 = defaultdict(int)
            for r in peng_rows: agg2[str(r[4]).strip() or "Tanpa Kategori"] += parse_nominal(r[5])
            data_peng = [{"Jenis": k, "Nominal": v} for k,v in agg2.items()]; data_peng = sorted(data_peng, key=lambda x: x["Nominal"], reverse=True)
            st.dataframe(data_peng, use_container_width=True)
            fig_mpl2, fig_plotly2 = plot_3d_bar(data_peng, "🔥 PENGELUARAN 3D - per Jenis")
            if fig_mpl2: st.pyplot(fig_mpl2, use_container_width=True)
            elif fig_plotly2: st.plotly_chart(fig_plotly2, use_container_width=True)
            try:
                import plotly.express as px
                fig = px.bar(data_peng, x="Jenis", y="Nominal", color="Jenis", title="Pengeluaran per Jenis (2D)", text="Nominal"); fig.update_layout(height=400); st.plotly_chart(fig, use_container_width=True)
                fig2 = px.pie(data_peng, values="Nominal", names="Jenis", title="Distribusi Pengeluaran"); st.plotly_chart(fig2, use_container_width=True)
            except: st.bar_chart({d["Jenis"]: d["Nominal"] for d in data_peng})
        else: st.info("Belum ada data pengeluaran")
    st.stop()

# === HALAMAN INPUT ===
def halaman(tipe):
    is_masuk = tipe=="pemasukan"
    pem_rows, peng_rows, custom_rows, custom_sumber_rows = load_mysql()
    rows = pem_rows if is_masuk else peng_rows
    if st.session_state.just_saved: st.balloons(); st.success(st.session_state.saved_msg + " - Form kosong!"); st.toast(st.session_state.saved_msg, icon="🎉"); play_success_sound(st.session_state.saved_msg); st.session_state.just_saved=False
    st.markdown(f"<h1 style='text-align:center'>{'🟢' if is_masuk else '🔴'} {tipe.upper()} - MySQL</h1>", unsafe_allow_html=True)
    apply_beda_warna()
    n1,n2,n3,n4 = st.columns(4)
    with n1:
        if st.button("🏠 HOME 3D", use_container_width=True, key=f"h1_{tipe}"): st.session_state.page="home"; st.rerun()
    with n2:
        t = "pengeluaran" if is_masuk else "pemasukan"
        if st.button(f"🔄 Ke {t.capitalize()} 3D", use_container_width=True, key=f"h2_{tipe}"): st.session_state.page=t; st.rerun()
    with n3:
        if st.button("📊 Data Dashboard 3D", use_container_width=True, key=f"h3_{tipe}"): st.session_state.page="dashboard"; st.rerun()
    with n4:
        if st.button("🚪 LOGOUT 3D", use_container_width=True, key=f"h4_{tipe}"): st.session_state.logged=False; st.session_state.page="home"; st.rerun()
    nom_list = get_nom_list(custom_rows, tipe)
    st.caption(f"🕐 Sekarang WIB: {now_wib().strftime('%A %d/%m/%Y %H:%M')} - Kalau tab sudah lama kebuka, klik Refresh dulu!")
    if st.button("🔄 Refresh Hari / Tanggal / Jam Sekarang (WIB)", use_container_width=True, key=f"refresh_wib_{tipe}"):
        st.session_state.form_key += 1; st.rerun()
    with st.container(border=True):
        st.markdown(f"### Form {tipe.capitalize()} - Dropdown 3D")
        col_kiri, col_kanan = st.columns(2)
        with col_kiri:
            hari = st.selectbox("Hari Indonesia", HARI, index=now_wib().weekday(), key=f"hari_{tipe}_{st.session_state.form_key}")
            tgl = st.date_input("Tanggal", value=today_wib(), format="DD/MM/YYYY", key=f"tgl_{tipe}_{st.session_state.form_key}")
            jam = st.time_input("Jam", value=now_wib().time(), key=f"jam_{tipe}_{st.session_state.form_key}")
        with col_kanan:
            sumber = ""; sumber_custom_input = ""
            if is_masuk:
                sumber_list = get_sumber_list(custom_sumber_rows)
                selected_sumber = st.selectbox("Sumber Pemasukan (Dropdown)", sumber_list, key=f"sumber_{tipe}_{st.session_state.form_key}")
                if "Dll" in selected_sumber:
                    sumber_custom_input = st.text_input("💡 Input Sumber Baru - Jadi dropdown permanen!", placeholder="Unit 12AB", key=f"sumber_custom_{tipe}_{st.session_state.form_key}")
                    if sumber_custom_input.strip(): sumber=sumber_custom_input.strip(); st.success(f"✅ {sumber} akan jadi dropdown permanen!")
                    else: sumber=""; st.warning("Ketik sumber baru!")
                else: sumber=selected_sumber
            else:
                jenis_list = get_jenis_pengeluaran_list(custom_sumber_rows)
                selected_jenis = st.selectbox("Jenis Pengeluaran (Dropdown)", jenis_list, key=f"sumber_{tipe}_{st.session_state.form_key}")
                if "Dll" in selected_jenis:
                    sumber_custom_input = st.text_input("💡 Input Jenis Pengeluaran Baru - Jadi dropdown permanen!", placeholder="Beli Pulsa", key=f"sumber_custom_{tipe}_{st.session_state.form_key}")
                    if sumber_custom_input.strip(): sumber=sumber_custom_input.strip(); st.success(f"✅ {sumber} akan jadi dropdown permanen!")
                    else: sumber=""; st.warning("Ketik jenis baru!")
                else: sumber=selected_jenis
            selected_nom = st.selectbox("Nominal (Pilih Dll untuk custom)", nom_list, key=f"nom_{tipe}_{st.session_state.form_key}")
            final_nom = selected_nom; custom_input=""
            if "Dll" in selected_nom:
                custom_input = st.text_input("💡 Isi Nominal Baru misal Rp4.000,00 - jadi dropdown permanen!", placeholder="Rp4.000,00", key=f"custom_{tipe}_{st.session_state.form_key}")
                if custom_input.strip(): final_nom=custom_input.strip(); st.success(f"✅ {final_nom} akan jadi dropdown permanen!")
                else: final_nom=""; st.warning("Ketik Rp4.000,00!")
            ket = st.text_area("Keterangan *WAJIB DIISI - Tidak Boleh Kosong!*", height=100, placeholder="WAJIB ISI! Contoh: tips dari unit 20GA", key=f"ket_{tipe}_{st.session_state.form_key}")
            if ket.strip()=="": st.error("⛔ KETERANGAN BELUM DIISI! Wajib isi keterangan dulu, tidak boleh kosong!")
        if st.button(f"💾 SIMPAN {tipe.upper()} 3D", use_container_width=True, key=f"btn_simpan_{tipe}_{st.session_state.form_key}"):
            if ket.strip()=="": st.error("⛔ GAGAL SIMPAN! Keterangan masih kosong! Isi keterangan dulu - tidak boleh ada kolom kosong!")
            elif sumber.strip()=="": st.warning("Pilih sumber/jenis dulu!")
            elif "Dll" in selected_nom and custom_input.strip()=="": st.warning("Isi dulu nominal barunya!")
            elif final_nom=="": st.warning("Pilih nominal dulu!")
            else:
                is_dup=False
                if rows:
                    last=rows[0]
                    if str(last[4]).strip()==sumber.strip() and str(last[5]).strip()==final_nom.strip() and str(last[6]).strip()==ket.strip() and str(last[2])==str(tgl): is_dup=True
                if is_dup: st.error("⚠️ Duplikat! Sudah ada data sama!")
                else:
                    try:
                        hari_fix=HARI[tgl.weekday()]; conn=get_conn(); cur=conn.cursor()
                        if is_masuk: cur.execute("INSERT INTO pemasukan (hari,tanggal,jam,sumber,nominal,keterangan) VALUES (%s,%s,%s,%s,%s,%s)", (hari_fix,tgl,jam,sumber.strip(),final_nom,ket.strip()))
                        else: cur.execute("INSERT INTO pengeluaran (hari,tanggal,jam,kategori,nominal,keterangan) VALUES (%s,%s,%s,%s,%s,%s)", (hari_fix,tgl,jam,sumber.strip(),final_nom,ket.strip()))
                        if "Dll" in selected_nom and final_nom not in NOMINAL and final_nom.strip()!="": cur.execute("INSERT IGNORE INTO custom_nominal (jenis,nominal) VALUES (%s,%s)", (tipe,final_nom))
                        if sumber_custom_input and sumber_custom_input.strip()!="": cur.execute("INSERT IGNORE INTO custom_sumber (jenis,sumber) VALUES (%s,%s)", (tipe,sumber_custom_input.strip()))
                        conn.commit(); conn.close()
                        st.session_state.just_saved=True; st.session_state.saved_msg=f"✅ {tipe.capitalize()} {final_nom} - {sumber} tersimpan!"; st.session_state.form_key+=1; st.rerun()
                    except Exception as e: st.error(f"MySQL Error: {e}")
    datas_bawah = pem_rows if is_masuk else peng_rows  # NGEBUT: pakai data yang sudah di-load, jangan load lagi!
    st.markdown(f"### 📊 DATA {tipe.upper()} DI BAWAH - TOTAL {len(datas_bawah)} DATA")
    if datas_bawah:
        st.metric(f"Total {tipe.capitalize()}", f"{len(datas_bawah)} data")
        display=[{"No":i,"Hari":r[1],"Tanggal":str(r[2]),"Jam":str(r[3]),"Sumber/Jenis":r[4],"Nominal":r[5],"Keterangan":r[6],"ID":r[0]} for i,r in enumerate(datas_bawah)]
        st.dataframe(display, use_container_width=True, height=300)
        xlsx=buat_xlsx(datas_bawah, is_masuk)
        if xlsx: st.download_button(f"📥 XLSX {tipe.capitalize()} ({len(datas_bawah)})", xlsx, file_name=f"{tipe}_{today_wib()}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key=f"xlsx_bawah_{tipe}")
    else: st.info("Belum ada data - input di atas dulu!")
    st.markdown("---")
    st.markdown(f"### ✏️ EDIT DATA {tipe.capitalize()}")
    if datas_bawah:
        opsi=[f"{i} - {r[2]} | {r[1]} | {r[4]} | {r[6]} | {r[5]} (ID:{r[0]})" for i,r in enumerate(datas_bawah)]
        pilih=st.selectbox(f"Pilih data {tipe}", opsi, key=f"pilih_edit_{tipe}"); idx=int(pilih.split(" - ")[0]); sel=datas_bawah[idx]
        if st.session_state.edit_lock_id is not None and sel[0]!=st.session_state.edit_lock_id: st.session_state.edit_lock_id=None
        if st.session_state.edit_lock_id==sel[0]: st.info(f"✅ No {idx} ID {sel[0]} sudah selesai UPDATE! Pilih data lain!")
        st.warning(f"Terpilih No {idx} ID {sel[0]}: {sel[4]} - {sel[5]}")
        with st.container(border=True):
            ec1,ec2=st.columns(2)
            with ec1:
                try: h_idx=HARI.index(sel[1])
                except: h_idx=0
                e_hari=st.selectbox("EDIT Hari", HARI, index=h_idx, key=f"e_hari_{tipe}_{sel[0]}")
                try: y,m,d=map(int,str(sel[2]).split("-")); e_tgl_val=date(y,m,d)
                except: e_tgl_val=today_wib()
                e_tgl=st.date_input("EDIT Tanggal", value=e_tgl_val, format="DD/MM/YYYY", key=f"e_tgl_{tipe}_{sel[0]}")
                try: parts=str(sel[3]).split(":"); e_jam_val=time(int(parts[0]), int(parts[1]), int(parts[2]) if len(parts)>2 else 0)
                except: e_jam_val=now_wib().time()
                e_jam=st.time_input("EDIT Jam", value=e_jam_val, key=f"e_jam_{tipe}_{sel[0]}")
            with ec2:
                e_sumber=sel[4]; e_sumber_custom=""
                if is_masuk:
                    e_sumber_list=get_sumber_list(custom_sumber_rows)
                    try: e_s_idx=e_sumber_list.index(sel[4])
                    except: e_s_idx=len(e_sumber_list)-1; e_sumber_list.insert(-1,sel[4])
                    e_sel_sumber=st.selectbox("EDIT Sumber Pemasukan (Dropdown)", e_sumber_list, index=e_s_idx, key=f"e_sumber_sel_{tipe}_{sel[0]}")
                    if "Dll" in e_sel_sumber:
                        e_sumber_custom=st.text_input("EDIT Sumber Baru - Jadi dropdown permanen!", value=sel[4] if sel[4] not in SUMBER_PEMASUKAN_BASE else "", key=f"e_sumber_custom_{tipe}_{sel[0]}")
                        e_sumber=e_sumber_custom.strip() if e_sumber_custom.strip() else sel[4]
                    else: e_sumber=e_sel_sumber
                else:
                    e_jenis_list=get_jenis_pengeluaran_list(custom_sumber_rows)
                    try: e_j_idx=e_jenis_list.index(sel[4])
                    except: e_j_idx=len(e_jenis_list)-1; e_jenis_list.insert(-1,sel[4])
                    e_sel_jenis=st.selectbox("EDIT Jenis Pengeluaran (Dropdown)", e_jenis_list, index=e_j_idx, key=f"e_sumber_sel_{tipe}_{sel[0]}")
                    if "Dll" in e_sel_jenis:
                        e_sumber_custom=st.text_input("EDIT Jenis Baru - Jadi dropdown permanen!", value=sel[4] if sel[4] not in JENIS_PENGELUARAN_BASE else "", key=f"e_sumber_custom_{tipe}_{sel[0]}")
                        e_sumber=e_sumber_custom.strip() if e_sumber_custom.strip() else sel[4]
                    else: e_sumber=e_sel_jenis
                e_nom_list=get_nom_list(custom_rows, tipe)
                try: e_nom_idx=e_nom_list.index(sel[5])
                except: e_nom_idx=0
                e_nom_sel=st.selectbox("EDIT Nominal", e_nom_list, index=e_nom_idx, key=f"e_nom_sel_{tipe}_{sel[0]}")
                e_final=e_nom_sel
                if "Dll" in e_nom_sel:
                    e_custom=st.text_input("EDIT Nominal Baru", value=sel[5] if sel[5] not in NOMINAL[:-1] else "", key=f"e_custom_{tipe}_{sel[0]}")
                    e_final=e_custom.strip() if e_custom.strip() else ""
                e_ket=st.text_area("EDIT Keterangan *WAJIB DIISI - Tidak Boleh Kosong!*", value=sel[6], key=f"e_ket_{tipe}_{sel[0]}")
                if e_ket.strip()=="": st.error("⛔ EDIT KETERANGAN BELUM DIISI! Wajib isi keterangan dulu!")
            b1,b2,b3=st.columns(3)
            with b1:
                if st.button(f"✅ UPDATE No {idx} ID {sel[0]}", use_container_width=True, key=f"up_{tipe}_{sel[0]}"):
                    if e_ket.strip()=="": st.error("⛔ GAGAL UPDATE! Keterangan masih kosong! Isi keterangan dulu - tidak boleh ada kolom kosong!")
                    elif st.session_state.edit_lock_id==sel[0]: st.warning(f"⚠️ No {idx} ID {sel[0]} sudah selesai UPDATE tadi! Pilih data lain!")
                    else:
                        try:
                            conn=get_conn(); cur=conn.cursor()
                            if is_masuk: cur.execute("UPDATE pemasukan SET hari=%s, tanggal=%s, jam=%s, sumber=%s, nominal=%s, keterangan=%s WHERE id=%s", (e_hari,e_tgl,e_jam,e_sumber,e_final,e_ket,sel[0]))
                            else: cur.execute("UPDATE pengeluaran SET hari=%s, tanggal=%s, jam=%s, kategori=%s, nominal=%s, keterangan=%s WHERE id=%s", (e_hari,e_tgl,e_jam,e_sumber,e_final,e_ket,sel[0]))
                            if e_sumber_custom and e_sumber_custom.strip()!="": cur.execute("INSERT IGNORE INTO custom_sumber (jenis,sumber) VALUES (%s,%s)", (tipe,e_sumber_custom.strip()))
                            conn.commit(); conn.close(); st.session_state.edit_lock_id=sel[0]; st.session_state.just_saved=True; st.session_state.saved_msg=f"✅ UPDATE No {idx} ID {sel[0]} - selesai!"; st.rerun()
                        except Exception as e: st.error(f"Gagal: {e}")
            with b2:
                if st.button(f"🗑️ HAPUS No {idx} ID {sel[0]}", use_container_width=True, key=f"del_{tipe}_{sel[0]}"):
                    try: conn=get_conn(); cur=conn.cursor(); cur.execute(f"DELETE FROM {'pemasukan' if is_masuk else 'pengeluaran'} WHERE id=%s", (sel[0],)); conn.commit(); conn.close(); st.session_state.just_saved=True; st.session_state.saved_msg=f"✅ HAPUS No {idx}"; st.rerun()
                    except Exception as e: st.error(f"Gagal: {e}")
            with b3:
                if st.button("❌ BATAL", use_container_width=True, key=f"cancel_{tipe}_{sel[0]}"): st.rerun()

if st.session_state.page=="pemasukan": halaman("pemasukan")
elif st.session_state.page=="pengeluaran": halaman("pengeluaran")

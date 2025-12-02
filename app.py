from flask import Flask, render_template, request, redirect, session, flash
from flask_mysqldb import MySQL
from datetime import datetime, date
from functools import wraps

app = Flask(__name__)
app.secret_key = 'medibase_secret_key_2025' 

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'medibase1'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'logged_in' not in session:
                flash('Anda harus login terlebih dahulu.', 'warning')
                return redirect('/login')
            
            if session.get('role') not in allowed_roles:
                flash('Anda tidak memiliki izin untuk mengakses halaman ini.', 'danger')
                return redirect('/dashboard')
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/')
def landing():
    if 'logged_in' in session:
        return redirect('/dashboard')
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username == 'admin' and password == 'admin123':
            session['logged_in'] = True
            session['username'] = username
            session['role'] = 'admin'
            return redirect('/dashboard')
        elif username == 'petugas' and password == 'petugas123':
            session['logged_in'] = True
            session['username'] = username
            session['role'] = 'petugas'
            return redirect('/dashboard')
        else:
            flash('Username atau password salah!', 'danger')
            return render_template('login.html', error='Username atau password salah!')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear() # Hapus semua sesi
    return redirect('/')

@app.route('/dashboard')
@role_required(['admin', 'petugas'])
def dashboard():
    cur = mysql.connection.cursor()
    
    cur.execute("SELECT COUNT(*) as total FROM pasien")
    total_pasien = cur.fetchone()['total']
    
    cur.execute("SELECT COUNT(*) as total FROM dokter")
    total_dokter = cur.fetchone()['total']
    
    cur.execute("SELECT COUNT(*) as total FROM obat")
    total_obat = cur.fetchone()['total']
    
    today = date.today()
    cur.execute("SELECT COUNT(*) as total FROM kunjungan WHERE DATE(tanggal_kunjungan) = %s", (today,))
    kunjungan_hari_ini = cur.fetchone()['total']
    
    cur.execute("SELECT nama, spesialis, jadwal_praktek FROM dokter LIMIT 5")
    dokter_hari_ini = cur.fetchall()
    
    cur.close()
    
    hari_ini = today.strftime('%A, %d %B %Y')
    
    return render_template('dashboard.html', 
                            title="Dashboard",
                            total_pasien=total_pasien,
                            total_dokter=total_dokter,
                            total_obat=total_obat,
                            kunjungan_hari_ini=kunjungan_hari_ini,
                            dokter_hari_ini=dokter_hari_ini,
                            today=hari_ini)

@app.route('/obat')
@role_required(['admin', 'petugas'])
def obat():
    cur = mysql.connection.cursor()
    cur.execute("SELECT DISTINCT kategori FROM obat ORDER BY kategori ASC")
    kategori_list = cur.fetchall()

    search = request.args.get('search', '')
    kategori = request.args.get('kategori', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('limit', 10, type=int)

    query = "SELECT * FROM obat WHERE 1=1"
    params = []

    if search:
        query += " AND nama_obat LIKE %s"
        params.append("%" + search + "%")

    if kategori:
        query += " AND kategori = %s"
        params.append(kategori)

    cur.execute(query, params)
    total = len(cur.fetchall())

    offset = (page - 1) * per_page
    query += " ORDER BY nama_obat ASC LIMIT %s OFFSET %s"
    params.extend([per_page, offset])

    cur.execute(query, params)
    data = cur.fetchall()
    cur.close()

    total_pages = (total + per_page - 1) // per_page

    return render_template(
        'obat.html',
        obat=data,
        page=page,
        total_pages=total_pages,
        kategori_list=kategori_list,
        kategori=kategori,
        search=search,
        per_page=per_page
    )

@app.route('/obat/tambah', methods=['GET', 'POST'])
@role_required(['admin'])
def tambah_obat():
    if request.method == 'POST':
        nama = request.form['nama_obat']
        kategori = request.form['kategori']
        harga = request.form['harga']
        stok = request.form['stok']
        exp = request.form['tanggal_exp']

        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO obat (nama_obat,kategori, stok,harga, tanggal_exp)
            VALUES (%s, %s, %s, %s, %s)
        """, (nama,kategori, stok, harga, exp))
        mysql.connection.commit()
        cur.close()

        return redirect('/obat')

    return render_template('tambah_obat.html', title="Tambah Obat")

@app.route('/obat/edit/<id>', methods=['GET','POST'])
@role_required(['admin'])
def edit_obat(id):
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        nama = request.form['nama_obat']
        kategori = request.form['kategori']
        stok = request.form['stok']
        harga = request.form['harga']
        exp = request.form['tanggal_exp']

        cur.execute("""
            UPDATE obat
            SET nama_obat=%s, kategori=%s, stok=%s, harga=%s, tanggal_exp=%s
            WHERE id_obat=%s
        """, (nama, kategori, stok, harga, exp, id))

        mysql.connection.commit()
        cur.close()
        return redirect('/obat')

    cur.execute("SELECT * FROM obat WHERE id_obat=%s", (id,))
    data = cur.fetchone()
    cur.close()

    return render_template('edit_obat.html', obat=data, title="Edit Obat")

@app.route('/obat/hapus/<id>')
@role_required(['admin'])
def hapus_obat(id):
    cur = mysql.connection.cursor()

    cur.execute("DELETE FROM resep WHERE id_obat=%s", (id,))

    cur.execute("DELETE FROM obat WHERE id_obat=%s", (id,))

    mysql.connection.commit()
    cur.close()
    return redirect('/obat')

@app.route('/dokter')
@role_required(['admin', 'petugas'])
def dokter():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM dokter ORDER BY id_dokter ASC")
    data = cur.fetchall()
    cur.close()
    return render_template('dokter.html', dokter=data, title="Data Dokter")

@app.route('/dokter/tambah', methods=['GET', 'POST'])
@role_required(['admin'])
def tambah_dokter():
    if request.method == 'POST':
        nama = request.form['nama']
        spesialis = request.form['spesialis']
        no_hp = request.form['no_hp']
        jadwal = request.form['jadwal_praktek']

        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO dokter (nama, spesialis, no_hp, jadwal_praktek)
            VALUES (%s, %s, %s, %s)
        """, (nama, spesialis, no_hp, jadwal))
        mysql.connection.commit()
        cur.close()

        return redirect('/dokter')

    return render_template('tambah_dokter.html', title="Tambah Dokter")

@app.route('/dokter/edit/<id>', methods=['GET','POST'])
@role_required(['admin'])
def edit_dokter(id):
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        nama = request.form['nama_dokter']
        spesialis = request.form['spesialis']
        no_hp = request.form['no_hp']
        jadwal = request.form['jadwal_praktek']

        cur.execute("""
            UPDATE dokter
            SET nama=%s, spesialis=%s, no_hp=%s, jadwal_praktek=%s
            WHERE id_dokter=%s
        """, (nama, spesialis, no_hp, jadwal, id))

        mysql.connection.commit()
        cur.close()

        return redirect('/dokter')

    cur.execute("SELECT * FROM dokter WHERE id_dokter=%s", (id,))
    data = cur.fetchone()
    cur.close()

    return render_template('edit_dokter.html', dokter=data, title="Edit Dokter")

@app.route('/dokter/hapus/<id>')
@role_required(['admin'])
def hapus_dokter(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM dokter WHERE id_dokter=%s", (id,))
    mysql.connection.commit()
    cur.close()
    return redirect('/dokter')

@app.route('/pasien')
@role_required(['admin', 'petugas'])
def pasien():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM pasien ORDER BY id_pasien ASC")
    data = cur.fetchall()
    cur.close()
    return render_template('pasien.html', pasien=data, title="Data Pasien")
-----

@app.route('/pasien/tambah', methods=['GET', 'POST'])
@role_required(['petugas'])
def tambah_pasien():
    if request.method == 'POST':
        nama = request.form['nama']
        tgl = request.form['tanggal_lahir']
        alamat = request.form['alamat']

        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO pasien (nama, tanggal_lahir, alamat)
            VALUES (%s, %s, %s)
        """, (nama, tgl, alamat))
        mysql.connection.commit()
        cur.close()

        return redirect('/pasien')

    return render_template('tambah_pasien.html', title="Tambah Pasien")

@app.route('/pasien/edit/<id>', methods=['GET','POST'])
@role_required(['petugas'])
def edit_pasien(id):
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        nama = request.form['nama']
        tgl = request.form['tanggal_lahir']
        alamat = request.form['alamat']

        cur.execute("""
            UPDATE pasien SET nama=%s, tanggal_lahir=%s, alamat=%s
            WHERE id_pasien=%s
        """, (nama, tgl, alamat, id))

        mysql.connection.commit()
        cur.close()

        return redirect('/pasien')

    cur.execute("SELECT * FROM pasien WHERE id_pasien=%s", (id,))
    data = cur.fetchone()
    cur.close()

    return render_template('edit_pasien.html', pasien=data, title="Edit Pasien")

@app.route('/pasien/hapus/<id>')
@role_required(['petugas'])
def hapus_pasien(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM pasien WHERE id_pasien=%s", (id,))
    mysql.connection.commit()
    cur.close()
    return redirect('/pasien')

@app.route('/kunjungan')
@role_required(['admin', 'petugas'])
def kunjungan():
    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT 
            k.id_kunjungan,
            k.tanggal_kunjungan,
            k.keluhan,
            k.diagnosis,
            p.nama AS nama_pasien,
            d.nama AS nama_dokter,
            GROUP_CONCAT(CONCAT(o.nama_obat, ' (', r.jumlah, ')') 
                SEPARATOR '<br>') AS daftar_obat
        FROM kunjungan k
        JOIN pasien p ON k.id_pasien = p.id_pasien
        JOIN dokter d ON k.id_dokter = d.id_dokter
        LEFT JOIN resep r ON k.id_kunjungan = r.id_kunjungan
        LEFT JOIN obat o ON r.id_obat = o.id_obat
        GROUP BY k.id_kunjungan
        ORDER BY k.id_kunjungan ASC
    """)

    data = cur.fetchall()
    cur.close()

    return render_template('kunjungan.html', kunjungan=data, title="Data Kunjungan")

@app.route('/kunjungan/tambah', methods=['GET','POST'])
@role_required(['petugas'])
def tambah_kunjungan():
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        id_pasien = request.form['id_pasien']
        id_dokter = request.form['id_dokter']
        tanggal = request.form['tanggal_kunjungan']
        keluhan = request.form['keluhan']
        diagnosa = request.form['diagnosa']

        cur.execute("""
            INSERT INTO kunjungan (id_pasien, id_dokter, tanggal_kunjungan, keluhan, diagnosis)
            VALUES (%s, %s, %s, %s, %s)
        """, (id_pasien, id_dokter, tanggal, keluhan, diagnosa))

        id_kunjungan = cur.lastrowid 

        id_obat_list = request.form.getlist('id_obat[]')
        jumlah_list = request.form.getlist('jumlah[]')
        dosis_list = request.form.getlist('dosis[]')

        for i in range(len(id_obat_list)):
            id_obat = id_obat_list[i]
            jumlah = jumlah_list[i]
            dosis = dosis_list[i]

            cur.execute("""
                INSERT INTO resep (id_kunjungan, id_obat, jumlah, dosis)
                VALUES (%s, %s, %s, %s)
            """, (id_kunjungan, id_obat, jumlah, dosis))

        mysql.connection.commit()
        cur.close()

        return redirect('/kunjungan')

    cur.execute("SELECT * FROM pasien")
    pasien = cur.fetchall()

    cur.execute("SELECT * FROM dokter")
    dokter = cur.fetchall()

    cur.execute("SELECT * FROM obat")
    obat = cur.fetchall()

    cur.close()

    return render_template('tambah_kunjungan.html', pasien=pasien, dokter=dokter, obat=obat, title="Tambah Kunjungan")

@app.route('/kunjungan/edit/<id>', methods=['GET', 'POST'])
@role_required(['petugas'])
def edit_kunjungan(id):
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        
        id_pasien = request.form['id_pasien']
        id_dokter = request.form['id_dokter']
        tanggal = request.form['tanggal_kunjungan']
        keluhan = request.form['keluhan']
        diagnosis = request.form['diagnosis']

        cur.execute("""
            UPDATE kunjungan
            SET id_pasien=%s, id_dokter=%s, tanggal_kunjungan=%s,
                keluhan=%s, diagnosis=%s
            WHERE id_kunjungan=%s
        """, (id_pasien, id_dokter, tanggal, keluhan, diagnosis, id))

        mysql.connection.commit()
        cur.close()
        return redirect('/kunjungan')

    cur.execute("""
        SELECT k.*, p.nama AS nama_pasien, d.nama AS nama_dokter
        FROM kunjungan k
        JOIN pasien p ON k.id_pasien = p.id_pasien
        JOIN dokter d ON k.id_dokter = d.id_dokter
        WHERE k.id_kunjungan=%s
    """, (id,))
    kunj = cur.fetchone()

    cur.execute("SELECT * FROM pasien")
    pasien = cur.fetchall()

    cur.execute("SELECT * FROM dokter")
    dokter = cur.fetchall()

    cur.close()

    return render_template(
        'edit_kunjungan.html',
        kunjungan=kunj,
        pasien=pasien,
        dokter=dokter
    )

@app.route('/kunjungan/hapus/<id>')
@role_required(['petugas'])
def hapus_kunjungan(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM kunjungan WHERE id_kunjungan=%s", (id,))
    mysql.connection.commit()
    cur.close()
    return redirect('/kunjungan')


@app.route('/riwayat', methods=['GET'])
@role_required(['admin', 'petugas'])
def riwayat():
    cur = mysql.connection.cursor()

    keyword = request.args.get("cari", "")

    if keyword:
        cur.execute("""
            SELECT id_pasien, nama, tanggal_lahir, jenis_kelamin, no_hp
            FROM pasien
            WHERE nama LIKE %s
            ORDER BY nama ASC
        """, ("%" + keyword + "%",))
    else:
        cur.execute("""
            SELECT DISTINCT p.id_pasien, p.nama, p.tanggal_lahir, p.jenis_kelamin, p.no_hp
            FROM pasien p
            JOIN kunjungan k ON p.id_pasien = k.id_pasien
            ORDER BY p.nama ASC
        """)

    pasien_list = cur.fetchall()
    cur.close()

    return render_template("riwayat.html", pasien_list=pasien_list, title="Riwayat Pasien")

@app.route('/riwayat/<id_pasien>')
@role_required(['admin', 'petugas'])
def detail_riwayat(id_pasien):
    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT *, HitungUmur(tanggal_lahir) AS umur
        FROM pasien 
        WHERE id_pasien = %s
    """, (id_pasien,))
    pasien = cur.fetchone()

    cur.execute("""
        SELECT 
            k.id_kunjungan,
            k.tanggal_kunjungan,
            k.keluhan,
            k.diagnosis,
            d.nama AS nama_dokter,
            o.nama_obat,
            r.jumlah,
            r.dosis,
            (o.harga * r.jumlah) AS subtotal
        FROM kunjungan k
        JOIN dokter d ON k.id_dokter = d.id_dokter
        LEFT JOIN resep r ON k.id_kunjungan = r.id_kunjungan
        LEFT JOIN obat o ON r.id_obat = o.id_obat
        WHERE k.id_pasien = %s
        ORDER BY k.id_kunjungan ASC 
    """, (id_pasien,))
    riwayat = cur.fetchall()

    total_biaya = {}
    sudah = set()

    for r in riwayat:
        id_k = r["id_kunjungan"]
        if id_k not in sudah:
            cur2 = mysql.connection.cursor() 
            try:
                cur2.callproc("HitungTotalBiaya", (id_k,))
                hasil = cur2.fetchall()
                total_biaya[id_k] = hasil[0]["Total_Biaya"]
            except Exception as e:
                print(f"Error calling HitungTotalBiaya for {id_k}: {e}")
                total_biaya[id_k] = 0 
            finally:
                cur2.close()

            sudah.add(id_k)

    cur.close()

    return render_template(
        "detail_riwayat.html",
        pasien=pasien,
        riwayat=riwayat,
        total_biaya=total_biaya
    )

@app.route('/registrasi', methods=['GET', 'POST'])
@role_required(['petugas'])
def registrasi():
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        nama = request.form['nama']
        tgl = request.form['tanggal_lahir']
        jk = request.form['jenis_kelamin']
        alamat = request.form['alamat']
        nohp = request.form['no_hp']

        cur.execute("""
            INSERT INTO pasien (nama, tanggal_lahir, jenis_kelamin, alamat, no_hp, tanggal_registrasi)
            VALUES (%s, %s, %s, %s, %s, NOW())
        """, (nama, tgl, jk, alamat, nohp))

        mysql.connection.commit()
        cur.close()
        return redirect('/pasien')

    return render_template('registrasi.html', title="Registrasi Pasien")

if __name__ == '__main__':
    app.run(debug=True)

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

@app.route('/registrasi', methods=['GET', 'POST'])
@role_required(['petugas']) # Hanya Petugas (CRUD)
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







if __name__ == '__main__':
    app.run(debug=True)

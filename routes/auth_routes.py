from flask import render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from config import app, mysql
import re
from urllib.parse import urljoin, urlparse

def is_safe_redirect(target):
    """Only allow redirects to the same host."""
    if not target:
        return False
    ref = urlparse(request.host_url)
    test = urlparse(urljoin(request.host_url, target))
    return test.scheme in ('http', 'https') and ref.netloc == test.netloc

def validate_email(email):
    """Validasi format email sederhana tapi efektif"""
    email = email.strip().lower()
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(pattern, email):
        return False, "Format email tidak valid"
    
    return True, email

def validate_password(password, confirm_password):
    """Validasi password sederhana"""
    errors = []
    
    if password != confirm_password:
        errors.append("Password tidak sama")
    
    if len(password) < 8:
        errors.append("Password minimal 8 karakter")
    
    if not re.search(r'[A-Z]', password):
        errors.append("Password harus mengandung huruf besar (A-Z)")
    
    return errors

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Ambil data
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip() 
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        terms_accepted = request.form.get('terms')
        
        if not first_name or not last_name or not email or not password:
            flash('Semua field wajib diisi kecuali telepon', 'danger')
            return redirect(url_for('register'))
        
        if not terms_accepted:
            flash('Anda harus menyetujui syarat dan ketentuan', 'danger')
            return redirect(url_for('register'))
        
        is_valid_email, email_error = validate_email(email)
        if not is_valid_email:
            flash(email_error, 'danger')
            return redirect(url_for('register'))
        
        password_errors = validate_password(password, confirm_password)
        if password_errors:
            for error in password_errors:
                flash(error, 'danger')
            return redirect(url_for('register'))
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            cur.close()
            flash('Email sudah terdaftar', 'danger')
            return redirect(url_for('register'))
        
        try:
            hashed_password = generate_password_hash(password)
            cur.execute("""
                INSERT INTO users (first_name, last_name, email, phone, password, role)
                VALUES (%s, %s, %s, %s, %s, 'user')
            """, (first_name, last_name, email, phone if phone else None, hashed_password))
            
            mysql.connection.commit()
            user_id = cur.lastrowid
            cur.close()
            
            session['user_id'] = user_id
            session['email'] = email
            session['name'] = f"{first_name} {last_name}"
            session['role'] = 'user'
            
            flash('Pendaftaran berhasil! Akun Anda telah dibuat.', 'success')
            return redirect(url_for('index'))
            
        except Exception:
            mysql.connection.rollback()
            cur.close()
            app.logger.exception('Registration failed for %s', email)
            flash('Gagal mendaftar. Silakan coba lagi.', 'danger')
            return redirect(url_for('register'))
    
    return render_template('auth/register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('Email dan password harus diisi', 'danger')
            return redirect(url_for('login'))
        
        try:
            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cur.fetchone()
            cur.close()
            
            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['email'] = user['email']
                session['name'] = f"{user['first_name']} {user['last_name']}"
                session['role'] = user['role']
                
                flash('Login berhasil!', 'success')
                
                next_url = request.form.get('next') or request.args.get('next')
                if is_safe_redirect(next_url):
                    return redirect(next_url)
                
                if user['role'] == 'admin':
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('index'))
            else:
                flash('Email atau password salah', 'danger')
                
        except Exception:
            app.logger.exception('Login failed for %s', email)
            flash('Terjadi kesalahan sistem', 'danger')
    
    return render_template('auth/login.html')

@app.route('/logout', methods=['POST'])
def logout():
    # Validasi CSRF token
    from flask_wtf.csrf import validate_csrf
    try:
        validate_csrf(request.form.get('csrf_token'))
    except:
        flash('Invalid CSRF token', 'danger')
        return redirect(url_for('index'))
    
    session.clear()
    flash('Anda telah logout', 'info')
    return redirect(url_for('index'))
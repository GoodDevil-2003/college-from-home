from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'collegefromhome_secret_key'

# ─── DATABASE CONFIG ───────────────────────────────────
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'collage_from_home'

mysql = MySQL(app)

# ─── FILE UPLOAD CONFIG ────────────────────────────────
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'png', 'jpg', 'jpeg', 'mp4'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ─── HOME ──────────────────────────────────────────────
@app.route('/')
def home():
    return render_template('index.html')

# ─── LOGIN ─────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
        user = cur.fetchone()
        cur.close()
        if user:
            if user[6] == 1:
                flash('Your account has been blocked. Contact admin.', 'danger')
                return redirect(url_for('login'))
            if user[5] == 0 and user[4] != 'super_admin':
                flash('Your account is pending approval from Admin.', 'warning')
                return redirect(url_for('login'))
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            session['user_role'] = user[4]
            if user[4] == 'super_admin':
                return redirect(url_for('admin_dashboard'))
            elif user[4] == 'teacher':
                return redirect(url_for('teacher_dashboard'))
            elif user[4] == 'student':
                return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid email or password!', 'danger')
    return render_template('login.html')

# ─── REGISTER ──────────────────────────────────────────
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        existing = cur.fetchone()
        if existing:
            flash('Email already registered!', 'danger')
            return redirect(url_for('register'))
        cur.execute(
            "INSERT INTO users (full_name, email, password, role, is_approved) VALUES (%s, %s, %s, %s, %s)",
            (full_name, email, password, role, 0)
        )
        mysql.connection.commit()
        cur.close()
        flash('Registration successful! Wait for admin approval.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

# ─── ADMIN DASHBOARD ───────────────────────────────────
@app.route('/admin')
def admin_dashboard():
    if 'user_id' not in session or session['user_role'] != 'super_admin':
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) FROM users WHERE role = 'teacher'")
    total_teachers = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM users WHERE role = 'student'")
    total_students = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM users WHERE is_approved = 0 AND role != 'super_admin'")
    pending_approvals = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM announcements")
    total_announcements = cur.fetchone()[0]
    cur.execute("SELECT * FROM users WHERE role != 'super_admin' ORDER BY created_at DESC")
    all_users = cur.fetchall()
    cur.execute("SELECT * FROM announcements ORDER BY posted_at DESC")
    announcements = cur.fetchall()
    cur.execute("SELECT * FROM subjects ORDER BY class_name")
    subjects = cur.fetchall()
    cur.execute("SELECT u.id, u.full_name, u.email FROM users u WHERE u.role = 'teacher' AND u.is_approved = 1")
    teachers = cur.fetchall()
    cur.execute("""
        SELECT ta.id, u.full_name, s.subject_name, s.class_name 
        FROM teacher_assignments ta
        JOIN users u ON ta.teacher_id = u.id
        JOIN subjects s ON ta.subject_id = s.id
    """)
    assignments = cur.fetchall()
    cur.close()
    return render_template('admin_dashboard.html',
        name=session['user_name'],
        total_teachers=total_teachers,
        total_students=total_students,
        pending_approvals=pending_approvals,
        total_announcements=total_announcements,
        all_users=all_users,
        announcements=announcements,
        subjects=subjects,
        teachers=teachers,
        assignments=assignments
    )

# ─── APPROVE USER ──────────────────────────────────────
@app.route('/admin/approve/<int:user_id>')
def approve_user(user_id):
    if 'user_id' not in session or session['user_role'] != 'super_admin':
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    cur.execute("UPDATE users SET is_approved = 1 WHERE id = %s", (user_id,))
    mysql.connection.commit()
    cur.close()
    flash('User approved successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

# ─── BLOCK / UNBLOCK USER ──────────────────────────────
@app.route('/admin/block/<int:user_id>')
def block_user(user_id):
    if 'user_id' not in session or session['user_role'] != 'super_admin':
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    cur.execute("SELECT is_blocked FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    new_status = 0 if user[0] == 1 else 1
    cur.execute("UPDATE users SET is_blocked = %s WHERE id = %s", (new_status, user_id))
    mysql.connection.commit()
    cur.close()
    flash('User block status updated!', 'success')
    return redirect(url_for('admin_dashboard'))

# ─── CHANGE USER ROLE ──────────────────────────────────
@app.route('/admin/change_role/<int:user_id>', methods=['POST'])
def change_role(user_id):
    if 'user_id' not in session or session['user_role'] != 'super_admin':
        return redirect(url_for('login'))
    new_role = request.form['new_role']
    cur = mysql.connection.cursor()
    cur.execute("UPDATE users SET role = %s WHERE id = %s", (new_role, user_id))
    mysql.connection.commit()
    cur.close()
    flash('User role updated!', 'success')
    return redirect(url_for('admin_dashboard'))

# ─── ADD SUBJECT ───────────────────────────────────────
@app.route('/admin/add_subject', methods=['POST'])
def add_subject():
    if 'user_id' not in session or session['user_role'] != 'super_admin':
        return redirect(url_for('login'))
    subject_name = request.form['subject_name']
    class_name = request.form['class_name']
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO subjects (subject_name, class_name) VALUES (%s, %s)", (subject_name, class_name))
    mysql.connection.commit()
    cur.close()
    flash('Subject added successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

# ─── ASSIGN SUBJECT TO TEACHER ─────────────────────────
@app.route('/admin/assign_subject', methods=['POST'])
def assign_subject():
    if 'user_id' not in session or session['user_role'] != 'super_admin':
        return redirect(url_for('login'))
    teacher_id = request.form['teacher_id']
    subject_id = request.form['subject_id']
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM teacher_assignments WHERE teacher_id = %s AND subject_id = %s", (teacher_id, subject_id))
    existing = cur.fetchone()
    if existing:
        flash('This subject is already assigned to this teacher!', 'warning')
    else:
        cur.execute("INSERT INTO teacher_assignments (teacher_id, subject_id) VALUES (%s, %s)", (teacher_id, subject_id))
        mysql.connection.commit()
        flash('Subject assigned to teacher successfully!', 'success')
    cur.close()
    return redirect(url_for('admin_dashboard'))

# ─── REMOVE ASSIGNMENT ─────────────────────────────────
@app.route('/admin/remove_assignment/<int:assignment_id>')
def remove_assignment(assignment_id):
    if 'user_id' not in session or session['user_role'] != 'super_admin':
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM teacher_assignments WHERE id = %s", (assignment_id,))
    mysql.connection.commit()
    cur.close()
    flash('Assignment removed!', 'success')
    return redirect(url_for('admin_dashboard'))

# ─── POST ANNOUNCEMENT ─────────────────────────────────
@app.route('/admin/announcement', methods=['POST'])
def post_announcement():
    if 'user_id' not in session or session['user_role'] != 'super_admin':
        return redirect(url_for('login'))
    title = request.form['title']
    content = request.form['content']
    category = request.form['category']
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO announcements (title, content, category) VALUES (%s, %s, %s)", (title, content, category))
    mysql.connection.commit()
    cur.close()
    flash('Announcement posted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

# ─── DELETE ANNOUNCEMENT ───────────────────────────────
@app.route('/admin/delete_announcement/<int:ann_id>')
def delete_announcement(ann_id):
    if 'user_id' not in session or session['user_role'] != 'super_admin':
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM announcements WHERE id = %s", (ann_id,))
    mysql.connection.commit()
    cur.close()
    flash('Announcement deleted!', 'success')
    return redirect(url_for('admin_dashboard'))

# ─── TEACHER DASHBOARD ─────────────────────────────────
@app.route('/teacher')
def teacher_dashboard():
    if 'user_id' not in session or session['user_role'] != 'teacher':
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT s.id, s.subject_name, s.class_name 
        FROM teacher_assignments ta
        JOIN subjects s ON ta.subject_id = s.id
        WHERE ta.teacher_id = %s
    """, (session['user_id'],))
    assigned_subjects = cur.fetchall()

    cur.execute("""
        SELECT m.id, m.title, m.material_type, m.uploaded_at, s.subject_name
        FROM materials m
        JOIN subjects s ON m.subject_id = s.id
        WHERE m.teacher_id = %s
        ORDER BY m.uploaded_at DESC
    """, (session['user_id'],))
    my_materials = cur.fetchall()

    cur.execute("""
        SELECT sub.id, u.full_name, m.title, sub.submitted_at, sub.file_path, sub.teacher_remark, sub.id
        FROM submissions sub
        JOIN users u ON sub.student_id = u.id
        JOIN materials m ON sub.material_id = m.id
        WHERE m.teacher_id = %s
        ORDER BY sub.submitted_at DESC
    """, (session['user_id'],))
    submissions = cur.fetchall()

    cur.execute("SELECT COUNT(*) FROM submissions sub JOIN materials m ON sub.material_id = m.id WHERE m.teacher_id = %s", (session['user_id'],))
    total_submissions = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM materials WHERE teacher_id = %s", (session['user_id'],))
    total_materials = cur.fetchone()[0]

    cur.close()
    return render_template('teacher_dashboard.html',
        name=session['user_name'],
        assigned_subjects=assigned_subjects,
        my_materials=my_materials,
        submissions=submissions,
        total_submissions=total_submissions,
        total_materials=total_materials
    )

# ─── UPLOAD MATERIAL ───────────────────────────────────
@app.route('/teacher/upload', methods=['POST'])
def upload_material():
    if 'user_id' not in session or session['user_role'] != 'teacher':
        return redirect(url_for('login'))
    title = request.form['title']
    description = request.form['description']
    subject_id = request.form['subject_id']
    material_type = request.form['material_type']
    file = request.files['file']
    file_path = None
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        file_path = filename
    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO materials (teacher_id, subject_id, title, description, file_path, material_type)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (session['user_id'], subject_id, title, description, file_path, material_type))
    mysql.connection.commit()
    cur.close()
    flash('Material uploaded successfully!', 'success')
    return redirect(url_for('teacher_dashboard'))

# ─── DELETE MATERIAL ───────────────────────────────────
@app.route('/teacher/delete_material/<int:material_id>')
def delete_material(material_id):
    if 'user_id' not in session or session['user_role'] != 'teacher':
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    # First delete all student submissions linked to this material
    cur.execute("DELETE FROM submissions WHERE material_id = %s", (material_id,))
    # Then delete the material itself
    cur.execute("DELETE FROM materials WHERE id = %s AND teacher_id = %s", (material_id, session['user_id']))
    mysql.connection.commit()
    cur.close()
    flash('Material and related submissions deleted!', 'success')
    return redirect(url_for('teacher_dashboard'))

# ─── ADD REMARK ON SUBMISSION ──────────────────────────
@app.route('/teacher/remark/<int:submission_id>', methods=['POST'])
def add_remark(submission_id):
    if 'user_id' not in session or session['user_role'] != 'teacher':
        return redirect(url_for('login'))
    remark = request.form['remark']
    cur = mysql.connection.cursor()
    cur.execute("UPDATE submissions SET teacher_remark = %s WHERE id = %s", (remark, submission_id))
    mysql.connection.commit()
    cur.close()
    flash('Remark added successfully!', 'success')
    return redirect(url_for('teacher_dashboard'))

# ─── STUDENT DASHBOARD ─────────────────────────────────
@app.route('/student')
def student_dashboard():
    if 'user_id' not in session or session['user_role'] != 'student':
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()

    # Get all available subjects
    cur.execute("SELECT * FROM subjects ORDER BY class_name")
    all_subjects = cur.fetchall()

    # Get enrolled subjects
    cur.execute("""
        SELECT s.id, s.subject_name, s.class_name
        FROM student_enrollments se
        JOIN subjects s ON se.subject_id = s.id
        WHERE se.student_id = %s
    """, (session['user_id'],))
    enrolled_subjects = cur.fetchall()

    enrolled_ids = [s[0] for s in enrolled_subjects]

    # Get materials for enrolled subjects
    cur.execute("""
        SELECT m.id, m.title, m.description, m.material_type, m.file_path,
               m.uploaded_at, s.subject_name, u.full_name
        FROM materials m
        JOIN subjects s ON m.subject_id = s.id
        JOIN users u ON m.teacher_id = u.id
        WHERE m.subject_id IN %s
        ORDER BY m.uploaded_at DESC
    """ if enrolled_ids else "SELECT NULL LIMIT 0",
    (tuple(enrolled_ids),) if enrolled_ids else ())
    materials = cur.fetchall() if enrolled_ids else []

    # Get announcements
    cur.execute("SELECT * FROM announcements ORDER BY posted_at DESC")
    announcements = cur.fetchall()

    # Get student's submissions
    cur.execute("""
        SELECT sub.id, m.title, sub.submitted_at, sub.teacher_remark, sub.file_path
        FROM submissions sub
        JOIN materials m ON sub.material_id = m.id
        WHERE sub.student_id = %s
        ORDER BY sub.submitted_at DESC
    """, (session['user_id'],))
    my_submissions = cur.fetchall()

    cur.close()
    return render_template('student_dashboard.html',
        name=session['user_name'],
        all_subjects=all_subjects,
        enrolled_subjects=enrolled_subjects,
        enrolled_ids=enrolled_ids,
        materials=materials,
        announcements=announcements,
        my_submissions=my_submissions
    )

# ─── ENROLL IN SUBJECT ─────────────────────────────────
@app.route('/student/enroll/<int:subject_id>')
def enroll_subject(subject_id):
    if 'user_id' not in session or session['user_role'] != 'student':
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM student_enrollments WHERE student_id = %s AND subject_id = %s",
                (session['user_id'], subject_id))
    existing = cur.fetchone()
    if existing:
        flash('You are already enrolled in this subject!', 'warning')
    else:
        cur.execute("INSERT INTO student_enrollments (student_id, subject_id) VALUES (%s, %s)",
                    (session['user_id'], subject_id))
        mysql.connection.commit()
        flash('Enrolled successfully!', 'success')
    cur.close()
    return redirect(url_for('student_dashboard'))

# ─── UNENROLL FROM SUBJECT ─────────────────────────────
@app.route('/student/unenroll/<int:subject_id>')
def unenroll_subject(subject_id):
    if 'user_id' not in session or session['user_role'] != 'student':
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM student_enrollments WHERE student_id = %s AND subject_id = %s",
                (session['user_id'], subject_id))
    mysql.connection.commit()
    cur.close()
    flash('Unenrolled from subject!', 'success')
    return redirect(url_for('student_dashboard'))

# ─── SUBMIT SOLVED PAPER ───────────────────────────────
@app.route('/student/submit/<int:material_id>', methods=['POST'])
def submit_paper(material_id):
    if 'user_id' not in session or session['user_role'] != 'student':
        return redirect(url_for('login'))
    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Add student id prefix to avoid name conflicts
        filename = f"student_{session['user_id']}_{filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO submissions (student_id, material_id, file_path)
            VALUES (%s, %s, %s)
        """, (session['user_id'], material_id, filename))
        mysql.connection.commit()
        cur.close()
        flash('Assignment submitted successfully!', 'success')
    else:
        flash('Invalid file type!', 'danger')
    return redirect(url_for('student_dashboard'))

# ─── LOGOUT ────────────────────────────────────────────
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
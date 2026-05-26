# ─── REPORTS & EXPORT IMPORTS ──────────────────────────
import csv
import io
from flask import make_response
from datetime import datetime

# ─── REPORTS DASHBOARD ─────────────────────────────────
@app.route('/admin/reports')
def admin_reports():
    if 'user_id' not in session or session['user_role'] != 'super_admin':
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    # Dashboard Counts
    cur.execute("SELECT COUNT(*) FROM users WHERE role='teacher'")
    total_teachers = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM users WHERE role='student'")
    total_students = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM users WHERE is_approved=0 AND role!='super_admin'")
    pending_users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM users WHERE is_blocked=1")
    blocked_users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM materials")
    total_materials = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM submissions")
    total_submissions = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM announcements")
    total_announcements = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM subjects")
    total_subjects = cur.fetchone()[0]

    # Registrations
    cur.execute("""
        SELECT id, full_name, email, role,
               is_approved, is_blocked, created_at
        FROM users
        WHERE role != 'super_admin'
        ORDER BY created_at DESC
    """)
    all_registrations = cur.fetchall()

    # Uploaded Materials
    cur.execute("""
        SELECT m.id, m.title, m.material_type,
               m.file_path, m.uploaded_at,
               s.subject_name, s.class_name,
               u.full_name
        FROM materials m
        JOIN subjects s ON m.subject_id = s.id
        JOIN users u ON m.teacher_id = u.id
        ORDER BY m.uploaded_at DESC
    """)
    all_uploads = cur.fetchall()

    # Submissions
    cur.execute("""
        SELECT sub.id,
               u.full_name,
               m.title,
               s.subject_name,
               sub.submitted_at,
               sub.teacher_remark,
               sub.file_path
        FROM submissions sub
        JOIN users u ON sub.student_id = u.id
        JOIN materials m ON sub.material_id = m.id
        JOIN subjects s ON m.subject_id = s.id
        ORDER BY sub.submitted_at DESC
    """)
    all_submissions = cur.fetchall()

    # Announcements
    cur.execute("""
        SELECT *
        FROM announcements
        ORDER BY posted_at DESC
    """)
    all_announcements = cur.fetchall()

    # Subject Stats
    cur.execute("""
        SELECT s.subject_name,
               s.class_name,
               COUNT(m.id) AS total
        FROM subjects s
        LEFT JOIN materials m ON s.id = m.subject_id
        GROUP BY s.id
        ORDER BY total DESC
    """)
    subject_stats = cur.fetchall()

    # Student Stats
    cur.execute("""
        SELECT u.full_name,
               u.email,
               COUNT(sub.id) AS total
        FROM users u
        LEFT JOIN submissions sub ON u.id = sub.student_id
        WHERE u.role='student'
        GROUP BY u.id
        ORDER BY total DESC
    """)
    student_stats = cur.fetchall()

    # Teacher Stats
    cur.execute("""
        SELECT u.full_name,
               u.email,
               COUNT(m.id) AS total
        FROM users u
        LEFT JOIN materials m ON u.id = m.teacher_id
        WHERE u.role='teacher'
        GROUP BY u.id
        ORDER BY total DESC
    """)
    teacher_stats = cur.fetchall()

    cur.close()

    return render_template(
        'reports.html',
        total_teachers=total_teachers,
        total_students=total_students,
        pending_users=pending_users,
        blocked_users=blocked_users,
        total_materials=total_materials,
        total_submissions=total_submissions,
        total_announcements=total_announcements,
        total_subjects=total_subjects,
        all_registrations=all_registrations,
        all_uploads=all_uploads,
        all_submissions=all_submissions,
        all_announcements=all_announcements,
        subject_stats=subject_stats,
        student_stats=student_stats,
        teacher_stats=teacher_stats,
        generated_at=datetime.now().strftime('%d %b %Y %I:%M %p')
    )

# ─── EXPORT REGISTRATIONS ──────────────────────────────
@app.route('/admin/export/registrations')
def export_registrations():

    if 'user_id' not in session or session['user_role'] != 'super_admin':
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT id,
               full_name,
               email,
               role,
               CASE
                    WHEN is_approved=1
                    THEN 'Approved'
                    ELSE 'Pending'
               END,
               CASE
                    WHEN is_blocked=1
                    THEN 'Blocked'
                    ELSE 'Active'
               END,
               created_at
        FROM users
        WHERE role!='super_admin'
        ORDER BY created_at DESC
    """)

    data = cur.fetchall()
    cur.close()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        'ID',
        'Full Name',
        'Email',
        'Role',
        'Approval Status',
        'Block Status',
        'Registered On'
    ])

    for row in data:
        writer.writerow(row)

    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=registrations_report.csv'
    response.headers['Content-type'] = 'text/csv'

    return response

# ─── EXPORT UPLOADS ────────────────────────────────────
@app.route('/admin/export/uploads')
def export_uploads():

    if 'user_id' not in session or session['user_role'] != 'super_admin':
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT m.id,
               m.title,
               m.material_type,
               m.file_path,
               s.subject_name,
               s.class_name,
               u.full_name,
               m.uploaded_at
        FROM materials m
        JOIN subjects s ON m.subject_id=s.id
        JOIN users u ON m.teacher_id=u.id
        ORDER BY m.uploaded_at DESC
    """)

    data = cur.fetchall()
    cur.close()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        'ID',
        'Title',
        'Type',
        'File Name',
        'Subject',
        'Class',
        'Uploaded By',
        'Uploaded On'
    ])

    for row in data:
        writer.writerow(row)

    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=uploads_report.csv'
    response.headers['Content-type'] = 'text/csv'

    return response

# ─── EXPORT SUBMISSIONS ────────────────────────────────
@app.route('/admin/export/submissions')
def export_submissions():

    if 'user_id' not in session or session['user_role'] != 'super_admin':
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT sub.id,
               u.full_name,
               m.title,
               s.subject_name,
               sub.submitted_at,
               CASE
                    WHEN sub.teacher_remark IS NOT NULL
                    THEN sub.teacher_remark
                    ELSE 'Pending Review'
               END
        FROM submissions sub
        JOIN users u ON sub.student_id=u.id
        JOIN materials m ON sub.material_id=m.id
        JOIN subjects s ON m.subject_id=s.id
        ORDER BY sub.submitted_at DESC
    """)

    data = cur.fetchall()
    cur.close()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        'ID',
        'Student Name',
        'Assignment Title',
        'Subject',
        'Submitted On',
        'Teacher Remark'
    ])

    for row in data:
        writer.writerow(row)

    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=submissions_report.csv'
    response.headers['Content-type'] = 'text/csv'

    return response

# ─── EXPORT ANNOUNCEMENTS ──────────────────────────────
@app.route('/admin/export/announcements')
def export_announcements():

    if 'user_id' not in session or session['user_role'] != 'super_admin':
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT id,
               title,
               content,
               category,
               posted_at
        FROM announcements
        ORDER BY posted_at DESC
    """)

    data = cur.fetchall()
    cur.close()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        'ID',
        'Title',
        'Content',
        'Category',
        'Posted On'
    ])

    for row in data:
        writer.writerow(row)

    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=announcements_report.csv'
    response.headers['Content-type'] = 'text/csv'

    return response

# ─── EXPORT FULL REPORT ────────────────────────────────
@app.route('/admin/export/full')
def export_full():

    if 'user_id' not in session or session['user_role'] != 'super_admin':
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(['=== COLLEGE FROM HOME - FULL REPORT ==='])
    writer.writerow([
        'Generated On',
        datetime.now().strftime('%d %b %Y %I:%M %p')
    ])
    writer.writerow([])

    # Registrations
    writer.writerow(['=== USER REGISTRATIONS ==='])

    writer.writerow([
        'ID',
        'Full Name',
        'Email',
        'Role',
        'Status',
        'Blocked',
        'Registered On'
    ])

    cur.execute("""
        SELECT id,
               full_name,
               email,
               role,
               CASE
                    WHEN is_approved=1
                    THEN 'Approved'
                    ELSE 'Pending'
               END,
               CASE
                    WHEN is_blocked=1
                    THEN 'Blocked'
                    ELSE 'Active'
               END,
               created_at
        FROM users
        WHERE role!='super_admin'
        ORDER BY created_at DESC
    """)

    for row in cur.fetchall():
        writer.writerow(row)

    writer.writerow([])

    # Uploads
    writer.writerow(['=== UPLOADED MATERIALS ==='])

    writer.writerow([
        'ID',
        'Title',
        'Type',
        'File',
        'Subject',
        'Class',
        'Teacher',
        'Date'
    ])

    cur.execute("""
        SELECT m.id,
               m.title,
               m.material_type,
               m.file_path,
               s.subject_name,
               s.class_name,
               u.full_name,
               m.uploaded_at
        FROM materials m
        JOIN subjects s ON m.subject_id=s.id
        JOIN users u ON m.teacher_id=u.id
        ORDER BY m.uploaded_at DESC
    """)

    for row in cur.fetchall():
        writer.writerow(row)

    writer.writerow([])

    # Submissions
    writer.writerow(['=== STUDENT SUBMISSIONS ==='])

    writer.writerow([
        'ID',
        'Student',
        'Assignment',
        'Subject',
        'Date',
        'Remark'
    ])

    cur.execute("""
        SELECT sub.id,
               u.full_name,
               m.title,
               s.subject_name,
               sub.submitted_at,
               CASE
                    WHEN sub.teacher_remark IS NOT NULL
                    THEN sub.teacher_remark
                    ELSE 'Pending'
               END
        FROM submissions sub
        JOIN users u ON sub.student_id=u.id
        JOIN materials m ON sub.material_id=m.id
        JOIN subjects s ON m.subject_id=s.id
        ORDER BY sub.submitted_at DESC
    """)

    for row in cur.fetchall():
        writer.writerow(row)

    writer.writerow([])

    # Announcements
    writer.writerow(['=== ANNOUNCEMENTS ==='])

    writer.writerow([
        'ID',
        'Title',
        'Category',
        'Posted On'
    ])

    cur.execute("""
        SELECT id,
               title,
               category,
               posted_at
        FROM announcements
        ORDER BY posted_at DESC
    """)

    for row in cur.fetchall():
        writer.writerow(row)

    cur.close()

    response = make_response(output.getvalue())

    response.headers['Content-Disposition'] = 'attachment; filename=full_report.csv'

    response.headers['Content-type'] = 'text/csv'

    return response
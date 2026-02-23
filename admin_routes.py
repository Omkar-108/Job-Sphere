# routes/admin_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, session
from services.admin_service import admin_service
from utils.decorators import require_admin

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        from database.setup import db
        email = request.form['email']
        password = request.form['password']
        admin_data = db.admin.find_one({'email': email, 'password': password})
        
        if admin_data:
            session['is_admin'] = True
            session['admin_id'] = str(admin_data['_id'])
            session['admin_email'] = admin_data['email']
            return redirect(url_for('admin.admin_dashboard'))
        else:
            return render_template('admin_login.html', error="Invalid credentials")
    
    return render_template('admin_login.html')

@admin_bp.route('/admin/dashboard')
@require_admin
def admin_dashboard():
    search = request.args.get("search", "").strip()
    department = request.args.get("department", "").strip()
    page = int(request.args.get("page", 1))
    
    result = admin_service.get_all_hr(search, department, page, 5)
    
    return render_template(
        "dashboard_admin.html",
        hr_list=result['hr_list'],
        hired=result['analytics']['hired'],
        pending=result['analytics']['pending'],
        search=search,
        department=department,
        page=page,
        has_next=result['pagination']['has_next']
    )

@admin_bp.route('/admin/hr/add', methods=['POST'])
@require_admin
def admin_add_hr():
    hr_data = {
        'name': request.form['name'],
        'department': request.form['department'],
        'email': request.form['email'],
        'password': request.form['password'],
        'username': request.form['username']
    }
    print(hr_data)
    
    result = admin_service.add_hr(hr_data)
    print(f"{result}")
    from flask import flash
    if 'error' in result:
        flash(result['error'], 'error')
    else:
        flash("HR added successfully!", 'success')
    
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/admin/hr/edit/<hr_id>', methods=['POST'])
@require_admin
def admin_edit_hr(hr_id):
    hr_data = {
        'username': request.form['username'],
        'name': request.form['name'],
        'department': request.form['department'],
        'email': request.form['email'],
        'password': request.form['password']
    }
    
    result = admin_service.update_hr(hr_id, hr_data)
    
    if 'error' in result:
        from flask import flash
        flash(result['error'], 'error')
    else:
        flash("HR updated successfully!", 'success')
    
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/admin/hr/delete/<hr_id>')
@require_admin
def admin_delete_hr(hr_id):
    result = admin_service.delete_hr(hr_id)
    from flask import flash
    if 'error' in result:
        flash(result['error'], 'error')
    else:
        flash("HR deleted successfully!", 'success')
    
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/admin/analytics/data')
@require_admin
def admin_analytics_data():
    analytics = admin_service.get_hr_analytics()
    
    # Convert to list for JSON response
    result = []
    for hr_id in analytics['hired']:
        result.append({
            '_id': hr_id,
            'hired': analytics['hired'][hr_id],
            'pending': analytics['pending'].get(hr_id, 0)
        })
    
    from flask import jsonify
    return jsonify(result)
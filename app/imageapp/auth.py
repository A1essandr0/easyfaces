import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash
from imageapp.db import get_db

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None

        if not username:
            error = "Username needed"
        elif not password:
            error = "Password needed"
        elif db.execute(
            'SELECT id FROM users WHERE username = ?', (username,)
        ).fetchone() is not None:
            error = "User {0} already exist".format(username)

        if error is None:
            db.execute(
            'INSERT INTO users (username, password) VALUES (?, ?)',
            (username, generate_password_hash(password))
            )
            db.commit()
            flash("User {0} registered".format(username))
            return redirect(url_for('auth.login'))

        flash(error)
    return render_template('auth/register.html')


@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None
        user = db.execute(
            'SELECT * FROM users WHERE username = ?', (username,)
        ).fetchone()

        if user is None:
            error = "Wrong username"
        elif not check_password_hash(user['password'], password):
            error = "Wrong password"

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            return redirect(url_for('index'))

        flash(error)
    return render_template('auth/login.html')


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            'SELECT * FROM users WHERE id = ?', (user_id, )
        ).fetchone()


@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# Decorator for views that need login
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash('Authorization required')
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view

# Decorator for views that need login as admin
def admin_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user['admin_status'] == 0:
            flash('Admin rights required')
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view

@bp.route('/userlist', methods=('GET', 'POST'))
@admin_required
def edit_userlist():
    db = get_db()
    if request.method == 'POST':
        promoted_to_admin = []
        deleted = []
        demoted = []

        for field in request.form:
            if field.startswith('make_admin_id'):
                promoted_to_admin.append(field[13:])
            if field.startswith('delete_account_id'):
                deleted.append(field[17:])
            if field.startswith('unmake_admin_id'):
                demoted.append(field[15:])

        for _id in promoted_to_admin:
            db.execute('UPDATE users SET admin_status = 1 WHERE id = ?', (_id,) )
        for _id in demoted:
            db.execute('UPDATE users SET admin_status = 0 WHERE id = ?', (_id,) )
        for _id in deleted:
            db.execute('DELETE FROM users WHERE id = ?', (_id,) )
        db.commit()
        flash("Users' changes applied")

    users = db.execute("""
        SELECT id, username, upload_count, admin_status FROM users
    """
    ).fetchall()

    return render_template('auth/userlist.html', users=users)

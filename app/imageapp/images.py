import os
import requests
import json

from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, send_from_directory
)
from werkzeug.exceptions import abort
from werkzeug.utils import secure_filename

from imageapp.auth import login_required
from imageapp.db import get_db
from imageapp.settings import imgbank, allowed_extensions, access_token, service_url

bp = Blueprint('images', __name__)

# Helpers
# Gets file extension
def extension(f):
    return f.rsplit('.', 1)[1].lower()
# Checks whether file is allowed to upload
def filename_allowed(filename):
    return '.' in filename and extension(filename) in allowed_extensions


# Gets database record which corresponds image id
def get_image(id, check_author=True):
    image = get_db().execute("""
        SELECT images.id, filename, author_id, created, about, username
            FROM (images JOIN users ON images.author_id = users.id)
            WHERE images.id = ?""",
        (id,)
    ).fetchone()

    if image is None:
        abort(404, "Image with id {0} doesn't exist".format(id))

    if check_author and image['author_id'] != g.user['id'] and g.user['admin_status'] != 1:
        abort(403)

    return image


# Uploaded images' list
@bp.route('/')
def index():
    db = get_db()
    # Getting records
    images = db.execute("""
        SELECT images.id, filename, author_id, created, about, username
            FROM (images JOIN users ON images.author_id = users.id)
            ORDER BY created DESC
    """
    ).fetchall()

    return render_template('images/index.html', images=images, imgbank=imgbank.split('/')[-2])

# Image view. Also used for <img src="">
@bp.route('/<string:filename>')
def show(filename):
    return send_from_directory(imgbank, filename, as_attachment=False)

# Upload new image
@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        # with open('uploads.log','w') as log:
        #     print(request.files, sep=" ; ", file=log)
        error = None
        if 'file' not in request.files:
            flash('File needed')
        else:
            img = request.files['file']
            if img.filename == '':
                error = 'File needed'

        if not img or not filename_allowed(img.filename):
            error = 'Upload failed, check filename/path'
            # filename = secure_filename(img.filename)

        if error is not None:
            flash(error, category='error')
        else:
            db = get_db()
            about = request.form['about']
            
            # Temporary record
            tmp_filename = 'tmp' + str(g.user['id'])
            db.execute("""
                INSERT INTO images (about, filename, author_id)
                    VALUES (?, ?, ?)""",
                (about, tmp_filename, g.user['id'])    
            )
            # Filename generation
            filename = 'image' + str(db.execute("""
                SELECT id FROM images
                    WHERE filename = ?""",
                (tmp_filename,)
            ).fetchone()['id']) + '.' + extension(img.filename)

            # Creating/updating database record
            db.execute("UPDATE images SET filename = ? WHERE filename = ?", 
                (filename, tmp_filename))
            # Upload image to file storage
            filepath = os.path.join(imgbank, filename)
            if os.path.exists(filepath):
                error = 'Filename already exists'
            else:
                img.save(filepath)            
            
            # Increment image counter
            count = 1 + db.execute("""
                SELECT upload_count FROM users
                    WHERE id = ?""",
                    (g.user['id'],)
            ).fetchone()['upload_count']
            db.execute("UPDATE users SET upload_count = ? WHERE id = ?", (count, g.user['id']))

            db.commit()
            flash('File uploaded successfully', category='info')

            return redirect(url_for('images.index'))

    return render_template('images/create.html')

# Deleting image
@bp.route('/<int:id>/delete', methods=('POST', 'GET'))
@login_required
def delete(id):
    get_image(id)
    db = get_db()
    filename = db.execute('SELECT filename FROM images WHERE id = ?', (id,)
    ).fetchone()['filename']
    # Delete database record
    db.execute('DELETE FROM images WHERE id = ?', (id,))
    # DELETE ON CASCADE manually, sqlite doesn't do that
    db.execute('DELETE FROM faces WHERE image_id = ?', (id,))
    db.commit()
    # Delete file itself
    filepath = os.path.join(imgbank, filename)
    os.remove(filepath)
    flash('Image {0} deleted'.format(filename))

    return redirect(url_for('images.index'))


# Editing face rectangles
@bp.route('/<int:id>/edit', methods=('GET', 'POST'))
@login_required
def edit(id):
    image = get_image(id)

    if request.method == 'GET':
        db = get_db()
        coordinates = db.execute("""
            SELECT x1, y1, x2, y2 FROM faces WHERE image_id = ? """, (id,) ).fetchall()

    elif request.method == 'POST':
        about = request.form['about']
        error = None
        if not about:
            error = 'Description needed'

        if request.form['x1']: # If new rectangle added
            msg = 'Coordinates added: ({0};{1}) and ({2};{3})'.format(
                request.form['x1'], request.form['y1'],
                request.form['x2'], request.form['y2'] )
        else:
            msg = None

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute("""
                UPDATE images SET about = ? WHERE id = ? """, (about, id) )
            if msg: # Inserting new rectangle in database
                db.execute("""
                    INSERT INTO faces (x1, y1, x2, y2, image_id)
                        VALUES (?, ?, ?, ?, ?)""",
                    (request.form['x1'], request.form['y1'], request.form['x2'], request.form['y2'], id,) )
                flash(msg)

            db.commit()
            return redirect(url_for('images.edit', id=id))

    return render_template('images/edit.html',  image=image,
                                                imgbank=imgbank.split('/')[-2],
                                                coordinates=coordinates )

# Getting face rectangles from Azure Cognitive Services
@bp.route('/<int:id>/facecloud', methods=('POST',))
@login_required
def facecloud(id):
    
    # Requesting rectangles
    image = get_image(id)
    db = get_db()
    filename = db.execute('SELECT filename FROM images WHERE id = ?', (id,)
                        ).fetchone()['filename']
    filepath = os.path.join(imgbank, filename)

    headers = {'Ocp-Apim-Subscription-Key': access_token, 'Content-Type': 'application/octet-stream'}
    params = {
        'returnFaceId': 'true',
        'returnFaceLandmarks': 'false',
        'returnFaceAttributes': 'age,gender,headPose,smile,facialHair,glasses,emotion,hair',
    }
    binary_file = open(filepath, 'rb')
    response = requests.post(service_url, params=params,
                            headers=headers, data=binary_file)
    
    coordinates = []
    for face_record in response.json():
        x1 = face_record['faceRectangle']['left']
        y1 = face_record['faceRectangle']['top']
        x2 = x1 + face_record['faceRectangle']['width']
        y2 = y1 + face_record['faceRectangle']['height']
        coordinates.append({'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2})
        db.execute("""
            INSERT INTO faces (x1, y1, x2, y2, image_id)
                VALUES (?, ?, ?, ?, ?)""",
            (x1, y1, x2, y2, id,) )
        db.commit()

    json_filename = "face_" + face_record['faceId'] + ".json"
    with open(os.path.join(imgbank, json_filename), "w") as json_fh:
        print(json.dumps(response.json(), indent=4), file=json_fh)
    
    if coordinates:
        flash("Face rectangles added")
    else:
        flash("Faces not detected")
        
    return render_template('images/facecloud.html', image=image,
                                                    imgbank=imgbank.split('/')[-2],
                                                    coordinates=coordinates,
                                                    json_filename=json_filename)

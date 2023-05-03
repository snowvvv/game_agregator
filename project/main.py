import os
from datetime import datetime
import configparser

import smtplib
from email.mime.multipart import MIMEMultipart  # Многокомпонентный объект
from email.mime.text import MIMEText
from cloudipsp import Api, Checkout

from flask import Blueprint, render_template, request, redirect, url_for, send_from_directory, flash
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from . import db
from .models import User, Post, Setup
from . import UPLOAD_FOLDER, ALLOWED_EXTENSIONS

main = Blueprint('main', __name__)
config = configparser.ConfigParser()
config.read("config.ini")


def send_email(addr_to, body):
    addr_from = config["send_email"]["addr_from"]

    password_em = config["send_email"]["password_em"]

    msg = MIMEMultipart()
    msg['From'] = addr_from  # Адресат
    msg['To'] = addr_to
    msg['Subject'] = 'Отклик на ваш пост по поиску тиммейтов'

    msg.attach(MIMEText(body, 'plain'))

    server = smtplib.SMTP_SSL('smtp.yandex.ru', 465)
    server.login(addr_from, password_em)
    server.send_message(msg)
    server.quit()


@main.route('/')
def index():
    return render_template('new_index.html')


@main.route('/search-teammates')
@login_required
def search_teammates():
    q = request.args.get('q')
    if q:
        posts = Post.query.filter(Post.tag.contains(f'{q}'))
    else:
        posts = Post.query.all()
    return render_template('new_search_teammates.html', data=posts)


@main.route('/create-post', methods=['POST'])
@login_required
def create_post():
    id = Post.query.all()
    my_id = len(id) + 1
    title = request.form.get('title')
    description = request.form.get('description')
    tag = request.form.get('tag')

    # if len(title) < 1 or len(description) < 1 or len(tag) < 1:
    #     flash("Заполните все поля")
    #     return redirect(url_for('main.create-post'))

    new_post = Post(id=my_id, title=title, description=description, user_id=current_user.id, tag=tag)
    if os.path.exists(f'static/images/{new_post.id}.png'):
        db.session.add(new_post)
        db.session.commit()
    else:
        db.session.add(new_post)
        db.session.commit()
    return render_template('new_profile.html', data=my_id)


@main.route('/create-post', methods=['GET'])
@login_required
def post():
    id = Post.query.all()
    my_id = len(id) + 1
    return render_template('new_offer.html', data=my_id)


@main.route('/profile')
@login_required
def profile():
    return render_template('new_profile.html')


@main.route('/own')
@login_required
def own_posts():
    if current_user.email == config["Admin"]["email"]:
        post = Post.query.all()
    else:
        post = Post.query.filter_by(user_id=current_user.id)
    return render_template('new_my_items.html', data=post)


@main.route('/info/<int:id>', methods=['GET', 'POST'])
@login_required
def info(id):
    post = Post.query.filter_by(id=id).first()
    user = User.query.filter_by(id=post.user_id).first()
    email = user.email
    if request.method == "POST":
        if email is not None:
            send_email(email,
                       f"Найден тиммейт! \n" 
                       f" Его Discord - {current_user.discord}. Его Steam - {current_user.steam}. \n"
                       f" Удачной игры!")
        setattr(post, 'responded_user', current_user.name)
        db.session.commit()
        return redirect('/search-teammates')
    else:
        return render_template('new_info.html', data=post, pic=f'/static/images/{post.id}.png')


@main.route('/change/<int:num>', methods=['GET'])
@login_required
def change_get(num):
    post = Post.query.filter_by(id=num).first()
    return render_template("new_change.html", data=post)


@main.route('/change/<int:num>', methods=['POST'])
@login_required
def change(num):
    if current_user.email == config["Admin"]["email"]:
        posts_id = Post.query.all()
    else:
        posts_id = Post.query.filter_by(user_id=current_user.id).all()
    title = request.form.get('title')
    description = request.form.get('description')
    tag = request.form.get('tag')
    post = Post.query.filter_by(id=num).first()

    new_post = Post(id=post.id, title=title, description=description, tag=tag, user_id=current_user.id)
    if post in posts_id:
        db.session.delete(post)
        db.session.add(new_post)
        db.session.commit()
        return redirect('/own')

    else:
        flash('У вас нет доступа к чужим постам')
        return redirect(url_for("main.profile"))


@main.route('/delete/<int:num>')
@login_required
def delete(num):
    if current_user.email == config["Admin"]["email"]:
        posts_id = Post.query.all()
    else:
        posts_id = Post.query.filter_by(user_id=current_user.id).all()
    post = Post.query.filter_by(id=num).first()

    if post in posts_id:
        db.session.delete(post)
        db.session.commit()
        return redirect('/profile')
    else:
        flash('Вам не принадлежит этот пост. Возможно произошла ошибка')
    return redirect('/own')


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@main.route('/uploads/<int:id>', methods=['GET', 'POST'])
def upload_file(id):
    post = Post.query.filter_by(id=id).first()
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, str(id) + ".png"))
            if post == None:
                return redirect(url_for('main.create_post'))
            else:
                return redirect(url_for('main.index'))
    return '''
       <!doctype html>
       <title>Загрузите файл</title>
       <h1>Upload new File</h1>
       <form method=post enctype=multipart/form-data>
         <input type=file name=file>
         <input type=submit value=Upload>
       </form>
       '''


@main.route('/items/<name>')
def uploaded_file(name):
    return send_from_directory(UPLOAD_FOLDER, name)


@main.route('/check-fps', methods=['GET', 'POST'])
def check_fps():
    setup = Setup.query.all()
    if request.method == 'POST':
        game = request.form.get('game')
        CPU = request.form.get('CPU')
        GPU = request.form.get('GPU')
        CPU_id = Setup.query.filter_by(CPU=CPU).first()
        GPU_id = Setup.query.filter_by(GPU=GPU).first()
        if game == 'CS GO':
            if CPU_id.id <= 200 and GPU_id.id <= 200:
                return render_template('check_fps.html',result='Ваш пк реально тянет!'
                                                                ' Вам гарантировано 60+ fps при разрешении FullHD ', data=setup)
            elif CPU_id.id > 200 and GPU_id.id > 200:
                return render_template('check_fps.html', result='Ваш пк ниже минимальных системных требований,'
                                                                ' скорее всего игра будет нестабильна', data=setup)
        elif game == 'DOTA 2':
            if CPU_id.id <= 200 and GPU_id.id <= 200:
                return render_template('check_fps.html', result='Ваш пк реально тянет!'
                                                                ' Вам гарантировано 60+ fps при разрешении FullHD ', data=setup)
            if 300 >= CPU_id.id > 200 and 300 >= GPU_id.id > 200:
                return render_template('check_fps.html',
                                       result='Ваш пк выше минимальных требований игры, 30 fps при разрешении FullHd', data=setup)
        elif game == 'Genshin Impact':
            if 230 >= CPU_id.id > 75 and 230 >= GPU_id.id > 75:
                return render_template('check_fps.html', result='Ваш пк реально тянет!'
                                                                ' Вам гарантировано 60+ fps при разрешении FullHD ', data=setup)
            if 230 <= CPU_id.id and 230 <= GPU_id.id:
                return render_template('check_fps.html', result='Ваш пк ниже минимальных системных требований,'
                                                                ' скорее всего игра будет нестабильна', data=setup)
        elif game == 'PUBG: Battlegrounds':
            if CPU_id.id <= 140 and GPU_id.id <= 140:
                return render_template('check_fps.html', result='Ваш пк реально тянет!'
                                                                ' Вам гарантировано 60+ fps при разрешении FullHD ', data=setup)
            if 199 <= CPU_id.id and 199 <= GPU_id.id:
                return render_template('check_fps.html', result='Ваш пк ниже минимальных системных требований,'
                                                                ' скорее всего игра будет нестабильна', data=setup)
        elif game == 'League of Legends':
            if CPU_id.id <= 320 and GPU_id.id <= 320:
                return render_template('check_fps.html', result='Ваш пк реально тянет!'
                                                                ' Вам гарантировано 60+ fps при разрешении FullHD ', data=setup)
            if 199 <= CPU_id.id and 199 <= GPU_id.id:
                return render_template('check_fps.html', result='Ваш пк ниже минимальных системных требований,'
                                                                ' скорее всего игра будет нестабильна', data=setup)
        elif game == 'GTA 5':
            if CPU_id.id <= 150 and GPU_id.id <= 150:
                return render_template('check_fps.html', result='Ваш пк реально тянет!'
                                                                ' Вам гарантировано 60+ fps при разрешении FullHD ', data=setup)
            if 200 <= CPU_id.id and 200 <= GPU_id.id:
                return render_template('check_fps.html', result='Ваш пк ниже минимальных системных требований,'
                                                                ' скорее всего игра будет нестабильна', data=setup)
    else:
        return render_template('check_fps.html', data=setup)

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
from .models import User, Item, Post
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
    return render_template('index.html')


@main.route('/search-teammates')
@login_required
def search_teammates():
    posts = Post.query.all()
    if request.form.get('q'):
        q = request.form.get('q')
        f_posts = Post.query.filter_by(tag=q)
        return render_template('main_menu.html', data=f_posts)
    return render_template('main_menu.html', data=posts)


@main.route('/create-post', methods=['POST'])
@login_required
def create_post():
    title = request.form.get('title')
    description = request.form.get('description')
    tag = request.form.get('tag')

    # if len(title) < 1 or len(description) < 1 or len(tag) < 1:
    #     flash("Заполните все поля")
    #     return redirect(url_for('main.create-post'))

    new_post = Post(title=title, description=description, user_id=current_user.id, tag=tag)
    if os.path.exists(f'static/images/{new_post.id}.png'):
        db.session.add(new_post)
        db.session.commit()
    else:
        db.session.add(new_post)
        db.session.commit()
    return redirect(url_for('main.profile'))


@main.route('/create-post', methods=['GET'])
@login_required
def post():
    return render_template('offer.html')


@main.route('/profile')
@login_required
def profile():
    return render_template('profile.html')


@main.route('/own')
@login_required
def own_posts():
    if current_user.email == config["Admin"]["email"]:
        post = Post.query.all()
    else:
        post = Post.query.filter_by(user_id=current_user.id)
    return render_template('my_items.html', data=post)


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

        return redirect('/')
    else:
        return render_template('buy.html', data=post, pic=f'/static/images/{post.id}.png')


@main.route('/change/<int:num>', methods=['GET'])
@login_required
def change_get(num):
    post = Post.query.filter_by(id=num).first()
    return render_template("change.html", data=post)


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
        return redirect('/')

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
    return redirect('/profile')


# @main.route('/offer', methods=['POST'])
# def offer_post():
#     title = request.form.get('title')
#     price = request.form.get('price')
#     final_date = request.form.get('final_date')
#     description = request.form.get('description')
#
#     if len(title) < 1 or len(price) < 1 or len(final_date) < 1 or int(price) < 0:
#         flash("Заполните все поля")
#         return redirect(url_for('main.offer'))
#
#     new_item = Item(title=title, price=price, final_date=final_date, user=current_user, description=description)
#     if os.path.exists(f'static/images/{new_item.id}.png'):
#         db.session.add(new_item)
#         db.session.commit()
#     else:
#         db.session.add(new_item)
#         db.session.commit()
#     return redirect(url_for('main.profile'))


# else:
#  flash("Заполните все поля (в том числе добавьте картинку)")
#   return redirect(url_for('main.offer'))
# return redirect(url_for('main.profile'))


# @main.route('/offer', methods=['GET'])
# @login_required
# def offer():
#     return render_template('offer.html')


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@main.route('/uploads/<int:id>', methods=['GET', 'POST'])
def upload_file(id):
    item = Item.query.filter_by(id=id).first()
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
        if file and allowed_file(file.filename) and item.user_id == current_user.id:
            filename = secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, str(id) + ".png"))
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


# @main.route('/own')
# def own_lots():
#     if current_user.email == config["Admin"]["email"]:
#         item = Item.query.all()
#     else:
#         item = Item.query.filter_by(user_id=current_user.id)
#     return render_template('my_items.html', data=item)


# @main.route('/buy/<int:id>', methods=['GET', 'POST'])
# @login_required
# def buy(id):
#     email = request.form.get('email')
#     item = Item.query.filter_by(id=id).first()
#
#     api = Api(merchant_id=1396424,
#               secret_key='test')
#     checkout = Checkout(api=api)
#     data = {
#         "currency": "RUB",
#         "amount": str(item.price * 3) + '00'
#     }
#     url = checkout.url(data).get('checkout_url')
#
#     dt = str(datetime.fromisoformat(item.final_date))[:-3]
#     delta = datetime(int(dt[0:4]), int(dt[5:7]), int(dt[8:10])) - datetime.now()
#     final_delta = str(delta.days) + " дней ", str(delta.seconds // 3600) + " часов ", str(
#         (delta.seconds // 60) % 60) + " минут ", str(delta.seconds % 60) + " секунд "
#     final_delta = ''.join(final_delta)
#     if request.method == "POST" and request.form.get('bet'):
#
#         new_price = request.form.get('price')
#         mail = request.form.get('mail')
#         if int(new_price) > item.price:
#             setattr(item, 'price', new_price)
#             setattr(item, 'buyer', current_user.name)
#
#             db.session.commit()
#             if email is not None:
#                 send_email(email,
#                            f"Найден тиммейт! \n"
#                            f" Его Discord - {current_user.discord}. Его Steam - {current_user.steam}. \n"
#                            f" Удачной игры!")
#
#         else:
#             flash("Я все понимаю, но цена должна быть больше стартовой")
#
#         return redirect('/')
#     else:
#
#         dts = dt[8:10] + '-' + dt[5:7] + '-' + dt[0:4] + "  00:00"
#         return render_template('buy.html', data=item, dt=final_delta, url=url, pic=f'/static/images/{item.id}.png')


# @main.route('/change/<int:num>', methods=['GET'])
# @login_required
# def change_get(num):
#     item = Item.query.filter_by(id=num).first()
#     return render_template("change.html", data=item)


# @main.route('/change/<int:num>', methods=['POST'])
# @login_required
# def change(num):
#     if current_user.email == config["Admin"]["email"]:
#         items_id = Item.query.all()
#     else:
#         items_id = Item.query.filter_by(user_id=current_user.id).all()
#     title = request.form.get('title')
#     price = request.form.get('price')
#     final_date = request.form.get('final_date')
#     description = request.form.get('description')
#     item = Item.query.filter_by(id=num).first()
#
#     new_item = Item(id=item.id, title=title, price=price, final_date=final_date, description=description,
#                     user=current_user)
#     if item in items_id:
#         db.session.delete(item)
#         db.session.add(new_item)
#         db.session.commit()
#         return redirect('/')
#
#     else:
#         flash('У вас нет доступа к чужим объявлениям')
#         return redirect(url_for("main.profile"))


# @main.route('/delete/<int:num>')
# @login_required
# def delete(num):
#     if current_user.email == config["Admin"]["email"]:
#         items_id = Item.query.all()
#     else:
#         items_id = Item.query.filter_by(user_id=current_user.id).all()
#     item = Item.query.filter_by(id=num).first()
#
#     if item in items_id:
#         db.session.delete(item)
#         db.session.commit()
#         return redirect('/profile')
#     else:
#         flash('Вам не принадлежит этот товар. Возможно произошла ошибка')
#     return redirect('/profile')

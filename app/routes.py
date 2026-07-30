from app.models import User, Item, Message, Watchlist
from flask import jsonify
from app.models import Message
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, current_user, logout_user, login_required
from app import db, bcrypt
from app.models import User
import os
import secrets
from flask import current_app, request, abort
from werkzeug.utils import secure_filename
from app.models import Item


main = Blueprint('main', __name__)


@main.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.market'))

    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        password = request.form.get('password')
        security_question = request.form.get('security_question')
        security_answer = request.form.get('security_answer')

        if User.query.filter_by(email=email).first():
            flash('Email is already registered.', 'danger')
            return redirect(url_for('main.register'))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        hashed_answer = bcrypt.generate_password_hash(security_answer.lower().strip()).decode('utf-8')

        user = User(
            full_name=full_name,
            email=email,
            password_hash=hashed_password,
            security_question=security_question,
            security_answer_hash=hashed_answer
        )

        db.session.add(user)
        db.session.commit()
        flash('Account created successfully.', 'success')
        return redirect(url_for('main.login'))

    return render_template('register.html')


@main.route("/", methods=['GET', 'POST'])
@main.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.market'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user, remember=True)
            return redirect(url_for('main.market'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html')


@main.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))


@main.route("/forgot_password", methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('main.market'))

    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()

        if user and not request.form.get('security_answer'):
            return render_template('forgot_password.html', user=user, step=2)

        if user and request.form.get('security_answer'):
            answer = request.form.get('security_answer').lower().strip()
            new_password = request.form.get('new_password')

            if bcrypt.check_password_hash(user.security_answer_hash, answer):
                user.password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
                db.session.commit()
                flash('Password reset successfully. You can now log in.', 'success')
                return redirect(url_for('main.login'))
            else:
                flash('Incorrect security answer.', 'danger')
                return render_template('forgot_password.html', user=user, step=2)

    return render_template('forgot_password.html', step=1)


# HELPER FUNCTIONS
def save_picture(form_picture, folder):
    """Saves uploaded images securely and returns the generated filename."""
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext

    # Ensure the target directory exists
    upload_path = os.path.join(current_app.root_path, 'static', 'uploads', folder)
    os.makedirs(upload_path, exist_ok=True)

    picture_path = os.path.join(upload_path, picture_fn)
    form_picture.save(picture_path)
    return picture_fn

# USER PROFILE
@main.route("/profile", methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        bio_input = request.form.get('bio', '')
        current_user.bio = bio_input[:30]

        if 'profile_image' in request.files:
            pic = request.files['profile_image']
            if pic.filename != '':
                current_user.profile_image = save_picture(pic, 'profiles')

        db.session.commit()
        flash('Your profile has been updated.', 'success')
        return redirect(url_for('main.profile'))

    my_items = Item.query.filter_by(owner_id=current_user.id).order_by(Item.date_posted.desc()).all()

    # Pass my_items to the template
    return render_template('profile.html', items=my_items)

# MARKETPLACE & ITEMS
@main.route("/market")
@login_required
def market():
    items = Item.query.order_by(Item.date_posted.desc()).all()
    return render_template('market.html', items=items)


@main.route("/item/new", methods=['GET', 'POST'])
@login_required
def new_item():
    if request.method == 'POST':
        title = request.form.get('title')
        price = request.form.get('price')
        description = request.form.get('description')

        image_path = 'default_item.png'
        if 'image' in request.files:
            pic = request.files['image']
            if pic.filename != '':
                image_path = save_picture(pic, 'items')

        item = Item(
            title=title,
            price=price,
            description=description,
            image_path=image_path,
            owner=current_user
        )
        db.session.add(item)
        db.session.commit()

        flash('Item listed successfully!', 'success')
        return redirect(url_for('main.market'))

    return render_template('new_item.html')


@main.route("/item/<int:item_id>")
@login_required
def item_detail(item_id):
    item = Item.query.get_or_404(item_id)
    return render_template('item_detail.html', item=item)


@main.route("/item/<int:item_id>/delete", methods=['POST'])
@login_required
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    if item.owner != current_user:
        abort(403)  # Forbidden

    db.session.delete(item)
    db.session.commit()
    flash('Your listing has been deleted.', 'success')
    return redirect(url_for('main.market'))

# INBOX & LIVE CHAT
@main.route("/inbox")
@login_required
def inbox():
    messages = Message.query.filter(
        (Message.sender_id == current_user.id) | (Message.receiver_id == current_user.id)
    ).order_by(Message.timestamp.desc()).all()

    conversations = {}
    for msg in messages:
        other_user = msg.receiver if msg.sender_id == current_user.id else msg.sender
        key = (msg.item_id, other_user.id)

        if key not in conversations:
            conversations[key] = {
                'item': msg.item,
                'other_user': other_user,
                'last_message': msg.content,
                'timestamp': msg.timestamp
            }

    return render_template('inbox.html', conversations=conversations.values())


@main.route("/chat/<int:item_id>/<int:other_user_id>")
@login_required
def chat(item_id, other_user_id):
    item = Item.query.get_or_404(item_id)
    other_user = User.query.get_or_404(other_user_id)

    if item.owner_id == other_user.id:
        role = "Seller"
    elif item.owner_id == current_user.id:
        role = "Buyer"
    else:
        role = "Student"

    return render_template('chat.html', item=item, other_user=other_user, role=role)

# INTERNAL APIs FOR LIVE CHAT (AJAX)
@main.route("/api/messages/<int:item_id>/<int:other_user_id>")
@login_required
def get_messages(item_id, other_user_id):
    """Fetches message history between two users about a specific item."""
    msgs = Message.query.filter(
        (Message.item_id == item_id) &
        (((Message.sender_id == current_user.id) & (Message.receiver_id == other_user_id)) |
         ((Message.sender_id == other_user_id) & (Message.receiver_id == current_user.id)))
    ).order_by(Message.timestamp.asc()).all()

    chat_history = []
    for m in msgs:
        chat_history.append({
            'sender_id': m.sender_id,
            'content': m.content,
            'timestamp': m.timestamp.strftime("%b %d, %Y %I:%M %p")
        })
    return jsonify(chat_history)


@main.route("/api/send_message", methods=['POST'])
@login_required
def send_message():
    """Receives and stores a new message."""
    data = request.get_json()

    new_msg = Message(
        sender_id=current_user.id,
        receiver_id=data['receiver_id'],
        item_id=data['item_id'],
        content=data['content']
    )
    db.session.add(new_msg)
    db.session.commit()

    return jsonify({"status": "success"})

# PERSONALIZED WATCHLIST
@main.route("/item/<int:item_id>/watchlist", methods=['POST'])
@login_required
def toggle_watchlist(item_id):
    item = Item.query.get_or_404(item_id)

    # Check if the bookmark already exists
    bookmark = Watchlist.query.filter_by(user_id=current_user.id, item_id=item.id).first()

    if bookmark:
        # Toggle Off
        db.session.delete(bookmark)
        db.session.commit()
        flash('Item removed from your watchlist.', 'info')
    else:
        # Toggle On
        new_bookmark = Watchlist(user_id=current_user.id, item_id=item.id)
        db.session.add(new_bookmark)
        db.session.commit()
        flash('Item saved to your watchlist!', 'success')

    return redirect(url_for('main.item_detail', item_id=item.id))


@main.route("/watchlist")
@login_required
def watchlist():
    bookmarks = Watchlist.query.filter_by(user_id=current_user.id).all()
    return render_template('watchlist.html', bookmarks=bookmarks)
import os
from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import db, User, Tweet, Comment, Like
from forms import RegisterForm, LoginForm, TweetForm, CommentForm, ProfileForm


def _build_mysql_url_from_parts() -> str | None:
    host = os.getenv("MYSQLHOST") or os.getenv("DB_HOST")
    port = os.getenv("MYSQLPORT") or os.getenv("DB_PORT") or "3306"
    user = os.getenv("MYSQLUSER") or os.getenv("DB_USER")
    password = os.getenv("MYSQLPASSWORD") or os.getenv("DB_PASS")
    name = os.getenv("MYSQLDATABASE") or os.getenv("DB_NAME")
    if all([host, user, password, name]):
        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}?charset=utf8mb4"
    return None


def _resolve_db_url() -> str:
    # Railway farklı adlarla verebilir
    url = (
        os.getenv("DATABASE_URL")
        or os.getenv("MYSQL_URL")
        or os.getenv("MYSQLDATABASE_URL")
        or _build_mysql_url_from_parts()
    )
    if not url:
        raise RuntimeError(
            "Veritabanı URL bulunamadı. DATABASE_URL veya MYSQLHOST/PORT/USER/PASSWORD/DATABASE ayarla."
        )
    # SQLAlchemy 2 ile pymysql şemasını garanti et
    if url.startswith("mysql://"):
        url = url.replace("mysql://", "mysql+pymysql://", 1)
    return url


def create_app():
    app = Flask(__name__)

    # Config
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-me")
    app.config["SQLALCHEMY_DATABASE_URI"] = _resolve_db_url()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["UPLOAD_FOLDER"] = os.path.join("static", "avatars")
    app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # 2MB

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Extensions
    db.init_app(app)
    CSRFProtect(app)

    login_manager = LoginManager(app)
    login_manager.login_view = "login"

    @login_manager.user_loader
    def load_user(user_id):
        # SQLAlchemy 2.0 tarzı
        return db.session.get(User, int(user_id))

    with app.app_context():
        db.create_all()

    # Helpers
    def ensure_username(u: User):
        if not u.username:
            base = (u.email.split("@")[0])[:20]
            cand, i = base, 1
            while User.query.filter_by(username=cand).first():
                i += 1
                cand = f"{base}{i}"
            u.username = cand
            db.session.commit()

    def save_avatar(file_storage):
        filename = secure_filename(file_storage.filename or "")
        if "." not in filename:
            abort(400)
        ext = filename.rsplit(".", 1)[-1].lower()
        new_name = f"{current_user.id}.{ext}"
        path = os.path.join(app.config["UPLOAD_FOLDER"], new_name)
        file_storage.save(path)
        return new_name

    # Routes
    @app.route("/")
    def home():
        form = TweetForm() if current_user.is_authenticated else None
        tweets = (
            Tweet.query.order_by(Tweet.created_at.desc())
            .join(User)
            .add_entity(User)
            .all()
        )
        return render_template("home.html", form=form, tweets=tweets)

    @app.route("/tweet", methods=["POST"])
    @login_required
    def tweet():
        form = TweetForm()
        if form.validate_on_submit():
            t = Tweet(body=form.body.data, user_id=current_user.id)
            db.session.add(t)
            db.session.commit()
            flash("Tweet gönderildi", "success")
        else:
            flash("Tweet gönderilemedi", "danger")
        return redirect(url_for("home"))

    @app.route("/tweet/<int:tweet_id>/like", methods=["POST"])
    @login_required
    def like(tweet_id):
        t = Tweet.query.get_or_404(tweet_id)
        existing = Like.query.filter_by(user_id=current_user.id, tweet_id=t.id).first()
        if existing:
            db.session.delete(existing)
        else:
            db.session.add(Like(user_id=current_user.id, tweet_id=t.id))
        db.session.commit()
        return redirect(request.referrer or url_for("home"))

    @app.route("/tweet/<int:tweet_id>/comment", methods=["POST"])
    @login_required
    def comment(tweet_id):
        t = Tweet.query.get_or_404(tweet_id)
        form = CommentForm()
        if form.validate_on_submit():
            c = Comment(body=form.body.data, user_id=current_user.id, tweet_id=t.id)
            db.session.add(c)
            db.session.commit()
        else:
            flash("Yorum hatalı", "danger")
        return redirect(request.referrer or url_for("home"))

    @app.route("/u/<username>")
    def profile(username):
        u = User.query.filter_by(username=username).first_or_404()
        ensure_username(u)
        tweets = (
            Tweet.query.filter_by(user_id=u.id)
            .order_by(Tweet.created_at.desc())
            .all()
        )
        return render_template("profile.html", u=u, tweets=tweets)

    @app.route("/settings/profile", methods=["GET", "POST"])
    @login_required
    def profile_settings():
        ensure_username(current_user)
        form = ProfileForm(obj=current_user)
        if form.validate_on_submit():
            if form.username.data:
                current_user.username = form.username.data.strip()
            current_user.bio = form.bio.data
            if form.avatar.data:
                current_user.avatar = save_avatar(form.avatar.data)
            try:
                db.session.commit()
                flash("Profil güncellendi", "success")
                return redirect(url_for("profile", username=current_user.username))
            except Exception:
                db.session.rollback()
                flash("Kullanıcı adı kullanımda veya hata oluştu", "danger")
        return render_template("profile_settings.html", form=form)

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("home"))
        form = RegisterForm()
        if form.validate_on_submit():
            if User.query.filter_by(email=form.email.data.lower()).first():
                flash("E-posta kayıtlı", "warning")
                return redirect(url_for("register"))
            u = User(
                email=form.email.data.lower(),
                password_hash=generate_password_hash(form.password.data),
            )
            db.session.add(u)
            db.session.commit()
            ensure_username(u)
            login_user(u)
            flash("Kayıt tamamlandı", "success")
            return redirect(url_for("home"))
        return render_template("register.html", form=form)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("home"))
        form = LoginForm()
        if form.validate_on_submit():
            u = User.query.filter_by(email=form.email.data.lower()).first()
            if not u or not check_password_hash(u.password_hash, form.password.data):
                flash("Geçersiz bilgiler", "danger")
                return redirect(url_for("login"))
            login_user(u)
            flash("Giriş yapıldı", "success")
            return redirect(url_for("home"))
        return render_template("login.html", form=form)

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("Çıkış yapıldı", "info")
        return redirect(url_for("home"))

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

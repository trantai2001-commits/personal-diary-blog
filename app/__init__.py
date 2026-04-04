from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
import click

from config import Config

db = SQLAlchemy()
migrate = Migrate(render_as_batch=True)

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Vui lòng đăng nhập để truy cập trang quản trị."


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from app.routes import main_bp
    from app.auth import auth_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)

    @app.cli.command("init-db")
    def init_db():
        with app.app_context():
            db.create_all()
            print("Đã tạo database thành công.")

    @app.cli.command("create-admin")
    @click.option("--username", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def create_admin(username, password):
        from app.models import User

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            print("Username này đã tồn tại.")
            return

        user = User(username=username)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        print(f"Đã tạo admin: {username}")

    with app.app_context():
        db.create_all()
    return app
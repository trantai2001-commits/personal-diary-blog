import re
import unicodedata
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Post(db.Model):
    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(255), unique=True, index=True)
    content = db.Column(db.Text, nullable=False)
    cover_image_url = db.Column(db.String(500), nullable=True)
    cover_image_public_id = db.Column(db.String(255), nullable=True)
    local_image_url = db.Column(db.String(500), nullable=True)  # ảnh đính kèm lưu local
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_published = db.Column(db.Boolean, default=True)
    is_featured = db.Column(db.Boolean, default=False)

    @staticmethod
    def generate_slug(title, post_id=None):
        # Bước 1: Xóa dấu tiếng Việt
        slug = unicodedata.normalize('NFKD', title).encode('ASCII', 'ignore').decode('utf-8')
        # Bước 2: Giữ lại chữ, số và khoảng trắng, gạch ngang
        slug = re.sub(r'[^\w\s-]', '', slug).strip().lower()
        # Bước 3: Thay khoảng trắng bằng gạch ngang
        slug = re.sub(r'[-\s]+', '-', slug)
        
        if post_id:
            slug = f"{slug}-{post_id}"
        return slug

    @property
    def reading_time(self):
        words = len(self.content.split())
        return max(1, round(words / 200))

    def __repr__(self):
        return f"<Post {self.title}>"

class Todo(db.Model):
    __tablename__ = "todos"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Todo {self.title}>"


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500), nullable=False)
    category = db.Column(db.String(20), nullable=False, default="work")  # work | study | life
    is_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    CATEGORY_LABELS = {
        "work": "Làm việc",
        "study": "Học tập",
        "life": "Đời sống",
    }

    CATEGORY_ICONS = {
        "work": "💼",
        "study": "📚",
        "life": "🌿",
    }

    @property
    def category_label(self):
        return self.CATEGORY_LABELS.get(self.category, self.category)

    @property
    def category_icon(self):
        return self.CATEGORY_ICONS.get(self.category, "📋")

    def __repr__(self):
        return f"<Task {self.content[:30]}>"
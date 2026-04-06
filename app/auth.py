import os
import uuid
from datetime import datetime, date as date_type
from pathlib import Path

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename

from app import db
from app.models import User, Post, Todo, Task, DiaryEntry, get_vn_time
from app.cloudinary_utils import (
    is_allowed_image,
    upload_cover_image,
    delete_cloudinary_image,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/admin")

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}


def _is_allowed(filename: str) -> bool:
    return Path(filename).suffix.lower().lstrip(".") in ALLOWED_IMAGE_EXTENSIONS


def _save_local_image(file_storage) -> str | None:
    """Save uploaded file to static/uploads and return the URL path."""
    if not file_storage or not file_storage.filename:
        return None
    if not _is_allowed(file_storage.filename):
        return None

    ext = Path(file_storage.filename).suffix.lower()
    safe_name = f"{uuid.uuid4().hex}{ext}"
    upload_dir = Path(current_app.root_path) / "static" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_storage.save(upload_dir / safe_name)
    return f"/static/uploads/{safe_name}"


def _delete_local_image(url_path: str | None):
    """Delete a local uploaded image by its URL path."""
    if not url_path or not url_path.startswith("/static/uploads/"):
        return
    filename = url_path.split("/")[-1]
    full_path = Path(current_app.root_path) / "static" / "uploads" / filename
    try:
        full_path.unlink(missing_ok=True)
    except Exception:
        pass


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash("Đăng nhập thành công.", "success")
            return redirect(url_for("auth.dashboard"))
        else:
            flash("Sai username hoặc password.", "danger")

    return render_template("login.html")


@auth_bp.route("/dashboard")
@login_required
def dashboard():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template("admin_dashboard.html", posts=posts)


@auth_bp.route("/posts/new", methods=["GET", "POST"])
@login_required
def create_post():
    if request.method == "POST":
        title   = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        is_published = request.form.get("is_published") == "on"
        is_featured  = request.form.get("is_featured")  == "on"
        cover_file  = request.files.get("cover_image")
        inline_file = request.files.get("inline_image")

        if not title:
            flash("Tiêu đề không được để trống.", "danger")
            return render_template("create_post.html")

        if not content:
            flash("Nội dung không được để trống.", "danger")
            return render_template("create_post.html")

        # --- Cover image (Cloudinary) ---
        cover_image_url = None
        cover_image_public_id = None
        if cover_file and cover_file.filename:
            if not is_allowed_image(cover_file.filename):
                flash("Ảnh bìa chỉ chấp nhận: png, jpg, jpeg, webp, gif.", "danger")
                return render_template("create_post.html")
            uploaded = upload_cover_image(cover_file)
            cover_image_url = uploaded["url"]
            cover_image_public_id = uploaded["public_id"]

        # --- Inline / attached image (local static) ---
        local_image_url = None
        if inline_file and inline_file.filename:
            if not _is_allowed(inline_file.filename):
                flash("Ảnh đính kèm chỉ chấp nhận: png, jpg, jpeg, webp, gif.", "danger")
                return render_template("create_post.html")
            local_image_url = _save_local_image(inline_file)

        post = Post(
            title=title,
            content=content,
            cover_image_url=cover_image_url,
            cover_image_public_id=cover_image_public_id,
            local_image_url=local_image_url,
            is_published=is_published,
            is_featured=is_featured,
        )

        db.session.add(post)
        db.session.flush()
        post.slug = Post.generate_slug(title, post.id)
        db.session.commit()

        flash("Đã tạo bài viết thành công.", "success")
        return redirect(url_for("auth.dashboard"))

    return render_template("create_post.html")


@auth_bp.route("/posts/<int:post_id>/edit", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    post = db.session.get(Post, post_id)

    if post is None:
        flash("Không tìm thấy bài viết.", "danger")
        return redirect(url_for("auth.dashboard"))

    if request.method == "POST":
        title   = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        is_published = request.form.get("is_published") == "on"
        is_featured  = request.form.get("is_featured")  == "on"
        remove_cover  = request.form.get("remove_cover_image") == "on"
        remove_inline = request.form.get("remove_inline_image") == "on"
        cover_file  = request.files.get("cover_image")
        inline_file = request.files.get("inline_image")

        if not title:
            flash("Tiêu đề không được để trống.", "danger")
            return render_template("edit_post.html", post=post)

        if not content:
            flash("Nội dung không được để trống.", "danger")
            return render_template("edit_post.html", post=post)

        post.title   = title
        post.slug    = Post.generate_slug(title, post.id)
        post.content = content
        post.is_published = is_published
        post.is_featured  = is_featured

        # --- Cover image (Cloudinary) ---
        if remove_cover and not (cover_file and cover_file.filename):
            old_pid = post.cover_image_public_id
            post.cover_image_url = None
            post.cover_image_public_id = None
            if old_pid:
                try: delete_cloudinary_image(old_pid)
                except Exception: pass

        if cover_file and cover_file.filename:
            if not is_allowed_image(cover_file.filename):
                flash("Ảnh bìa chỉ chấp nhận: png, jpg, jpeg, webp, gif.", "danger")
                return render_template("edit_post.html", post=post)
            old_pid = post.cover_image_public_id
            uploaded = upload_cover_image(cover_file)
            post.cover_image_url = uploaded["url"]
            post.cover_image_public_id = uploaded["public_id"]
            if old_pid:
                try: delete_cloudinary_image(old_pid)
                except Exception: pass

        # --- Inline image (local) ---
        if remove_inline and not (inline_file and inline_file.filename):
            _delete_local_image(post.local_image_url)
            post.local_image_url = None

        if inline_file and inline_file.filename:
            if not _is_allowed(inline_file.filename):
                flash("Ảnh đính kèm chỉ chấp nhận: png, jpg, jpeg, webp, gif.", "danger")
                return render_template("edit_post.html", post=post)
            _delete_local_image(post.local_image_url)  # overwrite old
            post.local_image_url = _save_local_image(inline_file)

        db.session.commit()
        flash("Đã cập nhật bài viết thành công.", "success")
        return redirect(url_for("auth.dashboard"))

    return render_template("edit_post.html", post=post)


@auth_bp.route("/posts/<int:post_id>/delete", methods=["POST"])
@login_required
def delete_post(post_id):
    post = db.session.get(Post, post_id)

    if post is None:
        flash("Không tìm thấy bài viết để xóa.", "danger")
        return redirect(url_for("auth.dashboard"))

    old_public_id = post.cover_image_public_id
    old_local     = post.local_image_url

    db.session.delete(post)
    db.session.commit()

    if old_public_id:
        try: delete_cloudinary_image(old_public_id)
        except Exception: pass

    _delete_local_image(old_local)

    flash("Đã xóa bài viết thành công.", "success")
    return redirect(url_for("auth.dashboard"))


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Đã đăng xuất.", "success")
    return redirect(url_for("auth.login"))

@auth_bp.route("/todos", methods=["GET", "POST"])
@login_required
def todos():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if title:
            todo = Todo(title=title)
            db.session.add(todo)
            db.session.commit()
            flash("Đã thêm việc mới.", "success")
        return redirect(url_for("auth.todos"))

    todo_list = Todo.query.order_by(Todo.created_at.desc()).all()
    return render_template("admin_todo.html", todos=todo_list)

@auth_bp.route("/todos/<int:todo_id>/toggle", methods=["POST"])
@login_required
def toggle_todo(todo_id):
    todo = db.session.get(Todo, todo_id)
    if todo:
        todo.is_completed = not todo.is_completed
        db.session.commit()
    return redirect(url_for("auth.todos"))

@auth_bp.route("/todos/<int:todo_id>/delete", methods=["POST"])
@login_required
def delete_todo(todo_id):
    todo = db.session.get(Todo, todo_id)
    if todo:
        db.session.delete(todo)
        db.session.commit()
    return redirect(url_for("auth.todos"))


# ── Task Management (Work / Study / Life) ──────────────────────

@auth_bp.route("/tasks", methods=["GET", "POST"])
@login_required
def tasks():
    if request.method == "POST":
        content  = request.form.get("content", "").strip()
        category = request.form.get("category", "work").strip()
        if category not in ("work", "study", "life"):
            category = "work"
        if content:
            # Handle optional date from form
            task_date_str = request.form.get("task_date", "")
            created_at = get_vn_time()
            if task_date_str:
                try:
                    # Parse YYYY-MM-DD from HTML5 date input
                    selected_date = date_type.fromisoformat(task_date_str)
                    # Keep current time but change date
                    now = get_vn_time()
                    created_at = datetime.combine(selected_date, now.time())
                except ValueError:
                    pass

            task = Task(content=content, category=category, created_at=created_at)
            db.session.add(task)
            db.session.commit()
            flash("Đã thêm task mới.", "success")
        return redirect(url_for("auth.tasks"))

    filter_cat = request.args.get("cat", "")
    query = Task.query
    if filter_cat in ("work", "study", "life"):
        query = query.filter_by(category=filter_cat)
    task_list = query.order_by(Task.created_at.desc()).all()
    return render_template(
        "admin_tasks.html",
        tasks=task_list,
        filter_cat=filter_cat,
        today=get_vn_time().date()
    )


@auth_bp.route("/tasks/<int:task_id>/toggle", methods=["POST"])
@login_required
def toggle_task(task_id):
    task = db.session.get(Task, task_id)
    if task:
        task.is_completed = not task.is_completed
        db.session.commit()
    return redirect(url_for("auth.tasks"))


@auth_bp.route("/tasks/<int:task_id>/delete", methods=["POST"])
@login_required
def delete_task(task_id):
    task = db.session.get(Task, task_id)
    if task:
        db.session.delete(task)
        db.session.commit()
        flash("Đã xóa task.", "success")
    return redirect(url_for("auth.tasks"))


# ── Diary Management (Emotions / Notes) ─────────────────────

@auth_bp.route("/diary", methods=["GET", "POST"])
@login_required
def diary():
    if request.method == "POST":
        content = request.form.get("content", "").strip()
        emotion = request.form.get("emotion", "neutral").strip()
        if not content:
            flash("Nội dung không được để trống.", "danger")
        else:
            entry = DiaryEntry(content=content, emotion=emotion)
            db.session.add(entry)
            db.session.commit()
            flash("Đã lưu nhật ký.", "success")
        return redirect(url_for("auth.diary"))

    entries = DiaryEntry.query.order_by(DiaryEntry.created_at.desc()).all()
    # Mảng để map emoji cho form
    emotions = DiaryEntry.EMOTION_ICONS
    return render_template("admin_diary.html", entries=entries, emotions=emotions)

@auth_bp.route("/diary/<int:entry_id>/delete", methods=["POST"])
@login_required
def delete_diary(entry_id):
    entry = db.session.get(DiaryEntry, entry_id)
    if entry:
        db.session.delete(entry)
        db.session.commit()
        flash("Đã xóa nhật ký.", "success")
    return redirect(url_for("auth.diary"))
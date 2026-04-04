from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user

from app import db
from app.models import User, Post
from app.cloudinary_utils import (
    is_allowed_image,
    upload_cover_image,
    delete_cloudinary_image,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/admin")


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
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        is_published = request.form.get("is_published") == "on"
        is_featured = request.form.get("is_featured") == "on"
        cover_file = request.files.get("cover_image")

        if not title:
            flash("Tiêu đề không được để trống.", "danger")
            return render_template("create_post.html")

        if not content:
            flash("Nội dung không được để trống.", "danger")
            return render_template("create_post.html")

        cover_image_url = None
        cover_image_public_id = None

        if cover_file and cover_file.filename:
            if not is_allowed_image(cover_file.filename):
                flash("Ảnh bìa chỉ chấp nhận: png, jpg, jpeg, webp, gif.", "danger")
                return render_template("create_post.html")

            uploaded = upload_cover_image(cover_file)
            cover_image_url = uploaded["url"]
            cover_image_public_id = uploaded["public_id"]

        post = Post(
            title=title,
            content=content,
            cover_image_url=cover_image_url,
            cover_image_public_id=cover_image_public_id,
            is_published=is_published,
            is_featured=is_featured,
        )

        db.session.add(post)
        db.session.flush() # Để lấy post.id auto-increment
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
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        is_published = request.form.get("is_published") == "on"
        is_featured = request.form.get("is_featured") == "on"
        remove_cover_image = request.form.get("remove_cover_image") == "on"
        cover_file = request.files.get("cover_image")

        if not title:
            flash("Tiêu đề không được để trống.", "danger")
            return render_template("edit_post.html", post=post)

        if not content:
            flash("Nội dung không được để trống.", "danger")
            return render_template("edit_post.html", post=post)

        post.title = title
        post.slug = Post.generate_slug(title, post.id)
        post.content = content
        post.is_published = is_published
        post.is_featured = is_featured

        if remove_cover_image and not (cover_file and cover_file.filename):
            old_public_id = post.cover_image_public_id
            post.cover_image_url = None
            post.cover_image_public_id = None

            if old_public_id:
                try:
                    delete_cloudinary_image(old_public_id)
                except Exception:
                    pass

        if cover_file and cover_file.filename:
            if not is_allowed_image(cover_file.filename):
                flash("Ảnh bìa chỉ chấp nhận: png, jpg, jpeg, webp, gif.", "danger")
                return render_template("edit_post.html", post=post)

            old_public_id = post.cover_image_public_id

            uploaded = upload_cover_image(cover_file)
            post.cover_image_url = uploaded["url"]
            post.cover_image_public_id = uploaded["public_id"]

            if old_public_id:
                try:
                    delete_cloudinary_image(old_public_id)
                except Exception:
                    pass

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

    db.session.delete(post)
    db.session.commit()

    if old_public_id:
        try:
            delete_cloudinary_image(old_public_id)
        except Exception:
            pass

    flash("Đã xóa bài viết thành công.", "success")
    return redirect(url_for("auth.dashboard"))


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Đã đăng xuất.", "success")
    return redirect(url_for("auth.login"))
from flask import Blueprint, render_template, abort

from app.models import Post

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    posts = Post.query.filter_by(is_published=True).order_by(Post.is_featured.desc(), Post.created_at.desc()).all()
    return render_template("index.html", posts=posts)


@main_bp.route("/bai-viet/<slug>")
def post_detail(slug):
    post = Post.query.filter_by(slug=slug, is_published=True).first()

    if post is None:
        abort(404)

    return render_template("post_detail.html", post=post)
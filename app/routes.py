import calendar
from datetime import datetime
from flask import Blueprint, render_template, abort, request, jsonify

from app.models import Post

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    posts = Post.query.filter_by(is_published=True).order_by(Post.is_featured.desc(), Post.created_at.desc()).all()

    # Calendar data
    today = datetime.today()
    year  = int(request.args.get('year',  today.year))
    month = int(request.args.get('month', today.month))

    # Clamp to valid range
    if month < 1:  month = 12; year -= 1
    if month > 12: month = 1;  year += 1

    cal = calendar.Calendar(firstweekday=0)  # Monday first
    weeks = cal.monthdatescalendar(year, month)

    # Collect published post dates for this month
    all_published = Post.query.filter_by(is_published=True).all()
    post_dates = set(
        p.created_at.date()
        for p in all_published
        if p.created_at.year == year and p.created_at.month == month
    )

    # Build post date -> slug map for linking
    post_date_slugs = {}
    for p in all_published:
        if p.created_at.year == year and p.created_at.month == month:
            d = p.created_at.date()
            if d not in post_date_slugs:
                post_date_slugs[d] = p.slug or str(p.id)

    import datetime as dt
    prev_month = month - 1 if month > 1 else 12
    prev_year  = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year  = year if month < 12 else year + 1

    month_names_vi = [
        '', 'Tháng 1', 'Tháng 2', 'Tháng 3', 'Tháng 4',
        'Tháng 5', 'Tháng 6', 'Tháng 7', 'Tháng 8',
        'Tháng 9', 'Tháng 10', 'Tháng 11', 'Tháng 12'
    ]

    return render_template(
        "index.html",
        posts=posts,
        cal_weeks=weeks,
        cal_year=year,
        cal_month=month,
        cal_month_name=month_names_vi[month],
        cal_today=today.date(),
        post_dates=post_dates,
        post_date_slugs=post_date_slugs,
        prev_year=prev_year,
        prev_month=prev_month,
        next_year=next_year,
        next_month=next_month,
    )


@main_bp.route("/bai-viet/<slug>")
def post_detail(slug):
    post = Post.query.filter_by(slug=slug, is_published=True).first()

    # Fallback cho các bài viết cũ chưa có slug (lấy ID)
    if post is None and slug.isdigit():
        post = Post.query.filter_by(id=int(slug), is_published=True).first()

    if post is None:
        abort(404)

    return render_template("post_detail.html", post=post)
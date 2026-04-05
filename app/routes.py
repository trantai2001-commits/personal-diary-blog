import calendar
from datetime import datetime
from flask import Blueprint, render_template, abort, request, jsonify

from app.models import Post

main_bp = Blueprint("main", __name__)


PER_PAGE = 5

@main_bp.route("/")
def home():
    # Calendar data
    today = datetime.today()
    year  = int(request.args.get('year',  today.year))
    month = int(request.args.get('month', today.month))
    page  = max(1, int(request.args.get('page', 1)))

    # Clamp month to valid range
    if month < 1:  month = 12; year -= 1
    if month > 12: month = 1;  year += 1

    # --- Pagination ---
    all_published = Post.query.filter_by(is_published=True)
    total = all_published.count()
    total_pages = max(1, -(-total // PER_PAGE))   # ceiling division
    page = min(page, total_pages)

    posts = (
        all_published
        .order_by(Post.is_featured.desc(), Post.created_at.desc())
        .offset((page - 1) * PER_PAGE)
        .limit(PER_PAGE)
        .all()
    )

    # --- Calendar ---
    cal   = calendar.Calendar(firstweekday=0)
    weeks = cal.monthdatescalendar(year, month)

    all_posts_for_cal = Post.query.filter_by(is_published=True).all()
    post_dates = set(
        p.created_at.date()
        for p in all_posts_for_cal
        if p.created_at.year == year and p.created_at.month == month
    )
    post_date_slugs = {}
    for p in all_posts_for_cal:
        if p.created_at.year == year and p.created_at.month == month:
            d = p.created_at.date()
            if d not in post_date_slugs:
                post_date_slugs[d] = p.slug or str(p.id)

    prev_month = month - 1 if month > 1 else 12
    prev_year  = year     if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year  = year      if month < 12 else year + 1

    month_names_vi = [
        '', 'Tháng 1', 'Tháng 2', 'Tháng 3', 'Tháng 4',
        'Tháng 5', 'Tháng 6', 'Tháng 7', 'Tháng 8',
        'Tháng 9', 'Tháng 10', 'Tháng 11', 'Tháng 12'
    ]

    return render_template(
        "index.html",
        posts=posts,
        page=page,
        total_pages=total_pages,
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
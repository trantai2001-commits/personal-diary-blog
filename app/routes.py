import calendar
from datetime import datetime, date as date_type
from flask import Blueprint, render_template, abort, request, redirect, url_for

from app import db
from app.models import Post, Task

main_bp = Blueprint("main", __name__)

PER_PAGE = 5


@main_bp.route("/")
def home():
    today = datetime.today()
    year  = int(request.args.get('year',  today.year))
    month = int(request.args.get('month', today.month))
    page  = max(1, int(request.args.get('page', 1)))

    # Clamp month
    if month < 1:  month = 12; year -= 1
    if month > 12: month = 1;  year += 1

    # --- Pagination ---
    all_published = Post.query.filter_by(is_published=True)
    total       = all_published.count()
    total_pages = max(1, -(-total // PER_PAGE))
    page        = min(page, total_pages)

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

    # --- On This Day ---
    on_this_day = (
        Post.query
        .filter(
            Post.is_published == True,
            # SQLite: strftime extracts month-day
            Post.created_at.isnot(None),
        )
        .all()
    )
    # Filter in Python: same month+day, different year
    on_this_day = [
        p for p in on_this_day
        if p.created_at.month == today.month
        and p.created_at.day   == today.day
        and p.created_at.year  != today.year
    ]
    on_this_day.sort(key=lambda p: p.created_at.year, reverse=True)

    # --- Tasks for sidebar ---
    # Show tasks for today by default, or for clicked date
    task_date_str = request.args.get('task_date', '')
    if task_date_str:
        try:
            task_date = date_type.fromisoformat(task_date_str)
        except ValueError:
            task_date = today.date()
    else:
        task_date = today.date()

    day_tasks = (
        Task.query
        .filter(
            db.func.date(Task.created_at) == task_date
        )
        .order_by(Task.category, Task.created_at)
        .all()
    )

    # Group tasks by category
    tasks_by_cat = {'work': [], 'study': [], 'life': []}
    for t in day_tasks:
        if t.category in tasks_by_cat:
            tasks_by_cat[t.category].append(t)

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
        on_this_day=on_this_day,
        tasks_by_cat=tasks_by_cat,
        task_date=task_date,
    )


@main_bp.route("/bai-viet/<slug>")
def post_detail(slug):
    post = Post.query.filter_by(slug=slug, is_published=True).first()

    if post is None and slug.isdigit():
        post = Post.query.filter_by(id=int(slug), is_published=True).first()

    if post is None:
        abort(404)

    return render_template("post_detail.html", post=post)


@main_bp.route("/tim-kiem")
def search():
    q = request.args.get("q", "").strip()
    results = []
    if q:
        like = f"%{q}%"
        results = (
            Post.query
            .filter(
                Post.is_published == True,
                (Post.title.ilike(like)) | (Post.content.ilike(like))
            )
            .order_by(Post.created_at.desc())
            .all()
        )
    return render_template("search.html", q=q, results=results)


@main_bp.route("/tasks/<int:task_id>/toggle", methods=["POST"])
def toggle_task_public(task_id):
    """Toggle task completion from the homepage sidebar."""
    task = db.session.get(Task, task_id)
    if task:
        task.is_completed = not task.is_completed
        db.session.commit()
    # Redirect back to referrer or home
    return redirect(request.referrer or url_for('main.home'))
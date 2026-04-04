import os
from app import create_app, db
from app.models import Post

app = create_app()

def backfill():
    with app.app_context():
        posts = Post.query.filter((Post.slug == None) | (Post.slug == '')).all()
        for post in posts:
            post.slug = Post.generate_slug(post.title, post.id)
            print(f"Update post {post.id} -> {post.slug}")
        
        db.session.commit()
        print(f"Đã cập nhật slug cho {len(posts)} bài viết.")

if __name__ == "__main__":
    backfill()

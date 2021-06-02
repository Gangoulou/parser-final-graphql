from datetime import date

from app import db, User, Post
db.create_all()
john = User(username='test')
post = Post()
post.title = "Hello World"
post.body = "This is the first post"
post.date = date.today()
post.author = john
db.session.add(post)
db.session.add(john)
db.session.commit()
print(User.query.all())
print(Post.query.all())
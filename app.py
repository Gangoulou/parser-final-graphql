import atexit
import os
from datetime import date

import graphene
import pika
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from graphene_sqlalchemy import SQLAlchemyObjectType, SQLAlchemyConnectionField
from flask_graphql import GraphQLView
from selenium import webdriver
from flask_rabbitmq import RabbitMQ

app = Flask(__name__)
app.debug = True

basedir = os.path.abspath(os.path.dirname(__file__))
# Configs
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'data.sqlite')
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
# Modules
db = SQLAlchemy(app)

# connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
# channel = connection.channel()
# channel.queue_declare(queue='hello')
# channel.basic_publish(exchange='',
#                       routing_key='hello',
#                       body='Hello World!')
# print(" [x] Sent 'Hello World!'")

# app.config.setdefault('RABMQ_RABBITMQ_URL', 'amqp://username:password@ip:port/dev_vhost')
# app.config.setdefault('RABMQ_SEND_EXCHANGE_NAME', 'flask_rabmq')
# app.config.setdefault('RABMQ_SEND_EXCHANGE_TYPE', 'topic')
# app.config.setdefault('RABMQ_SEND_POOL_SIZE', 2)
# app.config.setdefault('RABMQ_SEND_POOL_ACQUIRE_TIMEOUT', 5)
#
# ramq = RabbitMQ()
# ramq.init()


# Models
class User(db.Model):
    __tablename__ = 'users'
    uuid = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(256), index=True, unique=True)
    posts = db.relationship('Post', backref='author')

    def __repr__(self):
        return '<User %r>' % self.username


class Post(db.Model):
    __tablename__ = 'posts'
    uuid = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256), index=True)
    body = db.Column(db.Text)
    date = db.Column(db.Date)
    author_id = db.Column(db.Integer, db.ForeignKey('users.uuid'))

    def __repr__(self):
        return '<Post %r>' % self.title


# Schema Objects
class PostObject(SQLAlchemyObjectType):
    class Meta:
        model = Post
        interfaces = (graphene.relay.Node,)


class UserObject(SQLAlchemyObjectType):
    class Meta:
        model = User
        interfaces = (graphene.relay.Node,)


class Query(graphene.ObjectType):
    node = graphene.relay.Node.Field()
    all_posts = SQLAlchemyConnectionField(PostObject)
    all_users = SQLAlchemyConnectionField(UserObject)


class CreatePost(graphene.Mutation):
    class Arguments:
        title = graphene.String(required=True)
        body = graphene.String(required=True)
        date = graphene.String(required=True)
        username = graphene.String(required=True)

    post = graphene.Field(lambda: PostObject)

    def mutate(self, info, title, body, username, date):
        user = User.query.filter_by(username=username).first()
        post = Post(title=title, body=body, date=date)
        if user is not None:
            post.author = user
        db.session.add(post)
        db.session.commit()
        return CreatePost(post=post)


class Mutation(graphene.ObjectType):
    create_post = CreatePost.Field()

@app.route('/add-job/<cmd>')
def add(cmd):
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
    channel = connection.channel()
    channel.queue_declare(queue='task_queue', durable=True)
    channel.basic_publish(
        exchange='',
        routing_key='task_queue',
        body=cmd,
        properties=pika.BasicProperties(
            delivery_mode=2,  # make message persistent
        ))
    connection.close()
    return " [x] Sent: %s" % cmd

schema = graphene.Schema(query=Query, mutation=Mutation)


@app.route('/')
def index():
    startParser()
    post = CreatePost.mutate(title='test', body='test', info='test',
                             self=True, username='test', date=date.today())
    return '<p> Hello Scrawler!</p>'


@app.route('/getPost')
def getPost():
    startParser()
    # post = CreatePost.mutate(title='test', body='test', info='test',
    #                          self=True, username='test', date=date.today())
    return '<p> Hello Scrawler!</p>'


def parse_pages():
    browser = webdriver.Chrome()
    browser.get('https://best.znaj.ua/')
    for i in range(0, 10):
        Titles = browser.find_elements_by_tag_name('h4')
        for title in Titles:
            print(title.text, '\n')
            post = CreatePost.mutate(title=title.text, body='', info='',
                                     self=True, username='', date=date.today())
    return browser.quit()

    # chrome_options = Options()
    # chrome_options.add_argument('--verbose')
    # chrome_options.add_argument('--headless')
    # chrome_options.add_argument('--disable-gpu')
    # chrome_options.add_argument('--no-sandbox')
    # chrome_options.add_argument('--disable-dev-shm-usage')
    # # browser = webdriver.Remote(
    # #     command_executor='http://localhost:53645/',
    # #     desired_capabilities=chrome_options.to_capabilities())
    # browser = webdriver.Chrome()
    # browser.get('http://www.znaj.ua')
    # Titles = browser.find_elements_by_tag_name('h4')
    # for title in Titles:
    #
    # return Titles


def startParser():
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=parse_pages, trigger="interval", seconds=10)
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())


app.add_url_rule(
    '/graphql',
    view_func=GraphQLView.as_view(
        'graphql',
        schema=schema,
        graphiql=True  # for having the GraphiQL interface
    )
)

##################################
if __name__ == '__main__':
    app.run(host='0.0.0.0')

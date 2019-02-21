import os
import uuid

import smartninja_redis

from flask import render_template, request, redirect, url_for, Blueprint
from models.user import User
from models.topic import Topic

redis = smartninja_redis.from_url(os.environ.get("REDIS_URL"))

topic_handlers = Blueprint("topic", __name__)


@topic_handlers.route("/")
def index():
    # check if user is authenticated based on session_token
    session_token = request.cookies.get("session_token")
    user = User.get_by_session_token(session_token=session_token)

    # get all topics from db
    topics = Topic.get_all_topics()

    return render_template("topic/index.html", user=user, topics=topics)


@topic_handlers.route("/create-topic", methods=["GET", "POST"])
def topic_create():
    # get current user (author)
    session_token = request.cookies.get("session_token")
    user = User.get_by_session_token(session_token=session_token)

    # only logged in users can create a topic
    if not user:
        return redirect(url_for('auth.login'))

    # GET method
    if request.method == "GET":
        csrf_token = str(uuid.uuid4())  # create CSRF token
        redis.set(name=user.username, value=csrf_token)  # store CSRF token into Redis for that specific user
        return render_template("topic/topic_create.html", user=user, csrf_token=csrf_token)  # send CSRF token into HTML template

    # POST method
    elif request.method == "POST":
        csrf = request.form.get("csrf")  # csrf from HTML
        redis_csrf = redis.get(name=user.username).decode()  # csrf from Redis (needs to be decoded from byte string)

        # if they match, allow user to create a topic
        if csrf and csrf == redis_csrf:
            title = request.form.get("title")
            text = request.form.get("text")

            # create a Topic object
            topic = Topic(title=title, text=text, author_id=user._id, author_username=user.username)
            topic.insert()

            return redirect(url_for('topic.index'))
        else:
            return "CSRF token is not valid!"


@topic_handlers.route("/topic/<topic_id>", methods=["GET"])
def topic_details(topic_id):
    topic = Topic.get_by_id(topic_id=topic_id)

    # get current user
    session_token = request.cookies.get("session_token")
    user = User.get_by_session_token(session_token=session_token)

    return render_template("topic/topic_details.html", topic=topic, user=user)


@topic_handlers.route("/topic/<topic_id>/edit", methods=["GET", "POST"])
def topic_edit(topic_id):
    topic = Topic.get_by_id(topic_id=topic_id)

    if request.method == "GET":
        return render_template("topic/topic_edit.html", topic=topic)

    elif request.method == "POST":
        title = request.form.get("title")
        text = request.form.get("text")

        # get current user (author)
        session_token = request.cookies.get("session_token")
        user = User.get_by_session_token(session_token=session_token)

        # check if user is logged in and user is author
        if not user:
            return redirect(url_for('auth.login'))
        elif topic.author_id != user._id:
            return "You are not the author!"
        else:  # if user IS logged in and current user IS author
            Topic.edit_topic(topic_id=topic_id, updates_dict={"title": title, "text": text})
            return redirect(url_for('topic.topic_details', topic_id=topic_id))


@topic_handlers.route("/topic/<topic_id>/delete", methods=["GET", "POST"])
def topic_delete(topic_id):
    topic = Topic.get_by_id(topic_id=topic_id)

    if request.method == "GET":
        return render_template("topic/topic_delete.html", topic=topic)

    elif request.method == "POST":
        # get current user (author)
        session_token = request.cookies.get("session_token")
        user = User.get_by_session_token(session_token=session_token)

        # check if user is logged in and user is author
        if not user:
            return redirect(url_for('auth.login'))
        elif topic.author_id != user._id:
            return "You are not the author!"
        else:  # if user IS logged in and current user IS author
            Topic.delete_topic(topic_id=topic_id)
            return redirect(url_for('topic.index'))

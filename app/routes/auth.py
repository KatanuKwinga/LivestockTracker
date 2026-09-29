"""Authentication routes: farmer self-registration, login/logout, and a
farmer-only route for creating worker accounts."""

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from flask_mail import Message
from sqlalchemy.exc import IntegrityError

from app.extensions import bcrypt, db, mail
from app.forms import FarmerRegistrationForm, LoginForm, RequestResetForm, ResetPasswordForm, WorkerCreationForm
from app.models import Farmer, User, Worker

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def send_reset_email(user):
    """Build and send the actual password-reset email.

    Split out from the route below so the route stays focused on request
    handling, and so tests can call this directly if they ever want to
    check the email content without going through a full HTTP request.
    """
    token = user.get_reset_token()
    reset_url = url_for("auth.reset_password", token=token, _external=True)
    # _external=True is what makes this a full https://... link instead of
    # just a path — essential here since the link is going into an email,
    # read outside the context of our own site.

    message = Message(
        subject="Livestock Tracker — Password Reset Request",
        recipients=[user.email],
        body=(
            f"Hi {user.name},\n\n"
            "Someone (hopefully you) requested a password reset for your "
            "Livestock Tracker account. Click the link below to choose a "
            "new password:\n\n"
            f"{reset_url}\n\n"
            "This link expires in 30 minutes. If you didn't request this, "
            "you can safely ignore this email — your password won't change."
        ),
    )
    mail.send(message)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = FarmerRegistrationForm()
    if form.validate_on_submit():
        # We hash the password with bcrypt before it ever touches the database 
        hashed_pw = bcrypt.generate_password_hash(form.password.data).decode("utf-8")

        user = User(
            name=form.name.data.strip(),
            email=form.email.data.lower().strip(),
            password_hash=hashed_pw,
            phone=form.phone.data.strip() if form.phone.data else None,
        )
        db.session.add(user)
        # flush() sends the INSERT to the database and gets user.id back, without committing the transaction yet, we need that id to build the Farmer row below
        try:
            db.session.flush()

            farmer = Farmer(user_id=user.id)
            db.session.add(farmer)
            db.session.commit()
        except IntegrityError:
            # Validate_email() above already checks for a duplicate before we get here, but that check and this
            # INSERT aren't atomic — two requests submitted at nearly the
            # same instant (a double-click, or a resubmitted form) can
            # both pass validation before either has committed, and the
            # database's own UNIQUE constraint on email is what actually
            # catches the second one. Without this except block that
            # shows up to the user as a raw server error instead of a
            # normal "try again" message.
            db.session.rollback()
            flash("An account with this email already exists.", "danger")
            return render_template("auth/register.html", form=form)

        flash("Account created — please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()

        # bcrypt.check_password_hash re-hashes the submitted password with the same salt stored in password_hash and compares the results.
       
        if user and bcrypt.check_password_hash(user.password_hash, form.password.data):
            # A User row is either a farmer or a worker.
            # We log in whichever account object actually exists
            account = user.farmer or user.worker
            login_user(account)
            flash(f"Welcome back, {account.name}.", "success")

            next_page = request.args.get("next")
            return redirect(next_page or url_for("main.dashboard"))

        # Deliberately vague due to attackers
        flash("Invalid email or password.", "danger")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/workers/new", methods=["GET", "POST"])
@login_required
def new_worker():
    # Role-based access control, Only a Farmer account (not a Worker) may reach this page at all.
    if not isinstance(current_user, Farmer):
        flash("Only a farmer account can add workers.", "danger")
        return redirect(url_for("main.dashboard"))

    form = WorkerCreationForm()
    if form.validate_on_submit():
        hashed_pw = bcrypt.generate_password_hash(form.password.data).decode("utf-8")

        user = User(
            name=form.name.data.strip(),
            email=form.email.data.lower().strip(),
            password_hash=hashed_pw,
            phone=form.phone.data.strip() if form.phone.data else None,
        )
        db.session.add(user)
        try:
            db.session.flush()

            # The new worker is hard-linked to current_user.farmer_i
            # From the moment it's created it can only ever belong to this farm.
            worker = Worker(user_id=user.id, farmer_id=current_user.farmer_id)
            db.session.add(worker)
            db.session.commit()
        except IntegrityError:
            # Same race condition as in register() above 
            db.session.rollback()
            flash("An account with this email already exists.", "danger")
            return render_template("auth/new_worker.html", form=form)

        flash(f"Worker account created for {user.name}.", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("auth/new_worker.html", form=form)


@auth_bp.route("/reset-password", methods=["GET", "POST"])
def reset_request():
    """Step 1: farmer or worker types in their email, we (maybe) email
    them a reset link."""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()

        # Deliberately send the *same* flash message whether or not the
        # account exists, and only actually email when it does. If we
        # showed a different message for "no account with that email",
        # anyone could use this form to check which addresses are
        # registered — the same enumeration risk called out in login()'s
        # "Invalid email or password" comment.
        if user:
            try:
                send_reset_email(user)
            except Exception:
                # A real SMTP failure (bad credentials, network issue,
                # Gmail rate limit) shouldn't crash the request or leak
                # server internals to the user — log it for us to see,
                # show the same generic message either way.
                current_app.logger.exception("Failed to send password reset email")

        flash(
            "If an account with that email exists, we've sent instructions to reset your password.",
            "info",
        )
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_request.html", form=form)


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    """Step 2: the link from the email lands here. verify_reset_token
    does the heavy lifting — checking the signature and the 30-minute
    expiry — so this route only has to react to whether that came back
    with a real user or None."""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    user = User.verify_reset_token(token)
    if user is None:
        flash("That password reset link is invalid or has expired.", "danger")
        return redirect(url_for("auth.reset_request"))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.password_hash = bcrypt.generate_password_hash(form.password.data).decode("utf-8")
        db.session.commit()
        flash("Your password has been updated — please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", form=form)

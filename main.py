from flask import Flask, render_template, redirect, url_for
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
import requests

MOVIE_DB_SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJjODlhMmYwNDhiZGNiZWM1NDUzM2Q4ZGQ3NjBlNTE4NiIsIm5iZiI6MTc1MTE5ODQ4OC4wMzcsInN1YiI6IjY4NjEyYjE4NWZjYTg0N2IzMDkxNWE1YSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.o2qbOQ5HW2YfQRpcJbyZuP34249YzmbrsYuJrft5_oI"
MOVIE_DB_API_KEY = "c89a2f048bdcbec54533d8dd760e5186"

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "accept": "application/json"
}


app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
Bootstrap5(app)

class Base(DeclarativeBase):
  pass

db = SQLAlchemy(model_class=Base)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///movies.db"
db.init_app(app)

class Movie(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=False)
    ranking: Mapped[int] = mapped_column(Integer, nullable=False)
    review: Mapped[str] = mapped_column(String(500), nullable=False)
    img_url: Mapped[str] = mapped_column(String(500), nullable=False)


with app.app_context():
    db.create_all()

class EditMovieForm(FlaskForm):
    rating = StringField('Your Rating Out of 10', validators=[DataRequired()])
    review = StringField('Your Review', validators=[DataRequired()])
    submit = SubmitField('Done')

class AddMovieForm(FlaskForm):
    title = StringField('Movie Title', validators=[DataRequired()])
    submit = SubmitField('Search')

@app.route("/")
def home():
    all_movies = db.session.execute(db.select(Movie)).scalars()
    return render_template("index.html", movies=all_movies)

@app.route("/update/<int:id>", methods=["GET", "POST"])
def update(id):
    movie = db.session.get(Movie, id)
    if not movie:
        return "Movie not found", 404
    
    form = EditMovieForm(obj=movie)

    if form.validate_on_submit():
        movie.rating = float(form.rating.data)
        movie.review = form.review.data
        db.session.commit()
        return redirect(url_for("home"))

    return render_template("edit.html", movie=movie, form=form)

@app.route("/delete/<int:id>")
def delete(id):
    movie = db.session.get(Movie, id)
    db.session.delete(movie)
    db.session.commit()
    return redirect(url_for("home"))

@app.route("/add", methods=["GET", "POST"])
def add():
    form = AddMovieForm()
    if form.validate_on_submit():
        title = form.title.data
        try:
            response = requests.get(
                MOVIE_DB_SEARCH_URL,
                params={"query": title},
                headers=headers
            )
            response.raise_for_status()
            data = response.json().get("results", [])
            return render_template("select.html", options=data)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data: {e}")
            return render_template("add.html", form=form, error="Failed to fetch movies. Please try again.")
    
    return render_template("add.html", form=form)

@app.route("/add_movie/<int:movie_id>")
def add_movie(movie_id):
    # Fetch complete movie details from TMDB API
    MOVIE_DB_INFO_URL = f"https://api.themoviedb.org/3/movie/{movie_id}"
    
    try:
        response = requests.get(MOVIE_DB_INFO_URL, headers=headers)
        response.raise_for_status()
        movie_data = response.json()
        
        # Create new movie entry
        new_movie = Movie(
            title=movie_data["title"],
            year=int(movie_data["release_date"][:4]) if movie_data.get("release_date") else None,
            description=movie_data["overview"],
            rating=float(movie_data["vote_average"]),
            ranking=1,
            review="Your Review Here",
            img_url=f"https://image.tmdb.org/t/p/w500{movie_data['poster_path']}" if movie_data.get('poster_path') else None
        )

        ranking = db.session.query(Movie).count() + 1
        new_movie.ranking = ranking
        
        db.session.add(new_movie)
        db.session.commit()
        
        # Redirect to the edit page for the new movie
        return redirect(url_for('update', id=new_movie.id))
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching movie details: {e}")
        return redirect(url_for('add'))


if __name__ == '__main__':
    app.run(debug=True)

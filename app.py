#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import dateutil.parser
import babel
from flask import Flask, render_template, request, flash, redirect, url_for, abort
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging
from datetime import datetime
from logging import Formatter, FileHandler
import sys
from forms import *
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
Migrate(app, db)
# TODO: connect to a local postgresql database

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#


class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    genres = db.Column(db.String())
    website_link = db.Column(db.String())
    seeking_talent = db.Column(db.Boolean, nullable=False)
    seeking_description = db.Column(db.String())
    shows = db.relationship("Show", backref="venue_shows", lazy=True)


class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120))
    genres = db.Column(db.String(120), nullable=False)
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website_link = db.Column(db.String())
    seeking_venue = db.Column(db.Boolean, nullable=False)
    seeking_description = db.Column(db.String())
    shows = db.relationship("Show", backref="artist_shows", lazy=True)


class Show(db.Model):
    __tablename__ = 'Show'

    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime(), nullable=False)
    venue_id = db.Column(db.Integer, db.ForeignKey("Venue.id"), nullable=False)
    artist_id = db.Column(db.Integer, db.ForeignKey(
        "Artist.id"), nullable=False)

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#


def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(str(value))
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format, locale='en')


app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#


@app.route('/')
def index():
    return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
    data = []
    try:
        locations = Venue.query.with_entities(
            Venue.city, Venue.state).group_by(Venue.city, Venue.state).all()
        for location in locations:
            city = location[0]
            state = location[1]
            venues = Venue.query\
                .filter(Venue.city == city, Venue.state == state)\
                .with_entities(Venue.id, Venue.name, db.func.count(db.case((Show.start_time > datetime.now(), 1))).label("num_upcoming_shows"))\
                .outerjoin(Show)\
                .group_by(Venue.id).all()
            venue_objects = [venue._asdict() for venue in venues]
            data_object = {
                "city": city,
                "state": state,
                "venues": venue_objects
            }
            data.append(data_object)
    except:
        flash("An error occurred")
        abort(500)
    return render_template('pages/venues.html', areas=data)


@app.route('/venues/search', methods=['POST'])
def search_venues():
    # TODO: implement search on artists with partial string search. Ensure it is case-insensitive.
    # seach for Hop should return "The Musical Hop".
    # search for "Music" should return "The Musical Hop" and "Park Square Live Music & Coffee"
    response = {
        "count": 1,
        "data": [{
            "id": 2,
            "name": "The Dueling Pianos Bar",
            "num_upcoming_shows": 0,
        }]
    }
    return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    data = {}
    try:
        venue = Venue.query.get(venue_id)
        if(venue is None):
            raise ValueError("venue_id does not exist")
        show_query = Show.query.with_entities(
            Show.artist_id,
            Artist.name.label("artist_name"),
            Artist.image_link.label("artist_image_link"),
            Show.start_time,
        ).join(Artist)
        upcoming_shows = show_query.filter(
            Show.start_time > datetime.now(), Show.venue_id == venue_id).all()
        past_shows = show_query.filter(
            Show.start_time < datetime.now(), Show.venue_id == venue_id).all()
        data["id"] = venue.id
        data["name"] = venue.name
        data["genres"] = venue.genres.split(",")
        data["address"] = venue.address
        data["city"] = venue.city
        data["state"] = venue.state
        data["phone"] = venue.phone
        data["website"] = venue.website_link
        data["facebook_link"] = venue.facebook_link
        data["seeking_talent"] = venue.seeking_talent
        data["seeking_description"] = venue.seeking_description
        data["image_link"] = venue.image_link
        data["past_shows"] = [show._asdict() for show in past_shows]
        data["upcoming_shows"] = [show._asdict() for show in upcoming_shows]
        data["past_shows_count"] = len(past_shows)
        data["upcoming_shows_count"] = len(upcoming_shows)
    except ValueError as e:
        flash(f"An error occurred: {e}")
        abort(404)
    except:
        flash("An error occurred")
        abort(500)
    return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------


@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    form = VenueForm()
    error = False
    if form.validate_on_submit():
        try:
            venue = Venue(
                name=form.name.data,
                city=form.city.data,
                state=form.state.data,
                address=form.address.data,
                phone=form.phone.data,
                image_link=form.image_link.data,
                genres=",".join(form.genres.data),
                facebook_link=form.facebook_link.data,
                website_link=form.website_link.data,
                seeking_talent=form.seeking_talent.data,
                seeking_description=form.seeking_description.data
            )
            db.session.add(venue)
            db.session.commit()
            flash('Venue ' + venue.name + ' was successfully listed!')
        except:
            error = True
            db.session.rollback()
            flash('An error occurred. Venue ' +
                  form.name.data + ' could not be listed.')
            print(sys.exc_info())
        finally:
            db.session.close()
        if error:
            abort(500)
    else:
        flash("Some fields failed validation")
        return render_template('forms/new_venue.html', form=form)
    return redirect(url_for("index"))


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    # TODO: Complete this endpoint for taking a venue_id, and using
    # SQLAlchemy ORM to delete a record. Handle cases where the session commit could fail.

    # BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that
    # clicking that button delete it from the db then redirect the user to the homepage
    return None

#  Artists
#  ----------------------------------------------------------------


@app.route('/artists')
def artists():
    data = []
    try:
        artists = Artist.query.with_entities(Artist.id, Artist.name).all()
        data = [artist._asdict() for artist in artists]
    except:
        flash("An error occurred")
        abort(500)
    return render_template('pages/artists.html', artists=data)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    # TODO: implement search on artists with partial string search. Ensure it is case-insensitive.
    # seach for "A" should return "Guns N Petals", "Matt Quevado", and "The Wild Sax Band".
    # search for "band" should return "The Wild Sax Band".
    response = {
        "count": 1,
        "data": [{
            "id": 4,
            "name": "Guns N Petals",
            "num_upcoming_shows": 0,
        }]
    }
    return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    data = {}
    try:
        artist = Artist.query.get(artist_id)
        if(artist is None):
            raise ValueError("artist_id does not exist")
        show_query = Show.query.with_entities(
            Show.venue_id,
            Venue.name.label("venue_name"),
            Venue.image_link.label("venue_image_link"),
            Show.start_time,
        ).join(Venue)
        upcoming_shows = show_query.filter(
            Show.start_time > datetime.now(), Show.artist_id == artist_id).all()
        past_shows = show_query.filter(
            Show.start_time < datetime.now(), Show.artist_id == artist_id).all()
        data["id"] = artist.id
        data["name"] = artist.name
        data["genres"] = artist.genres.split(",")
        data["city"] = artist.city
        data["state"] = artist.state
        data["phone"] = artist.phone
        data["website"] = artist.website_link
        data["facebook_link"] = artist.facebook_link
        data["seeking_venue"] = artist.seeking_venue
        data["seeking_description"] = artist.seeking_description
        data["image_link"] = artist.image_link
        data["past_shows"] = [show._asdict() for show in past_shows]
        data["upcoming_shows"] = [show._asdict() for show in upcoming_shows]
        data["past_shows_count"] = len(past_shows)
        data["upcoming_shows_count"] = len(upcoming_shows)
    except ValueError as e:
        flash(f"An error occurred: {e}")
        abort(404)
    except:
        flash("An error occurred")
        abort(500)
    return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------


@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    form = ArtistForm()
    artist = Artist.query.get(artist_id)
    artist.genres = artist.genres.split(",")
    form.populate_obj(artist)
    # artist = {
    #     "id": 4,
    #     "name": "Guns N Petals",
    #     "genres": ["Rock n Roll"],
    #     "city": "San Francisco",
    #     "state": "CA",
    #     "phone": "326-123-5000",
    #     "website": "https://www.gunsnpetalsband.com",
    #     "facebook_link": "https://www.facebook.com/GunsNPetals",
    #     "seeking_venue": True,
    #     "seeking_description": "Looking for shows to perform at in the San Francisco Bay Area!",
    #     "image_link": "https://images.unsplash.com/photo-1549213783-8284d0336c4f?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=300&q=80"
    # }
    # TODO: populate form with fields from artist with ID <artist_id>
    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    # TODO: take values from the form submitted, and update existing
    # artist record with ID <artist_id> using the new attributes

    return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    form = VenueForm()
    venue = {
        "id": 1,
        "name": "The Musical Hop",
        "genres": ["Jazz", "Reggae", "Swing", "Classical", "Folk"],
        "address": "1015 Folsom Street",
        "city": "San Francisco",
        "state": "CA",
        "phone": "123-123-1234",
        "website": "https://www.themusicalhop.com",
        "facebook_link": "https://www.facebook.com/TheMusicalHop",
        "seeking_talent": True,
        "seeking_description": "We are on the lookout for a local artist to play every two weeks. Please call us.",
        "image_link": "https://images.unsplash.com/photo-1543900694-133f37abaaa5?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=400&q=60"
    }
    # TODO: populate form with values from venue with ID <venue_id>
    return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    # TODO: take values from the form submitted, and update existing
    # venue record with ID <venue_id> using the new attributes
    return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------


@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    form = ArtistForm()
    error = False
    if form.validate_on_submit():
        try:
            artist = Artist(
                name=form.name.data,
                city=form.city.data,
                state=form.state.data,
                phone=form.phone.data,
                genres=",".join(form.genres.data),
                image_link=form.image_link.data,
                facebook_link=form.facebook_link.data,
                website_link=form.website_link.data,
                seeking_venue=form.seeking_venue.data,
                seeking_description=form.seeking_description.data,
            )
            db.session.add(artist)
            db.session.commit()
            flash('Artist ' + artist.name +
                  ' was successfully listed!')
        except:
            error = True
            db.session.rollback()
        finally:
            db.session.close()
        if error:
            abort(500)
    else:
        flash("Some fields failed validation")
        return render_template('forms/new_artist.html', form=form)
    return redirect(url_for("index"))


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
    data = []
    try:
        shows = Show.query.with_entities(
            Show.venue_id,
            Venue.name.label("venue_name"),
            Show.artist_id,
            Artist.name.label("artist_name"),
            Artist.image_link.label("artist_image_link"),
            Show.start_time
        ).join(Artist).join(Venue).all()
        data = [show._asdict() for show in shows]
    except:
        flash("An error occurred")
        abort(500)
    return render_template('pages/shows.html', shows=data)


@app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    error = False
    form = ShowForm()
    if form.validate_on_submit():
        try:
            show = Show(
                start_time=form.start_time.data,
                artist_id=form.artist_id.data,
                venue_id=form.venue_id.data
            )
            db.session.add(show)
            db.session.commit()
            flash('Show was successfully listed!')
        except:
            error = True
            db.session.rollback()
            flash('An error occurred. Show could not be listed.')
        finally:
            db.session.close()
        if error:
            abort(500)
    else:
        flash("Some fields failed validation")
        return render_template('forms/new_show.html', form=form)
    return redirect(url_for("index"))


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run("0.0.0.0", port=3000)

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''

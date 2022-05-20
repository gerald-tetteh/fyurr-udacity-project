#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import dateutil.parser
import babel
from flask import jsonify, render_template, request, flash, redirect, url_for, abort
import logging
from datetime import datetime, timedelta
from logging import Formatter, FileHandler
import sys
from forms import *
from models import *

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
    venues = Venue.query.order_by(db.desc(Venue.id)).limit(10).all()
    artists = Artist.query.order_by(db.desc(Artist.id)).limit(10).all()
    return render_template('pages/home.html', venues=venues, artists=artists)


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
    search_query = Venue.query.with_entities(
        Venue.id, Venue.name,
        db.func.count(db.case((Show.start_time > datetime.now(), 1)))
        .label("num_upcoming_shows"))
    search_term = request.form.get("search_term", "")
    if "," in search_term:
        city, state = [string.strip() for string in search_term.split(",")]
        search_query = search_query.filter(
            Venue.city.ilike(city), Venue.state.ilike(state))
    else:
        search_query = search_query.filter(
            Venue.name.ilike(f"%{search_term}%"))
    venues = search_query.outerjoin(Show).group_by(Venue.id).all()
    response = {
        "count": len(venues),
        "data": [venue._asdict() for venue in venues]
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


@app.route('/venues/<int:venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    error = False
    try:
        venue = Venue.query.get(venue_id)
        if(venue is None):
            flash(f"Venue does not exist: {venue_id}")
            abort(404)
        db.session.delete(venue)
        db.session.commit()
        flash(f"Successfully delete venue: {venue_id}")
    except:
        error = True
        db.session.rollback()
    finally:
        db.session.close()
    if error:
        flash(f"Could not delete venue: {venue_id}")
        abort(500)
    return jsonify({"done": True})

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
    search_query = Artist.query.with_entities(
        Artist.id, Artist.name,
        db.func.count(db.case((Show.start_time > datetime.now(), 1)))
        .label("num_upcoming_shows"))
    search_term = request.form.get("search_term", "")
    if "," in search_term:
        city, state = [string.strip() for string in search_term.split(",")]
        search_query = search_query.filter(
            Artist.city.ilike(city), Artist.state.ilike(state))
    else:
        search_query = search_query.filter(
            Artist.name.ilike(f"%{search_term}%"))
    artists = search_query.outerjoin(Show).group_by(Artist.id).all()
    response = {
        "count": len(artists),
        "data": [artist._asdict() for artist in artists]
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
    artist = Artist.query.get(artist_id)
    if (artist is None):
        flash(f"Artist does not exist: {artist_id}")
        abort(404)
    artist.genres = artist.genres.split(",")
    form = ArtistForm(obj=artist)
    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    form = ArtistForm()
    error = False
    if form.validate_on_submit():
        try:
            artist = Artist.query.get(artist_id)
            form.populate_obj(artist)
            artist.genres = ",".join(artist.genres)
            db.session.commit()
        except:
            error = True
            db.session.rollback()
        finally:
            db.session.close()
    else:
        flash("Some fields are not valid")
        return redirect(url_for("edit_artist", artist_id=artist_id))
    if error:
        flash(f"Could not edit artist: {artist_id}")
        abort(500)
    flash(f"Successfully edited Artist: {form.name.data}")
    return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    venue = Venue.query.get(venue_id)
    if (venue is None):
        flash(f"Venue does not exist: {venue_id}")
        abort(404)
    venue.genres = venue.genres.split(",")
    form = VenueForm(obj=venue)
    return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    form = VenueForm()
    error = False
    if form.validate_on_submit():
        try:
            venue = Venue.query.get(venue_id)
            form.populate_obj(venue)
            venue.genres = ",".join(venue.genres)
            db.session.commit()
        except:
            error = True
            db.session.rollback()
        finally:
            db.session.close()
    else:
        flash("Some fields are not valid")
        print(form.errors)
        return redirect(url_for("edit_venue", venue_id=venue_id))
    if error:
        flash(f"Could not edit venue: {venue_id}")
        abort(500)
    flash(f"Successfully edited Venue: {form.name.data}")
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


@app.route('/artists/<int:artist_id>', methods=['DELETE'])
def delete_artist(artist_id):
    error = False
    try:
        artist = Artist.query.get(artist_id)
        if(artist is None):
            flash(f"Artist does not exist: {artist_id}")
            abort(404)
        db.session.delete(artist)
        db.session.commit()
        flash(f"Successfully delete artist: {artist_id}")
    except:
        error = True
        db.session.rollback()
    finally:
        db.session.close()
    if error:
        flash(f"Could not delete artist: {artist_id}")
        abort(500)
    return jsonify({"done": True})


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


@app.route("/shows/search", methods=['GET', 'POST'])
def search_shows():
    shows = []
    date_query = None
    if(request.method == "POST"):
        try:
            search_term = request.form.get("search_term", "")
            if("/" in search_term):
                [day, month, year] = [int(string.strip())
                                      for string in search_term.split("/")]
                date = datetime(year, month, day)
                next_date = date + timedelta(days=1)
                date_query = db.and_(
                    Show.start_time >= date,
                    Show.start_time < next_date
                )
            shows = Show.query\
                .with_entities(
                    Show.artist_id,
                    Show.venue_id,
                    Artist.image_link.label("artist_image_link"),
                    Artist.name.label("artist_name"),
                    Venue.name.label("venue_name"),
                    Show.start_time
                )\
                .join(Artist)\
                .join(Venue)\
                .filter(db.or_(
                    Artist.name.ilike(f"%{search_term}%"),
                    Venue.name.ilike(f"%{search_term}%"),
                    date_query
                )).all()
            shows = [show._asdict() for show in shows]
        except:
            flash("An error ocurred")
            abort(500)
    return render_template("pages/show.html", shows=shows)


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

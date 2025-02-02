# app/routes/station_routes.py

from flask import request
from flask_restx import Namespace, Resource, fields
from app.models.station import Station
from app.extensions import db
from math import radians, sin, cos, sqrt, atan2


api = Namespace('stations', description='Station related operations')

# Serializer models
station_model = api.model('Station', {
    'id': fields.Integer(readOnly=True, description='Unique identifier of the station'),
    'name_en': fields.String(required=True, description='Station name in English'),
    'name_ar': fields.String(required=True, description='Station name in Arabic'),
    'code': fields.String(description='Station code'),
    'location_lat': fields.Float(description='Latitude of the station'),
    'location_long': fields.Float(description='Longitude of the station'),
})

@api.route('/')
class StationList(Resource):
    @api.doc(security='apikey')
    @api.marshal_list_with(station_model)
    def get(self):
        """List all stations"""
        # Check for token in the header
        # token = request.headers.get('Authorization')
        # if not token:
        #     api.abort(401, 'Token missing')

        # For testing purposes, we accept any token
        # In a real application, you'd validate the token here

        stations = Station.query.all()
        return stations

    # @api.doc(security='apikey')
    @api.expect(station_model)
    @api.marshal_with(station_model, code=201)
    def post(self):
        """Create a new station"""
        # Check for token in the header
        # token = request.headers.get('Authorization')
        # if not token:
        #     api.abort(401, 'Token missing')

        # For testing purposes, we accept any token
        # In a real application, you'd validate the token and check permissions

        data = api.payload
        new_station = Station(
            name_en=data['name_en'],
            name_ar=data['name_ar'],
            code=data.get('code'),
            location_lat=data.get('location_lat'),
            location_long=data.get('location_long'),
        )
        db.session.add(new_station)
        db.session.commit()
        return new_station, 201

@api.route('/<int:id>')
@api.param('id', 'The station identifier')
class StationResource(Resource):
    # @api.doc(security='apikey')
    @api.marshal_with(station_model)
    def get(self, id):
        """Get a station by ID"""
        # Check for token in the header
        # token = request.headers.get('Authorization')
        # if not token:
        #     api.abort(401, 'Token missing')

        station = Station.query.get_or_404(id)
        return station

    # @api.doc(security='apikey')
    @api.expect(station_model)
    @api.marshal_with(station_model)
    def put(self, id):
        """Update a station by ID"""
        # Check for token in the header
        # token = request.headers.get('Authorization')
        # if not token:
        #     api.abort(401, 'Token missing')

        station = Station.query.get_or_404(id)
        data = api.payload

        station.name_en = data.get('name_en', station.name_en)
        station.name_ar = data.get('name_ar', station.name_ar)
        station.code = data.get('code', station.code)
        station.location_lat = data.get('location_lat', station.location_lat)
        station.location_long = data.get('location_long', station.location_long)

        db.session.commit()
        return station

    # @api.doc(security='apikey')
    @api.response(204, 'Station deleted')
    def delete(self, id):
        """Delete a station by ID"""
        # Check for token in the header
        # token = request.headers.get('Authorization')
        # if not token:
        #     api.abort(401, 'Token missing')

        station = Station.query.get_or_404(id)
        db.session.delete(station)
        db.session.commit()
        return '', 204

@api.route('/nearest-five')
class NearestFiveStations(Resource):
    @api.doc(params={
        'lat': 'Latitude of the reference location',
        'lon': 'Longitude of the reference location',
    })
    def get(self):
        """
        Returns the nearest five stations to the given (lat, lon).
        """
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)

        if lat is None or lon is None:
            api.abort(400, "Missing 'lat' or 'lon' query parameter.")

        # Fetch stations that have valid lat/long
        stations = Station.query.filter(
            Station.location_lat.isnot(None),
            Station.location_long.isnot(None)
        ).all()

        # Calculate distance for each station
        stations_with_distance = []
        for station in stations:
            distance_km = haversine(
                lat,
                lon,
                float(station.location_lat),
                float(station.location_long)
            )
            stations_with_distance.append((station, distance_km))

        # Sort by ascending distance
        stations_with_distance.sort(key=lambda x: x[1])

        # Take the first five
        nearest_five = stations_with_distance[:5]

        # Convert to a list of dicts with the info you need
        results = []
        for station, dist in nearest_five:
            results.append({
                'id': station.id,
                'name_en': station.name_en,
                'name_ar': station.name_ar,
                'distance_km': round(dist, 2)
            })

        return results, 200

def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points
    on the Earth (specified in decimal degrees).
    Returns distance in kilometers.
    """
    R = 6371.0  # approximate radius of earth in km
    dLat = radians(lat2 - lat1)
    dLon = radians(lon2 - lon1)
    a = sin(dLat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dLon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c
    return distance
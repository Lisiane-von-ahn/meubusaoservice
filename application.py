from flask import Flask, jsonify, request, make_response
from datetime import timedelta, datetime
from functools import wraps
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.conditions import Attr
from CustomJSONEncoder import CustomJSONEncoder
from util.databaseDefinition import getDatabase
import boto3
from flasgger import Swagger
from flasgger.utils import swag_from
from util.constants import NoDatabaseFound
from util.converter import rowConverter
from databaseMeuBusao import getConnectionCursor

import simplejson as json
import jwt
import sqlite3
from s3methods import s3_api

def getCities():
        print ("Getting Cities")
        try:
            c = getConnectionCursor("postgres")
        except Exception as err:
            print (err)
            return NoDatabaseFound
            
        c.execute("SELECT datname FROM pg_database")
        
        rows = c.fetchall()
        
        cities = []
        
        for row in rows:
            if "_" in row[0] and "pycache" not in row[0]:
                cities.append(row[0])
        
        return cities

app = Flask(__name__)

app.json_encoder = CustomJSONEncoder

app.config['JSON_AS_ASCII'] = False
app.config ['SECRET_KEY'] = "aooeioeriureoireo"

app.config['SWAGGER'] = {
    'title': 'My Bus Service - Meu Busao',
    'uiversion': 3,
    "specs_route": "/apidocs/",
    "components": {
        "schemas": {
            "Color": {
                "type": "string",
                "enum":["black"]
            }
        }
    }
}

template = {
  "swagger": "2.0",
  "cities": {"in": "path","required":"true","name":"city","enum": getCities()},
  "info": {
    "title": "My Bus Service - Meu Busao",
    "description": "API to manage GTFS across different cities",
    "version": "1.0.1"
  },
  "operationId": "getmyData"
}

swagger = Swagger(app,template=template)

def token_required(f):
    @wraps(f)
    def decorated (*args, **kwargs):
        token = request.headers.get("token")

        if not token:
            return jsonify({'message' : 'Token is missing'}), 403
        
        try:
            data = jwt.decode(token, app.config ['SECRET_KEY'])
        except:
            return jsonify({'message' : 'Token is invalid'}), 403
        
        return f(*args, **kwargs)
    return decorated

@app.route('/login')
@swag_from("login.yml")
def login():
    auth = request.headers.get("id")

    print(auth)

    db = "./config.db"

    conn = sqlite3.connect(db)

    c = conn.cursor()

    c.execute("select count(1) from users where identificator = ?", (auth,))

    data = c.fetchall()

    if int(data[0][0]) > 0:
        token = jwt.encode({"user" : auth, "exp" : datetime.utcnow() + timedelta(minutes=30)}, app.config ["SECRET_KEY"])
        return jsonify({"token" : token.decode("UTF-8")})

    return make_response('Could not verify! Login Failed',401, {'Err-Message' : 'Login Failed'})

@app.route('/getCalendar/<string:city>', methods=["GET"])
@swag_from("getCalendar.yml")
@token_required
def getCalendar(city) -> str:
    try:
        c = getConnectionCursor(city)
            
        c.execute("select * from calendar")
        rows = c.fetchall()

        row_headers=[x[0] for x in c.description]
        
        data = rowConverter(rows, row_headers)
        
        c.close()

        return json.dumps(data)

    except Exception as err:
        print(err)
        return jsonify(NoDatabaseFound)

@app.route('/getCalendarDates/<string:city>', methods=["GET"])
@swag_from("getCalendarDates.yml")
@token_required
def getCalendarDates(city) -> str:
    try:
        try:
            c = getConnectionCursor(city)
        except:
            return NoDatabaseFound
            
        c.execute("select * from calendar_dates")
        rows = c.fetchall()

        row_headers=[x[0] for x in c.description]
        
        data = rowConverter(rows, row_headers)
        
        c.close()

        return json.dumps(data)
    except Exception as err:
        return jsonify(NoDatabaseFound)
    
@app.route('/getStopTimeByRouteAndDirectionAndWeekday/<string:city>/<string:weekday>/<string:routeId>',  methods=["GET"])
@swag_from("getStopTimeByRouteAndDirectionAndWeekday.yml")
@token_required
def getStopTimeByRouteAndDirectionAndWeekday(city, weekday, routeId) -> str:
    
    direction = request.args.get("direction")
    
    try:
        try:
            c = getConnectionCursor(city)
        except Exception as err:
            print (err)
            return NoDatabaseFound
            
        c.execute("select distinct a.trip_id,a.route_id,a.trip_headsign,a.service_id,a.shape_id,a.wheelchair_accessible,a.bikes_allowed," +
                        " stop_name, arrival_time, departure_time, s.stop_id,st.stop_sequence" +
                        " from trip a join calendar c on a.service_id = c.service_id" +
                        " join stopstime st on st.trip_id = a.trip_id" +
                        " join stops s on st.stop_id  = s.stop_id" +
                        " where c." + weekday + " = '1' and a.trip_headsign = %s and a.route_id = %s" +
                        " and  to_char(CURRENT_DATE,'yyyyMMdd') <= end_date and to_char(CURRENT_DATE,'yyyyMMdd') >= start_date" +
                        " order by st.stop_sequence, arrival_time", (direction, routeId, ))
        
        rows = c.fetchall()

        row_headers=[x[0] for x in c.description]
        
        data = rowConverter(rows, row_headers)
        
        c.close()

        return json.dumps(data)

    except Exception as err:
        print (err)
        return jsonify(NoDatabaseFound)

@app.route('/getStopTimeByRouteAndDirectionAndWeekdayAndStopId/<string:city>/<string:weekday>/<string:routeId>/<string:stopId>', methods=["GET"])
@swag_from("getStopTimeByRouteAndDirectionAndWeekdayAndStopId.yml")
@token_required
def getStopTimeByRouteAndDirectionAndWeekdayAndStopId(city, weekday, routeId,stopId) -> str:
    
    direction = request.args.get("direction")
    
    try:
        try:
            c = getConnectionCursor(city)
        except:
            return NoDatabaseFound
            
        c.execute("select distinct '0' as trip_id,a.route_id,a.trip_headsign,'0' as service_id,a.shape_id,a.wheelchair_accessible,a.bikes_allowed," +
                        " stop_name, arrival_time, departure_time, s.stop_id,st.stop_sequence" +
                        " from trip a join calendar c on a.service_id = c.service_id" +
                        " join stopstime st on st.trip_id = a.trip_id" +
                        " join stops s on st.stop_id  = s.stop_id" +
                        " where c." + weekday + " = '1' and a.trip_headsign = %s and a.route_id = %s and s.stop_id = %s" +
                        " and  to_char(CURRENT_DATE,'yyyyMMdd') <= end_date and to_char(CURRENT_DATE,'yyyyMMdd') >= start_date" +
                        " order by st.stop_sequence, arrival_time", (direction, routeId, stopId, ))
        
        rows = c.fetchall()

        row_headers=[x[0] for x in c.description]
        
        data = rowConverter(rows, row_headers)
        
        c.close()

        return json.dumps(data)

    except Exception as err:
        return jsonify(NoDatabaseFound)


@app.route('/getStopsByRouteAndDirection/<string:city>/<string:weekday>/<string:routeId>', methods=["GET"])
@swag_from("getStopsByRouteAndDirection.yml")
@token_required
def getStopsByRouteAndDirection(city, weekday, routeId) -> str:
    direction = request.args.get("direction")

    try:
        try:
            c = getConnectionCursor(city)
        except:
            return NoDatabaseFound
            
        c.execute("select distinct s.stop_name,s.stop_id,s.stop_lat,s.stop_lon,s.parent_station, s.location_type,st.stop_sequence, max(a.shape_id) shape_id" +
                        " from trip a join calendar c on a.service_id = c.service_id" +
                        " join stopstime st on st.trip_id = a.trip_id" +
                        " join stops s on st.stop_id  = s.stop_id" +
                        " where c." + weekday + " = '1' and a.trip_headsign = %s and a.route_id = %s" +
                        " and  to_char(CURRENT_DATE,'yyyyMMdd') <= end_date and to_char(CURRENT_DATE,'yyyyMMdd') >= start_date" +
                        " group by s.stop_name,s.stop_id,s.stop_lat,s.stop_lon,s.parent_station, s.location_type,st.stop_sequence" + 
                        " order by st.stop_sequence", (direction, routeId, ))
        
        rows = c.fetchall()

        row_headers=[x[0] for x in c.description]
        
        data = rowConverter(rows, row_headers)
        
        c.close()

        return json.dumps(data)

    except Exception as err:
        return jsonify(NoDatabaseFound)


@app.route('/getStopTimeByRouteAndDirectionAndDate/<string:city>/<string:weekday>/<string:routeId>',  methods=["GET"])
@swag_from("getStopTimeByRouteAndDirectionAndDate.yml")
@token_required
def getStopTimeByRouteAndDirectionAndDate(city, date, routeId) -> str:
    
    direction = request.args.get("direction")
    
    try:
        try:
            c = getConnectionCursor(city)
        except Exception as err:
            print (err)
            return NoDatabaseFound
            
        c.execute("select distinct a.trip_id,a.route_id,a.trip_headsign,a.service_id,a.shape_id,a.wheelchair_accessible,a.bikes_allowed," +
                        " stop_name, arrival_time, departure_time, s.stop_id,st.stop_sequence" +
                        " from trip a join calendar_dates c on a.service_id = c.service_id" +
                        " join stopstime st on st.trip_id = a.trip_id" +
                        " join stops s on st.stop_id  = s.stop_id" +
                        " where datet = '" + date.replace("-","") + "' and a.trip_headsign = %s and a.route_id = %s" +
                        " order by st.stop_sequence, arrival_time", (direction, routeId, ))
        
        rows = c.fetchall()

        row_headers=[x[0] for x in c.description]
        
        data = rowConverter(rows, row_headers)
        
        c.close()

        return json.dumps(data)

    except Exception as err:
        print (err)
        return jsonify(NoDatabaseFound)

@app.route('/getStopTimeByRouteAndDirectionAndDateAndStopId/<string:city>/<string:date>/<string:routeId>/<string:stopId>', methods=["GET"])
@swag_from("getStopTimeByRouteAndDirectionAndDateAndStopId.yml")
@token_required
def getStopTimeByRouteAndDirectionAndDateAndStopId(city, date, routeId,stopId) -> str:
    
    direction = request.args.get("direction")
    
    try:
        try:
            c = getConnectionCursor(city)
        except:
            return NoDatabaseFound
            
        c.execute("select distinct '0' as trip_id,a.route_id,a.trip_headsign,'0' as service_id,a.shape_id,a.wheelchair_accessible,a.bikes_allowed," +
                        " stop_name, arrival_time, departure_time, s.stop_id,st.stop_sequence" +
                        " from trip a join calendar_dates c on a.service_id = c.service_id" +
                        " join stopstime st on st.trip_id = a.trip_id" +
                        " join stops s on st.stop_id  = s.stop_id" +
                        " where datet = '" + date.replace("-","") + "' and a.trip_headsign = %s and a.route_id = %s and s.stop_id = %s" +
                        " order by st.stop_sequence, arrival_time", (direction, routeId, stopId, ))
        
        rows = c.fetchall()

        row_headers=[x[0] for x in c.description]
        
        data = rowConverter(rows, row_headers)
        
        c.close()

        return json.dumps(data)

    except Exception as err:
        return jsonify(NoDatabaseFound)


@app.route('/getStopsByRouteAndDirectionDate/<string:city>/<string:date>/<string:routeId>', methods=["GET"])
@swag_from("getStopsByRouteAndDirectionDate.yml")
@token_required
def getStopsByRouteAndDirectionDate(city, date, routeId) -> str:
    direction = request.args.get("direction")

    try:
        try:
            c = getConnectionCursor(city)
        except:
            return NoDatabaseFound
            
        c.execute("select distinct s.stop_name,s.stop_id,s.stop_lat,s.stop_lon,s.parent_station, s.location_type,st.stop_sequence, max(a.shape_id) shape_id" +
                        " from trip a join calendar_dates c on a.service_id = c.service_id" +
                        " join stopstime st on st.trip_id = a.trip_id" +
                        " join stops s on st.stop_id  = s.stop_id" +
                        " where datet = '" + date.replace("-","") + "' and a.trip_headsign = %s and a.route_id = %s" +
                        " group by s.stop_name,s.stop_id,s.stop_lat,s.stop_lon,s.parent_station, s.location_type,st.stop_sequence" + 
                        " order by st.stop_sequence", (direction, routeId, ))
        
        rows = c.fetchall()

        row_headers=[x[0] for x in c.description]
        
        data = rowConverter(rows, row_headers)
        
        c.close()

        return json.dumps(data)

    except Exception as err:
        return jsonify(NoDatabaseFound)



@app.route('/getRouteByTrip/<string:city>/<string:tripId>', methods=["GET"])
@swag_from("getRoutebyTrip.yml")
@token_required
def getRouteByTrip(city, tripId) -> str:
    try:
        try:
            c = getConnectionCursor(city)
        except:
            return NoDatabaseFound
            
        c.execute("select * from trip where trip_id = %s", (tripId, ))
        
        rows = c.fetchall()

        row_headers=[x[0] for x in c.description]
        
        data = rowConverter(rows, row_headers)
        
        c.close()

        return json.dumps(data)

    except Exception as err:
        return jsonify(NoDatabaseFound)

@app.route('/getDirectionByRoute/<string:city>/<string:routeId>', methods=["GET"])
@swag_from("getDirections.yml")
@token_required
def getDirectionByRoute(city, routeId) -> str:
    try:
        try:
            c = getConnectionCursor(city)
        except:
            return NoDatabaseFound
            
        c.execute("select distinct trip_headsign from trip where route_id = %s", (routeId, ))
        
        rows = c.fetchall()

        row_headers=[x[0] for x in c.description]
        
        data = rowConverter(rows, row_headers)
        
        c.close()

        return json.dumps(data)

    except Exception as err:
        print (err)
        return jsonify(NoDatabaseFound)

@app.route('/getShape/<string:city>', methods=["GET"])
@swag_from("getShape.yml")
@token_required
def getShape(city) -> str:
    try:
        try:
            c = getConnectionCursor(city)
        except:
            return NoDatabaseFound
            
        c.execute("select * from shape")
        rows = c.fetchall()

        row_headers=[x[0] for x in c.description]
        
        data = rowConverter(rows, row_headers)
        
        c.close()

        return json.dumps(data)
    except Exception as err:
        return jsonify(NoDatabaseFound)

@app.route('/getShapeById/<string:city>', methods=["GET"])
@swag_from("getShapeById.yml")
@token_required
def getShapeById(city) -> str:
    try:
        shapeId = request.args.get("shapeId")
        try:
            c = getConnectionCursor(city)
        except:
            return NoDatabaseFound

        print("test")

        c.execute("select shape_pt_lat,shape_pt_lon,shape_pt_sequence from shape where shape_id = %s order by shape_pt_sequence", (shapeId,))
        rows = c.fetchall()

        row_headers=[x[0] for x in c.description]
        
        data = rowConverter(rows, row_headers)
        
        c.close()

        return json.dumps(data)

    except Exception as err:
        print(err)
        return jsonify(NoDatabaseFound)


@app.route('/getShapeByTripId/<string:city>', methods=["GET"])
@swag_from("getShapeByTripId.yml")
@token_required
def getShapeByTripId(city) -> str:
    try:
        tripId = request.args.get("tripId")
        try:
            c = getConnectionCursor(city)
        except:
            return NoDatabaseFound

        sql= "select s.* from shape s inner join trip t where t.shape_id =s.shape_id and t.trip_id = %s order by shape_pt_sequence"

        c.execute(sql, (shapeId,))
        rows = c.fetchall()

        row_headers=[x[0] for x in c.description]
        
        data = rowConverter(rows, row_headers)
        
        c.close()

        return json.dumps(data)

    except Exception as err:
        print(err)
        return jsonify(NoDatabaseFound)


@app.route('/getRoutes/<string:city>', methods=["GET"])
@swag_from("getRoute.yml")
@token_required
def getRoutes(city) -> str:
    try:
        try:
            c = getConnectionCursor(city)
        except Exception as Err:
            print (err)
            return NoDatabaseFound
            
        c.execute("select * from route")
        print ("Executed")
        rows = c.fetchall()
        
        c.close()

        row_headers=[x[0] for x in c.description]
        
        data = rowConverter(rows, row_headers)
        
        return json.dumps(data)
    
    except Exception as err:
        print (err)
        return jsonify(NoDatabaseFound)

@app.route('/getStopsTime/<string:city>')
@swag_from("getStopsTime.yml")
@token_required
def getStopsTime(city) -> str:
    c = getConnectionCursor(city)

    c.execute("select t.trip_id, arrival_time, departure_time,s.stop_id, stop_name, stop_lat, stop_lon, parent_station, trip_headsign,t.service_id " +
               " from STOPSTIME s inner join STOPS s2" + 
               " on s.stop_id = s2.stop_id" + 
               " inner join trip t" + 
               " on s.trip_id = t.trip_id")
    rows = c.fetchall()

    row_headers=[x[0] for x in c.description]
    
    data = rowConverter(rows, row_headers)
    
    c.close()

    return json.dumps(data)

@app.route('/getRouteByStopId/<string:city>/<string:stopId>')
@swag_from("getRoutebyStopId.yml")
@token_required
def getRouteByStopId(city, stopId) -> str:
    c = getConnectionCursor(city)

    c.execute("select route_id,route_long_name, route_short_name, route_color, route_text_color " +
               " from route" + 
               " where route_id in (select route_id from stopstime s inner join trip s2 on s.trip_id = s2.trip_id where stop_id = %s)",(stopId,))
    
    rows = c.fetchall()

    row_headers=[x[0] for x in c.description]
    
    data = rowConverter(rows, row_headers)
    
    c.close()

    return json.dumps(data)

#Get Stops from DB
@swag_from("getStops.yml")
@app.route('/getStops/<string:city>', methods=["GET"])
def getStops(city) -> str:
    c = getConnectionCursor(city)
    c.execute("SELECT * FROM stops ");

    rows = c.fetchall()

    row_headers=[x[0] for x in c.description]
    
    data = rowConverter(rows, row_headers)
    
    c.close()

    return json.dumps(data)

#Get Trips from DB
@swag_from("getTrips.yml")
@app.route('/getTrips/<string:city>/<string:route>', methods=["GET"])
def getTrips(city,route) -> str:
    c = getConnectionCursor(city)
    c.execute("SELECT * FROM trips where route_id = %s",route);

    rows = c.fetchall()

    row_headers=[x[0] for x in c.description]
    
    data = rowConverter(rows, row_headers)
    
    c.close()

    return json.dumps(data)

#Get Trips from DB
@swag_from("getStopsByTrip.yml")
@app.route('/getStopsByTrip/<string:city>/<string:trip>', methods=["GET"])
def getStopsByTrip(city,trip) -> str:
    c = getConnectionCursor(city)
    c.execute("select distinct stop_name , stop_lat, stop_lon,stop_sequence from stopstime s ,stops s2 where s.stop_id = s2.stop_id and trip_id = %s order by stop_sequence",(trip,));

    rows = c.fetchall()

    row_headers=[x[0] for x in c.description]
    
    data = rowConverter(rows, row_headers)
    
    c.close()

    return json.dumps(data)

if __name__ == "__main__":
    app.run(port=5000, debug=True)
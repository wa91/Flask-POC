
import pandas,sqlalchemy,ast,datetime,sys
from flask import Flask
from flask_restful import Resource, Api, reqparse

app = Flask(__name__)
api = Api(app)

try:
	user=sys.argv[1]
	password=sys.argv[2]
	database=sys.argv[3]
except Exception as e: 
	print(e)
	print('Please pass Postrges credentials as arguements to the script e.g. sandwich_orders.py USERNAME PASSWORD DATABASE')
	quit()
	
class Orders(Resource):
#Only POST enabled
	def post(self):
		#parse API input
		parser = reqparse.RequestParser()  
		parser.add_argument('name', required=True)
		parsed = parser.parse_args() 
		
		start_time = datetime.datetime.now()
		
		# connect to PG
		engine = sqlalchemy.create_engine('postgresql://'+user+':'+password+'@localhost:5432/'+database+'',echo=True)
		
		#create the table if it's not there - just incase
		connection = engine.connect()
		my_query = 'create table if not exists sandwich_schedule (sequence_no serial,sched_time time,task text,recipient text,order_time time)'
		connection.execute(my_query)
		
		# new orders cancel any future breaks
		connection = engine.connect()
		my_query = 'delete from sandwich_schedule where task = \'Take a break\' and sched_time> now()::time'
		connection.execute(my_query)
		
		#create the schedule time
		rows = pandas.read_sql("select count(1)as cnt from sandwich_schedule", con=engine)
		if rows.cnt[0]==0:
			sched_time=start_time + datetime.timedelta(seconds=60)
		else:
			#make the next sandwich only after previous one has been served
			old_sched_time = pandas.read_sql("select sched_time from sandwich_schedule where task='Serve sandwich' order by sequence_no desc limit 1", con=engine)
			if start_time.time()<old_sched_time.sched_time[0]:
				sched_time = datetime.datetime.combine(datetime.date.today(),old_sched_time.sched_time[0]) + datetime.timedelta(seconds=60)
			else:
				sched_time=start_time + datetime.timedelta(seconds=60)
		
		# create dataframes
		current_data = pandas.DataFrame({
			'sched_time': [str(sched_time)],
			'order_time': [str(start_time)],
			'task': ["Make sandwich"],
			'recipient': parsed['name']
		})
		future_data = pandas.DataFrame({
			'sched_time': [str(sched_time + datetime.timedelta(seconds=150))],
			'task': ["Serve sandwich"],
			'recipient': parsed['name']
		})
		break_data = pandas.DataFrame({
			'sched_time': [str(sched_time + datetime.timedelta(seconds=150)+datetime.timedelta(seconds=60))],
			'task': ["Take a break"]
		})
		
		df= current_data.append(future_data, ignore_index=True).append(break_data, ignore_index=True)
		
		# upload results
		df.to_sql('sandwich_schedule', engine, if_exists='append', index=False)

		return {'data': df.to_dict()}, 200 
		
	
api.add_resource(Orders, '/orders') 


if __name__ == '__main__':
	app.run()  # run our Flask app
from SimpleXMLRPCServer import SimpleXMLRPCServer
from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler
import serial
import param_vars
import sys
from time import sleep

ser_x80 = serial.Serial('/dev/tty0', param_vars.baud_rate)
ser_x81 = serial.Serial('/dev/tty1', param_vars.baud_rate)

start_const = 30000
k_const = 30000

class RequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ('/RPC2',)

# Create server
server = SimpleXMLRPCServer(("localhost", 8000),
                            requestHandler=RequestHandler, logRequests = False, 										 allow_none = True)
   # logRequests = False suppresses all output from the server about date and host location.
   
server.register_introspection_functions()
# Functions such as system.listMethods()


################
def drive_motor(board_num, motor, speed):

	board_num = 128
	motor=1
	speed=30000
	
	if (board_num == 0x80):
		ser = ser_x80
	else:
		ser = ser_x81
			
	if ((board_num > 0x87) or (board_num < 0x80)):
		print "Roboclaw board number is out of the scope of possible addresses."
		return param_vars.e_code
	if ((motor != 0) and (motor != 1)):
		print "Please select motor 0 or 1. Yes, I know the boards say 1 and 2. Yes, I know that doesn't make any sense."
		return param_vars.e_code
		
	command = (35 - param_vars.motor_min + motor)  # In case I decide to go with a 1-2 schema.

	speed_byte3 = speed & 0xff  #Least significant bit
	speed = speed >> 8
	speed_byte2 = speed & 0xff
	speed = speed >> 8
	speed_byte1 = speed & 0xff
	speed = speed >> 8
	speed_byte0 = speed & 0xff  # Most significant bit

	checksum = (board_num + command + speed_byte0 + speed_byte1 + speed_byte2 + speed_byte3) & 0x7f

	cmdList = [board_num, command, speed_byte0, speed_byte1, speed_byte2, speed_byte3, checksum]
	# Written MSB to LSB, per the spec sheet. 

	for i in range(len(cmdList)):
		ser.write(chr(cmdList[i]))
		#print cmdList[i]
	return 0;
		
server.register_function(drive_motor, 'drive_motor')
################

def read_encoder(board_num, motor):
	if (board_num == 0x80):
		ser = ser_x80
	else:
		ser = ser_x81
		
	if ((board_num > 0x87) or (board_num < 0x80)):
		print "Roboclaw board number is out of the scope of possible addresses."
		return param_vars.e_code
	if ((motor != 0) and (motor != 1)):
		print "Please select motor 0 or 1. Yes, I know the boards say 1 and 2. Yes, I know that doesn't make any sense."
		return param_vars.e_code

	command = (30 - param_vars.motor_min + motor)  # In case I decide to go with a 1-2 schema.
	
	data = [] # Declared before doing the serial just in case it would mess up timing otherwise.
	ser.write(chr(board_num))  # Write a command to read motor speed, 32 bit resolution. 
	ser.write(chr(command))	   # See roboclaw documentation for further detail

	#Since the serial data is kind of touchy, we NEED to implement a mutex flag for accessing the roboc1law: otherwise, our data will get corrupted and we won't be able to command the motors as we need to.

	for i in range(6):
		data.append(ser.read())

	for i in range(len(data)):
		print ord(data[i])

	speed = (data[0].encode("hex")) + (data[1].encode("hex")) + (data[2].encode("hex")) + (data[3].encode("hex"))
	#print speed ## Hex value
	speed = int(speed, 16)

	if ((ord(data[4]) == 1) and (speed != 0)):
		speed = ~(0xffffffff - speed) + 1
	# print speed #Signed ticks/125th seconde value
	rotations_per_second = float(speed) * 125 / 8192 # *125/8192 --> resolution in 125ths of a second, and then (apparently) 8192 ticks per rotation.
	return rotations_per_second
	
server.register_function(read_encoder, 'read_encoder')

#######################

def stop():
	stop_1 = [0x80, 35, 0, 0, 0, 0, 0x23]
	stop_2 = [0x80, 36, 0, 0, 0, 0, 0x24]
	stop_3 = [0x81, 35, 0, 0, 0, 0, 0x24]
	stop_4 = [0x81, 36, 0, 0, 0, 0, 0x25]
	ser_x80.write(chr(stop_1))	
	ser_x80.write(chr(stop_2))	
	ser_x81.write(chr(stop_3))	
	ser_x81.write(chr(stop_4))	
	return 0
	
server.register_function(stop, 'stop')

#######################

def p_control(s_command1, s_command2, s_command3, rps_d1, rps_d2, rps_d3, k1, k2, k3):
	start_time = time.time()
	change_speed(0,1,0)
	rotations_per_second1 = read_speed(ser_x80, 1) 	
	rotations_per_second2 = read_speed(ser_x80, 2)
	rotations_per_second3 = read_speed(ser_x81, 3)
	print rotations_per_second1

	
	diff1 = abs(rps_d1 - rotations_per_second1)
	diff2 = abs(rps_d2 - rotations_per_second2)
	diff3 = abs(rps_d3 - rotations_per_second3)
	
	if (diff1 > diff2 and diff1 > diff3):
		# Change speed 1
		change_speed(ser_x80, 1, s_command1)
		if (diff2 > diff3):
			# Change speed 2
			# Change speed 3
			change_speed(ser_x80, 2, s_command2)
			change_speed(ser_x81, 3, s_command3)
		else:
			#Change speed 3
			#Change speed 2
			change_speed(ser_x81, 3, s_command3)
			change_speed(ser_x80, 2, s_command2)
	elif (diff2 > diff3 and diff2 > diff1):
		#Change speed 2
		change_speed(ser_x80, 2, s_command2)
		if (diff1 > diff3):
			#change speed 1
			#change speed 3
			change_speed(ser_x80, 1, s_command1)
			change_speed(ser_x81, 3, s_command3)
		else:
			#change speed 3
			#change speed 1
			change_speed(ser_x81, 3, s_command3)
			change_speed(ser_x80, 1, s_command1)
	elif (diff3 > diff1 and diff3 > diff2):
		#Change speed 3
		change_speed(ser_x81, 3, s_command3)
		if (diff1 > diff2):
			#Change speed 1
			#Change speed 2
			change_speed(ser_x80, 1, s_command1)
			change_speed(ser_x80, 2, s_command2)
		else:
			#Change speed 2
			#Change speed 1
			change_speed(ser_x80, 2, s_command2)
			change_speed(ser_x80, 1, s_command1)
	
	count = 0
	mdiff_1 = abs(float(int(rps_d1)) * 125/8192)
	mdiff_2 = abs(float(int(rps_d2)) * 125/8192)
	mdiff_3 = abs(float(int(rps_d3)) * 125/8192)  #Maximum differences between speed desired and actual speed
	while((count < 3) and (abs(diff1) > mdiff_1) and (abs(diff2) > mdiff_2) and (abs(diff3) > mdiff3)):
		count = count + 1
		time.sleep(0.03)  #Kind of arbitrary
		rotations_per_second1 = read_speed(ser_x80, 1) 	
		rotations_per_second2 = read_speed(ser_x80, 2)
		rotations_per_second3 = read_speed(ser_x81, 3)
	
		diff1 = rps_d1 - rotations_per_second1
		diff2 = rps_d2 - rotations_per_second2
		diff3 = rps_d3 - rotations_per_second3  # Differences for the proportional loop
		
		s_command1 = s_command1 + k1 * diff1
		s_command2 = s_command2 + k2 * diff2
		s_command3 = s_command3 + k3 * diff3
		
		change_speed(ser_x80, 1, s_command1)
		change_speed(ser_x80, 2, s_command2)
		change_speed(ser_x81, 3, s_command3)
	stop_time = time.time()
	time_elapsed = stop_time - start_time
	return time_elapsed
		
			
def change_speed(serial, motor_num, speed):
	if (motor_num == 1):
		board_num = 0x80
		command = 35
	elif (motor_num == 2):
		board_num = 0x80
		command = 36
	elif (motor_num == 3):
		board_num = 0x81
		command = 36
	else:
		print "Not a possibility."
		
	speed_byte3 = speed & 0xff  #Least significant bit
	speed = speed >> 8
	speed_byte2 = speed & 0xff
	speed = speed >> 8
	speed_byte1 = speed & 0xff
	speed = speed >> 8
	speed_byte0 = speed & 0xff  # Most significant bit

	checksum = (board_num + command + speed_byte0 + speed_byte1 + speed_byte2 + speed_byte3) & 0x7f
	cmdList = [board_num, command, speed_byte0, speed_byte1, speed_byte2, speed_byte3, checksum]
	for i in range(len(cmdList)):
		serial.write(chr(cmdList[i]))
#		print cmdList[i]
	return 0;


def read_speed(serial, motor_num):
	if (motor_num == 1):
		board_num = 0x80
		command = 30
	elif (motor_num == 2):
		board_num = 0x80
		command = 31
	elif (motor_num == 3):
		board_num = 0x81
		command = 31
	data = []
	serial.write(chr(motor_num))
	serial.write(chr(command)) # Read motor 1 on board 0x80
	for i in range(6):
		data.append(serial.read())
		
	speed = (data[0].encode("hex")) + (data[1].encode("hex")) + (data[2].encode("hex")) + (data[3].encode("hex"))
	speed = int(speed, 16)
	if ((ord(data[4]) == 1) and (speed != 0)):
		speed = ~(0xffffffff - speed) + 1
	rotations_per_second = float(speed) * 125 / 8192 	
	return rotations_per_second
	
server.register_function(p_control)

###################################

def spin(time):
	time_passed = p_control(start_const, start_const, start_const, 1, 1, 1, k_const, k_const, k_const)
	time.sleep(time - time_passed)
	stop()
	return 0
	
server.register_function(spin)

###################################

def square(side_length):  # In feet
	sleep_time = (side_length * 0.3048) / 0.15 ## Assuming driving 0.15 m/s
	time_passed = p_control(start_const * 2, -1*start_const, -1*start_const, 1.1423, -0.57, -0.57, k_const, k_const, k_const)  # 0.15 m/s in X
	time.sleep(sleep_time - time_passed)
	time_passed = p_control(0, start_const*1.5, start_const*-1.5, 0, 0.98, -0.98, k_const, k_const, k_const)  # 0.15 m/s in X
	time.sleep(sleep_time - time_passed)
	time_passed = p_control(start_const * -2, start_const, start_const, -1.1423, 0.57, 0.57, k_const, k_const, k_const)  # 0.15 m/s in X
	time.sleep(sleep_time - time_passed)
	time_passed = p_control(0, start_const*-1.5, start_const*1.5, 0, -0.98, 0.98, k_const, k_const, k_const)  # 0.15 m/s in X
	time.sleep(sleep_time - time_passed)
	stop()
	return 0

server.register_function(square)

###################################

def drive_forward(distance):  ## at 15 cm/sec
	time = distance * 0.3048 / 0.15
	time_passed = p_control(2*start_const, -1 * start_const, -1 *start_const, 1.14, -0.57, -0.57, k_const, k_const, k_const)
	time.sleep(time - time_passed)
	stop()

server.register_function(drive_forward)

##################################

def rotate_one_sixth(): ## Left

	time_final = 1 # Designed for a rotation of 1/6th circle/sec
	time_p = p_control(start_const, start_const, start_const, 0.5941, 0.5941, 0.5941, k_const, k_const, k_const)  ## Primed for 20 degrees/sec rotation
	time.sleep (time_final - time_p)
	return 0
	
##################################

def rotate_degrees(degrees):
	if (degrees > 0):
		time_final = degrees/20
		time_p = p_control(start_const / 2, start_const /2, start_const / 2, 0.1485, 0.1485, 0.1485, k_const, k_const, k_const)  ## Primed for 20 degrees/sec rotation
		time.sleep (time_final - time_p)
		stop()
	else:
		time_final = degrees / -20
		time_p = p_control(start_const / -2, start_const /-2, start_const / -2, -0.1485, -0.1485, -0.1485, k_const, k_const, k_const)
		time.sleep (time_final - time_p)
		stop()

server.register_function(rotate_degrees)

###################################

# Run the server's main loop
server.serve_forever()

import sys
import serial

board_num = sys.argv[1]
motor = sys.argv[2]
speed = sys.argv[3]


def run_drive(board_num, motor, speed):
	import sys
	import serial
	import param_vars
	# Command arguments: Board number (0x80, 0x81...), motor number (0 or 1) and speed(2's complement signed integer)

	if (int(board_num,0) == 0x80):
		try: 
			ser = serial.Serial(param_vars.port_80, param_vars.baud_rate)
		except:
			print "The serial port " + param_vars.port_80 + " is not available."
	else:
		try:
			ser = serial.Serial(param_vars.port_81, param_vars.baud_rate)
		except:
			print "The serial port " + param_var.port_81 + " is not available."

	motor_min = 0
	motor_max = 1 # These are the two acceptable values for motor enumerated values. 
	e_code = -999 # Error code

	try:
		board_num = int(board_num, 0)
	except:
		print "Invalid address format: Must be a number"
		exit(e_code)
	try:
		motor = int(motor, 0)
	except:
		print "Motor must be either motor 0 or 1. Or possibly one or two..."
		exit(e_code)
	try:
		speed = int(speed, 0)
	except:
		print "Motor speed must be an integer."
		exit(e_code)

	#print board_num

	if ((board_num > 0x87) or (board_num < 0x80)):
		print "Roboclaw board number is out of the scope of possible addresses."
		exit(e_code)
	if ((motor != 0) and (motor != 1)):
		print "Please select motor 0 or 1. Yes, I know the boards say 1 and 2. Yes, I know that doesn't make any sense."
		exit(e_code)

	command = (35 - motor_min + motor)  # In case I decide to go with a 1-2 schema.

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

run_drive(board_num, motor, speed)

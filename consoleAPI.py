#*********************************************************************
#
#   MODULE NAME:
#       consoleAPI.py - ConsoleAPI Interfacing Class
#
#   DESCRIPTION:
#       Class to provide functionaility for interacting with the Raspberry
#		pi pico through the console
#
#   Copyright 2024 by Nate Lenze
#*********************************************************************

#---------------------------------------------------------------------
#                              IMPORTS
#--------------------------------------------------------------------- 
import serial
import time

#---------------------------------------------------------------------
#                          CLASSES
#---------------------------------------------------------------------
class consoleAPI:
	__uart_conn = None
	
	# ==================================
    # constructor() 
    # ==================================	
	def __init__(self):
		self.__uart_conn = serial.Serial(
							port='/dev/ttyS0',
							baudrate = 115200,
							parity=serial.PARITY_NONE,
							stopbits=serial.STOPBITS_ONE,
							bytesize=serial.EIGHTBITS,
							timeout=1
							)
	# ==================================
    # writeLine() 
    # ==================================	
	def writeLine(self, input_str: str , auto_return_carrige: bool = True  ) -> 'bool':
		# ------------------------------------
		# convert string to hex & append carrige
		# return if expected
		# ------------------------------------
		hex_list = self.__str_to_hex_list( str )

		if( auto_return_carrige ):
			hex_list.append( ord('\r') )

		# ------------------------------------
		# write message
		# ------------------------------------
		self.__uart_conn.write( hex_list )
		time.sleep(.1)
	
	# ==================================
    # readLine(): Used to manually read
	# from the uart buffer.
	#
	# NOTE: old data can reside in the buffer
	# if it has not been flushed. 
    # ==================================
	def readLine(self, read_limit_size: int ) -> ' str':
		return self.__uart_conn.read( read_limit_size )
	
	# ==================================
    # write_and_read() 
    # ==================================
	def write_and_read(self, str, auto_return_carrige = True, read_limit = 500 ) -> 'str':
		# ------------------------------------
		# clear connection so message is Tx/RX'ed
		# fresh
		# ------------------------------------
		self.clear_connection()

		# ------------------------------------
		# write line
		# ------------------------------------
		self.writeLine( str, auto_return_carrige )

		# ------------------------------------
		# read line and decode
		# ------------------------------------
		return_str = self.readLine( str, auto_return_carrige, read_limit )
		return_str = return_str.decode( "utf-8" )

		return return_str
	
	# ==================================
    # clear_connection() 
    # ==================================
	def clear_connection(self) -> 'None':
		self.__uart_conn.write( [ ord('\r') ] )
		time.sleep(.1)
		self.__uart_conn.flushInput()

	# ==================================
    # helper function: str_to_hex()
    # ==================================
	def __str_to_hex_list(self, str) -> 'list':
		hex_list = []
		for i in str:
			hex_list.append( ord( i ) )

		return hex_list
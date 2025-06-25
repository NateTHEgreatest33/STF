#*********************************************************************
#
#   MODULE NAME:
#       pi_pico.py - Raspberry Pi Pico Testing Class
#
#   DESCRIPTION:
#       Class to provide functionaility for testing with the Raspberry
#		pi pico.
#
#   Copyright 2024 by Nate Lenze
#*********************************************************************

#---------------------------------------------------------------------
#                              IMPORTS
#---------------------------------------------------------------------
from lib.msgAPI import messageAPI
from lib.consoleAPI import consoleAPI

import RPi.GPIO as GPIO  
import time
import os

#---------------------------------------------------------------------
#                          CLASSES
#---------------------------------------------------------------------
class pi_pico:
	msg_conn = None
	console_conn = None

	# ==================================
	# Constructor
	# ==================================
	def __init__(self, test_mode = False, power_cycle_pin=23 ):
		self.msg_conn = messageAPI( 
								bus = 0, 
								chip_select = 0, 
								currentModule = 0x00, 
								listOfModules=[0x00,0x01] 
								)
		self.console_conn = consoleAPI()
		self.msg_conn.InitAPI()
		
		# ------------------------------------
		# setup power cycle pin. Power cycle
		# happens when RUN pin on the pico
		# is connected to ground. To implement
		# this a relay, controlled by the 3B+,
		# connects or disconnects the circuit
		# ------------------------------------
		self.power_cycle_pin = power_cycle_pin
		GPIO.setmode(GPIO.BCM)
		GPIO.setup(self.power_cycle_pin, GPIO.OUT )

		self.power_cycle()
		self.set_test_mode( test_mode )
	
	# ==================================
	# set_test_mode()
	# ==================================
	def set_test_mode( self, enabled ) -> 'bool':
		# ------------------------------------
		# attempt to place pico into test mode
		# ------------------------------------
		rtn = self.console_conn.write_and_read( "testmode")
		if self.__verify_test_mode( rtn, enabled ):
			return True

		# ------------------------------------
		# since first attempt failed, try again
		# (toggle behavior)
		# ------------------------------------
		rtn = self.console_conn.write_and_read( "testmode")
		if self.__verify_test_mode( rtn, enabled ):
			return False
		
		# ------------------------------------
		# if still unable to enter test mode
		# there must be another issue, print
		# error and exit
		# ------------------------------------
		print("Test mode not working")
		return False
	
	# ==================================
	# power_cycle()
	# ==================================
	def power_cycle( self ) -> 'None':
		# ------------------------------------
		# Power Off, Sleep 2s, Power On
		# ------------------------------------
		GPIO.output(self.power_cycle_pin, GPIO.HIGH)
		time.sleep(2)
		GPIO.output(self.power_cycle_pin, GPIO.LOW)
		time.sleep(1) #allow to come back online


	# ==================================
	# load_software()
	# ==================================
	def load_software( self, elf_file_path ) -> 'None':
		self.console_conn.write_and_read( "bootsel" )
		os.system( "picotool load {}".format( elf_file_path) )
		self.power_cycle()

	# ==================================
	# helper function: __verify_test_mode()
	# ==================================
	def __verify_test_mode( self, rtn_str, enabled ) -> 'bool':
		expected_str = ( "testmode\r\nTest Mode: enabled\r\n" if enabled  else "testmode\r\nTest Mode: disabled\r\n")
		return ( rtn_str == expected_str )
	
	# ==================================
    # deconstructor
    # ==================================
	def __del__(self):
		# Reset test mode at end of test
		self.set_test_mode( False )
		self.power_cycle()
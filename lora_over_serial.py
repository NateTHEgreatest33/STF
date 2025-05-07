#*********************************************************************
#
#   MODULE NAME:
#       lora_over_serial.py - class for interfacing w/ lora over serial
#							  in python!
#
#   DESCRIPTION:
#       Provides message API functionality
#
#   Copyright 2025 by Nate Lenze
#*********************************************************************

# note requires python3.11!! (run using python3.11 lora_over_serial.py

#---------------------------------------------------------------------
#                              IMPORTS
#---------------------------------------------------------------------
import serial
import serial.tools.list_ports
import time

#---------------------------------------------------------------------
#                             VARIABLES
#---------------------------------------------------------------------
MAX_SER_TIMEOUT = 10  #in 1/10 of a sec, 10 = 1s

#---------------------------------------------------------------------
#                              CLASSES
#---------------------------------------------------------------------
class lora_serial:
    # ==================================
    # Constructor
    # ==================================
	def __init__(self, port="/dev/cu.usbmodem1101", baud=115200, debug_prints=False ):
		self.print_cmds = debug_prints
		self.ser_conn = serial.Serial(port=port, baudrate=115200, timeout=0)
		self.ser_conn.close()
		self.ser_conn.open()
		self.ser_conn.flush()
		self.send_cmd( "junkcmd" ) #clear out command buffer and flush
		self.read_and_return()
		self.glb_dbg = [] #allows you to see full response (helpful for debugging)
		
    # ==================================
    # x()
    # ==================================
	def __LoraInit(self):
		#dont need to do anything here since module will already be inited
		pass

    # ==================================
    # x()
    # ==================================
	def __LoraCheckMessage(self):
		raise( NotImplemented )
		pass

    # ==================================
    # x()
    # ==================================
	def __LoraReadMessageSingle(self):
		return self.LoraReadMessageSingle()
	
	def LoraReadMessageSingle(self):
		raise( NotImplemented )	

    # ==================================
    # x()
    # ==================================
	def __LoraReadMessageMulti(self):
		return self.LoraReadMessageMulti()

	def LoraReadMessageMulti(self):
		self.send_cmd( "lora get")
		response = self.read_and_return()

		if response[:5] == "Error":
			return []

		if self.print_cmds:
			print("Raw Lora Read: {}".format( response) )

		#format return
		rsp_list = response.split()
		rtn_lst = []
		for item in rsp_list:
			rtn_lst.append( int(item) )
		return rtn_lst

    # ==================================
    # x()
    # ==================================
	def __LoraSetRxMode(self):
		self.LoraSetRxMode()

	def LoraSetRxMode(self):
		self.send_cmd( "lora init rx" )
		self.read_and_return()
		

    # ==================================
    # x()
    # ==================================
	def __LoraSendMessage( self, messageList, messageSize):
		return self.LoraSendMessage( messageList, messageSize)
	
	def LoraSendMessage( self, messageList, messageSize):
		command = "lora send"
		for item in messageList:
			#NOTE: lora_serial is hardcoded to rx 4 char (0x00), you MUST pad out hex values!
			command = command + " " + f'{item:#0{4}x}'

		self.send_cmd( command )
		response = self.read_and_return()
		pass

    # ==================================
    # x()
    # ==================================
	def read_and_return(self, ignore_full_response=False ):
		response = self.ser_conn.read(10000).decode('utf-8') #.split("\r\n")
		timeout_cnt = 0
		if( ignore_full_response ):
			return ['']
		# wait for a full response to come in. This is signified 
		# by 2x return lines: 1) orginal msg, 2) response 
		while( response.count("\r\n") < 2 and timeout_cnt <= MAX_SER_TIMEOUT ):
			time.sleep(.1)
			timeout_cnt = timeout_cnt + 1 
			response = response + self.ser_conn.read(10000).decode('utf-8') #.split("\r\n")
		
		response = response.split("\r\n")
		self.glb_dbg = response
		return response[1]

    # ==================================
    # x()
    # ==================================
	def send_cmd(self, cmd ):
		if self.print_cmds == True:
			print( "sending command: {}".format(cmd))
		cmd = cmd + "\r"
		self.ser_conn.write( cmd.encode('utf-8') )

    # ==================================
    # x()
    # ==================================
	def flush_buffer(self ):
		#do a read& return to flush buffer
		self.read_and_return( ignore_full_response = True )


#---------------------------------------------------------------------
#                      MAIN FUNCTION
#---------------------------------------------------------------------
def main():
	print("Available Ports: ")
	ports = list(serial.tools.list_ports.comports())
	for p in ports:
		print(p)

	# port_sel = input("please provide port\n")
	port_sel = "/dev/cu.usbmodem1101"

	l_serial = lora_serial(port=port_sel)
	

	while( True ):
		l_serial.flush_buffer()
		in_cmd = input("Enter Command\n")
		match in_cmd:
			case "rx":
				rtn_data = l_serial.LoraReadMessageMulti()
				print( "rtn data: {}".format( [hex(i) for i in rtn_data] ) )
			case "tx":
				l_serial.LoraSendMessage( [0x01, 0x02, 0x03], 3 )
				l_serial.LoraSetRxMode()
			case "init rx":
				l_serial.__LoraSetRxMode()
			case _:
				print("No Command matches")
	
	return



#---------------------------------------------------------------------
#                      MAIN TEST LOOP SWRS0001
#---------------------------------------------------------------------
if __name__ == "__main__":
  main()
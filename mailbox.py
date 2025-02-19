#*********************************************************************
#
#   MODULE NAME:
#       mailbox.py - mailboxAPI Interfacing Class
#
#   DESCRIPTION:
#       Class to provide functionaility for interacting with the Raspberry
#		pi pico through the mailboxAPI
#
#   Copyright 2025 by Nate Lenze
#*********************************************************************

#---------------------------------------------------------------------
#                              DEBUG
#--------------------------------------------------------------------- 
Debug        = False #debug just this file (imports + main function)
Debug_test   = False #if we have imported this from a system test but want to run fake msgAPI
Debug_hw     = False #force skip TIVA board
Debug_prints = True 
#---------------------------------------------------------------------
#                              IMPORTS
#--------------------------------------------------------------------- 
import time
from enum import IntEnum

# needed for float32
import numpy as np
import struct

#only do this to fix imports
if Debug_test:
    from lib.util.msgAPI_sim import messageAPI
elif Debug:
    from util.msgAPI_sim import messageAPI 
else:
    from lib.msgAPI import messageAPI

#---------------------------------------------------------------------
#                              CONSTANTS
#--------------------------------------------------------------------- 
ACK_ID        = 0xFF
MSG_UPDATE_ID = 0xFE

#---------------------------------------------------------------------
#                            HELPER CLASSES
#--------------------------------------------------------------------- 
class modules(IntEnum):
    RPI_MODULE  = 0
    PICO_MODULE = 1

    NUM_MODULES = 2
    MODULE_ALL  = 3

class special_response(IntEnum):
    ACK_ID = 0xFF
    MSG_UPDATE_ID = 0xFE

class mailbox_idx(IntEnum):
    DATA = 0
    RATE = 1
    FLAG = 2
    DIR  = 3
    SRC  = 4
    DEST = 5

#---------------------------------------------------------------------
#                              VARIABLES
#--------------------------------------------------------------------- 
global_mailbox = [
# data, type,   flag,  dir,  src,                    dest
[ 0,   'ASYNC', False, 'RX', modules.RPI_MODULE,  modules.PICO_MODULE ],
[ 0.0, '1',     False, 'TX', modules.PICO_MODULE, modules.RPI_MODULE  ],
[ 0,   '5',     False, 'TX', modules.RPI_MODULE,  modules.PICO_MODULE ], 
[ 0.0, '5',     False, 'TX', modules.RPI_MODULE,  modules.PICO_MODULE ],
 ]

#---------------------------------------------------------------------
#                              CLASSES
#---------------------------------------------------------------------

class Mailbox():
    # ==================================
    # constructor() 
    # ==================================	
    def __init__(self, msg_conn, gbl_mailbox, manage_lst = None ):
        self.msg_conn          = msg_conn
        self.mailbox_map       = gbl_mailbox

        self.round_counter     = 0 # round counter always starts at 0 
        self.ack_list          = []
        self.expecting_ack_map = {}
        self.current_round     = 0
        self.tx_queue          = []

		# ------------------------------------
		# By default we only manage the
        # current module (ourself). However for
        # testing we can manage multiple modules
		# ------------------------------------
        self.manage_list = [ msg_conn.currentModule ] if manage_lst is None else manage_lst
        if manage_lst != None:
            # we need to make changes to msgAPI to provide destination data before we can implement here
            raise( NotImplementedError )

	# ==================================
    # mailbox_runtime() 
    # ==================================	
    def runtime( self ):
		# ------------------------------------
		# Call Rx and Tx Functions
		# ------------------------------------
        self.rx_runtime()
        time.sleep(.5)
        self.tx_runtime()


	# ==================================
    # rx_runtime() 
    # ==================================	
    def rx_runtime( self ):
		# ------------------------------------
		# Determine if we have any new messages
        # and exit if not
		# ------------------------------------
        rtn_data = self.msg_conn.RX_Multi()
        if( rtn_data == None ):
            return
        
		# ------------------------------------
		# Parse new message data
		# ------------------------------------
        num_rx, data_rx = rtn_data

		# ------------------------------------
		# Loop through each message
		# ------------------------------------
        if num_rx != 0:
            for msg in data_rx:
                rx_src, rx_data, rx_validity = msg

                # -----------------------------
                # Do not handle if validity is
                # False
                # -----------------------------
                if rx_validity != True:
                    print("Invalid msg Rx'ed: src/{} data/{} valid/{}".format(rx_src, rx_data, rx_validity))
                    continue

                # -----------------------------
                # Parse raw MsgAPI
                # -----------------------------
                self.debug_prints(dir='RX', data=rx_data)
                self.__parse_rx( rx_data )

	# ==================================
    # tx_runtime() 
    # ==================================
    def tx_runtime( self ):
		# ------------------------------------
		# Exit if it is not our turn to transmit
		# ------------------------------------
        if self.current_round != self.msg_conn.currentModule:
            return
        
		# ------------------------------------
		# Verify Acks
		# ------------------------------------
        for idx in self.expecting_ack_map:
            # ---------------------------------
            # If missing an ACK, report error &
            # clear for next round
            # ---------------------------------
            if self.expecting_ack_map[idx] == True:
                print("Missing ACK for idx {}".format( idx ) )
                self.expecting_ack_map[ idx ] = False

		# ------------------------------------
		# Loop through each entry in map and
        # handle any that need handling
		# ------------------------------------
        for idx, [data, rate, flag, dir, src, dest] in enumerate(self.mailbox_map):
            if( src == self.msg_conn.currentModule ):
                # ----------------------------
                # Only handle if:
                # 1) ASYNC and flagged 
                # *OR*
                # 2) Round % cntr == 0 
                # -----------------------------
                if ( rate == 'ASYNC' and flag == True ) or ( rate != 'ASYNC' and ( self.round_counter % int(rate) == 0) ):
                    self.tx_queue.append( ['data', idx] )
                    self.expecting_ack_map[ idx ] = True

		# ------------------------------------
		# Add round updater to tx queue
		# ------------------------------------
        self.tx_queue.append( [ 'round', 0 ] ) 

		# ------------------------------------
		# Pack and send Tx queue
		# ------------------------------------
        self.debug_prints(dir='TX',data=[])
        self.__msg_interface_pack_and_send()

		# ------------------------------------
		# Update round counter
        # 
        # NOTE: this is different than current
        # round, this is used to associate TX
        # rate by rate of tx_runtime()
		# ------------------------------------
        self.round_counter = (self.round_counter + 1) % 100

	# ==================================
    # __msg_interface_pack_and_send() 
    # ==================================	
    def __msg_interface_pack_and_send( self ):
		# ------------------------------------
		# setup local variables
		# ------------------------------------
        msg_data = []
        msg_dest = None

		# ------------------------------------
		# Loop through TX queue
		# ------------------------------------
        for data_type, data_idx in self.tx_queue:
            # ----------------------------
            # Data Type
            # ----------------------------
            if data_type == 'data':
                data_var, rate, flag, dir, src, dest = self.mailbox_map[data_idx]
                data_size = 1 if type(data_var) is bool else 4
                data_dest = dest

                # ------------------------
                # Because u32, flt and bool
                # are formatted differently
                # in binary, we need to
                # handle formatting
                # ------------------------
                data_formated = self.__data_type_handler( data_var, data_idx )

            # ----------------------------
            # Ack Type
            # ----------------------------
            if data_type == 'ack':
                data_var, rate, flag, dir, src, dest = self.mailbox_map[data_idx]
                data_size = 1
                data_dest = src

                data_formated = [ACK_ID, data_idx]

            # ----------------------------
            # Round Update Type
            # ----------------------------
            if data_type == 'round':
                data_size = 1
                data_dest = modules.MODULE_ALL
                # ------------------------
                # Updates the current round
                # and handles rollover
                # ------------------------
                self.__round_update()

                data_formated = [ MSG_UPDATE_ID, self.current_round ]

            # --------------------------------
            # Update destination based upon:
            # if this is the first time updating
            # or if destinations do not match
            # --------------------------------
            if msg_dest == None:
                msg_dest = data_dest
            elif msg_dest != data_dest:
                msg_dest = modules.MODULE_ALL

            # --------------------------------
            # Determine if new data can fit
            # into current message. if not, TX
            # current message and begin building
            # new message
            # --------------------------------
            if (len(msg_data) + len(data_formated) ) > 10:
                # ----------------------------
                # Tx and update msg_data & 
                # msg_dest w/ new params
                # ----------------------------
                self.msg_conn.TXMessage( msg_data, msg_dest )

                msg_data = []
                msg_dest = data_dest
            
            # --------------------------------
            # Add formatted data to end of 
            # msg_data
            # --------------------------------
            for data_bytes in data_formated:
                msg_data.append( data_bytes )


		# ------------------------------------
		# Run this one last time incase we have
        # a half full message upon exit.
		# ------------------------------------
        if len(msg_data) > 0:
            self.msg_conn.TXMessage( msg_data, msg_dest )

		# ------------------------------------
		# Empty queue for next run
		# ------------------------------------
        self.tx_queue = []

	# ==================================
    # __data_type_handler()
    #
    # DESC: formats int32, float32, and
    #       bools into uint8 list
    # ==================================	
    def __data_type_handler( self, data, idx ):
        # --------------------------------
        # integer
        # --------------------------------
        if type(data) == type(int()):
            temp_arr =  [ idx, (data >> 24 ), ((data >> 16) & 0x000000FF), ((data >> 8) & 0x000000FF), (data & 0x000000FF)]
            #fix direction packing
            return [ idx, temp_arr[4], temp_arr[3], temp_arr[2], temp_arr[1] ]
        # --------------------------------
        # bool
        # --------------------------------
        if type(data) == type(bool()):
            return [ idx, int(data) ]
        # --------------------------------
        # float
        # --------------------------------
        if type(data) == type(float()):
            temp_data = np.float32(data)
            hex_str = hex(struct.unpack('<I', struct.pack('<f', temp_data))[0])
            int_representation = int( hex_str, 16 )
            
            temp_arr = [ idx, (int_representation >> 24 ), ((int_representation >> 16) & 0x000000FF), ((int_representation >> 8) & 0x000000FF), (int_representation & 0x000000FF)]
            #fix direction packing
            return [ idx, temp_arr[4], temp_arr[3], temp_arr[2], temp_arr[1] ]

	# ==================================
    # __round_update() 
    # ==================================	
    def __round_update( self ):
        if Debug_hw:
            self.current_round = int(modules.PICO_MODULE)
            return

		# ------------------------------------
		# Update current round & account for
        # rollovers
		# ------------------------------------
        self.current_round = (self.current_round + 1 ) % len( self.msg_conn.listOfModules )

	# ==================================
    # __parse_rx() 
    # ==================================	
    def __parse_rx(self, rx_data ):
		# ------------------------------------
		# setup variables
		# ------------------------------------
        idx = 0

		# ------------------------------------
		# Loop through each index in rx_data
		# ------------------------------------
        while idx < len( rx_data):
            # --------------------------------
            # aquire first byte and switch 
            # based upon if it is an ACK, DATA,
            # or ROUND update
            # --------------------------------
            data_type = rx_data[idx]

            # ----------------------------
            # ACK Handling
            # ----------------------------
            if data_type == special_response.ACK_ID:
                idx = idx + 1
                self.expecting_ack_map[ rx_data[idx] ] = False
                idx = idx+1 # place index for next data
            # ----------------------------
            # UPDATE Handling. We dont have
            # to worry about a self update
            # w/ dest ALL because we cannot
            # TX and RX at the same time
            # ----------------------------
            elif data_type == special_response.MSG_UPDATE_ID:
                idx = idx + 1 
                new_rnd = rx_data[idx]
                self.__round_update()

                if new_rnd != self.current_round:
                    print("Missing RX? New Round Requested out of order")
                    self.current_round = new_rnd

                idx = idx+1 #place index for next data
            # ----------------------------
            # DATA/Default Handling
            # ----------------------------
            else:
                idx = idx + self.__data_rx_handler( rx_data[idx+1:], data_type )
                self.tx_queue.append( [ 'ack', data_type ] ) 

	# ==================================
    # __data_rx_handler() 
    # ==================================	
    def __data_rx_handler( self, data, idx ):
		# ------------------------------------
		# Aquire variables from mailbox map
		# ------------------------------------
        data_var, rate, flag, dir, src, dest = self.mailbox_map[ idx ]

		# ------------------------------------
		# Set flag to True for data RX
		# ------------------------------------
        flag = True

        # --------------------------------
        # INT -- 4 bytes + idx byte = 5
        # --------------------------------
        if type(data_var) == type(int()):
            data.reverse()
            self.mailbox_map[ idx ][mailbox_idx.DATA] = int( (data[0] << 24 ) | (data[1] << 16) | (data[2] << 8) | data[3] )
            return 5 # msg size
        
        # --------------------------------
        # BOOL -- 1 byte + idx byte = 2
        # --------------------------------
        if type(data_var) == type(bool()):
            self.mailbox_map[ idx ][mailbox_idx.DATA] = bool( data[0] )
            return 2 # msg size
        
        # --------------------------------
        # FLOAT -- 4 bytes + idx byte = 5
        #
        # This logic works due to all 
        # processors in the chain being
        # little endian. This would need
        # to be reworked if one isn't
        # --------------------------------
        if type(data_var) == type(float()):
            data.reverse()
            #Pi pico + macOS + rPi 3B+ is little endian so this should still work correctlty                  <--- this NEEDS to be verified
            raw_unit8_data = np.array(data[0:4], dtype='uint8')
            rtn = raw_unit8_data.view('<f4') #cast into float32
            self.mailbox_map[ idx ][mailbox_idx.DATA] = float(rtn[0])
            return 5 # msg size
        
        raise( "Data type is not supported, have we currupted our mailbox map?" )

    def set_data( self, data, idx ):
        if self.mailbox_map[idx][mailbox_idx.SRC] not in self.manage_list:
            return False

        if type(self.mailbox_map[idx][mailbox_idx.DATA]) != type( data ):
            return False
        
        self.mailbox_map[idx][mailbox_idx.DATA] = data
        self.mailbox_map[idx][mailbox_idx.FLAG] = True
        return True
    

    def debug_prints( self, dir, data ):
        dir_text = "Sending" if dir == 'TX' else "Receiving:"
        print( "{}: ".format(dir_text), end="")

        # ----------------------------------------
        # Rough copy of __parse_rx()
        # ----------------------------------------
        if dir == 'RX':
            # ------------------------------------
            # setup variables
            # ------------------------------------
            idx = 0
            # ------------------------------------
            # Loop through each index in rx_data
            # ------------------------------------
            while idx < len( data):
                # --------------------------------
                # aquire first byte and switch 
                # based upon if it is an ACK, DATA,
                # or ROUND update
                # --------------------------------
                data_type = data[idx]

                # ----------------------------
                # ACK Handling
                # ----------------------------
                if data_type == special_response.ACK_ID:
                    idx = idx + 1
                    print( "[ACK] - {} | ".format( hex(idx)), end="" )
                    self.expecting_ack_map[ data[idx] ] = False

                    idx = idx+1 # place index for next data
                # ----------------------------
                # UPDATE Handling. We dont have
                # to worry about a self update
                # w/ dest ALL because we cannot
                # TX and RX at the same time
                # ----------------------------
                elif data_type == special_response.MSG_UPDATE_ID:
                    idx = idx + 1 
                    new_rnd = data[idx]
                    print( "[RND] - {} | ".format( hex(new_rnd)), end="" )

                    idx = idx+1 #place index for next data
                # ----------------------------
                # DATA/Default Handling
                # ----------------------------
                else:
                    data_sz = ( 1 if type( self.mailbox_map[data_type][mailbox_idx.DATA]) is bool else 4 )
                    print( "[DATA - {}] - ".format( hex(data_type)), end="" )
                    idx = idx + 1
                    for i in range( data_sz):
                        print( "{} ".format( hex( data[idx]) ), end="" )
                        idx = idx + 1

                    print("| ", end="")


        # ----------------------------------------
        # Rough copy of __pack_tx()
        # ----------------------------------------
        if dir == 'TX':
            # ------------------------------------
            # setup local variables
            # ------------------------------------
            msg_data = []
            msg_dest = None

            # ------------------------------------
            # Loop through TX queue
            # ------------------------------------
            for data_type, data_idx in self.tx_queue:
                # ----------------------------
                # Data Type
                # ----------------------------
                if data_type == 'data':
                    data_var, rate, flag, dir, src, dest = self.mailbox_map[data_idx]

                    # ------------------------
                    # Because u32, flt and bool
                    # are formatted differently
                    # in binary, we need to
                    # handle formatting
                    # ------------------------
                    data_formated = self.__data_type_handler( data_var, data_idx )
                    print( "[DATA - {}] - ".format( hex(data_idx)), end="" )
                    for d in data_formated:
                        print( "{} ".format( hex(d)), end="")
                    print("| ", end="")
                # ----------------------------
                # Ack Type
                # ----------------------------
                if data_type == 'ack':
                    data_var, rate, flag, dir, src, dest = self.mailbox_map[data_idx]
                    data_size = 1
                    data_dest = src

                    data_formated = [ACK_ID, data_idx]
                    print( "[ACK - {}] - ".format( hex(data_idx)), end="" )
                    for d in data_formated:
                        print( "{} ".format( hex(d)), end="")
                    print("| ", end="")

                # ----------------------------
                # Round Update Type
                # ----------------------------
                if data_type == 'round':
                    data_formated = [ MSG_UPDATE_ID, self.current_round ]
                    print( "[RND] - ", end="" )
                    for d in data_formated:
                        print( "{} ".format( hex(d)), end="")
                    print("| ", end="")
   
        print("") #add \n

#---------------------------------------------------------------------
#                               MAIN
#---------------------------------------------------------------------
def main():
    # pico = pi_pico()
    msg_conn = messageAPI(  bus = 0, 
                            chip_select = 0, 
                            currentModule = 0x00, 
                            listOfModules=[0x00,0x01,0x02] )
    mailbox = Mailbox( msg_conn, global_mailbox )

 

    while( True ):
        #run every 10ms
        time.sleep(2)    
        mailbox.runtime()

        #realtime debug help
        # mailbox.current_round = 0 

        mailbox.set_data( 5.5, 3 )

        if Debug:
            #Pretend to send acks from other unit
            ack_msg = [ int(special_response.ACK_ID), 0x02 ]
            msg_conn.rx_data_fill(src=int(modules.RPI_MODULE), data=ack_msg, validity=True)


            #send data to be acked
            #note bc we send 2x for every tx_runtime we need to ack 2-3 times
            msg_to_ack = [ 0, 0, 0, 0, 1] #data from index 1
            msg_conn.rx_data_fill(src=int(modules.PICO_MODULE), data=msg_to_ack, validity=True)

            #update round command
            new_rnd = (mailbox.current_round + 1 )% modules.NUM_MODULES
            round_update_msg= [ int(special_response.MSG_UPDATE_ID), new_rnd ]
            msg_conn.rx_data_fill(src=int(modules.RPI_MODULE), data=round_update_msg, validity=True)


#---------------------------------------------------------------------
#                              RUN
#---------------------------------------------------------------------
if __name__ == "__main__":
    main()
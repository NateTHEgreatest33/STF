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
#                              IMPORTS
#--------------------------------------------------------------------- 
import time
import numpy as np # required for float32
from enum import IntEnum

# from msgAPI import messageAPI
from util.msgAPI_sim import messageAPI


#---------------------------------------------------------------------
#                              CONSTANTS
#--------------------------------------------------------------------- 
ACK_ID        = 0xFF
MSG_UPDATE_ID = 0xFE

class modules(IntEnum):
    RPI_MODULE  = 0
    TIVA_MODULE = 1    
    PICO_MODULE = 2

    NUM_MODULES = 3
    MODULE_ALL  = 4

class special_response(IntEnum):
    ACK_ID = 0xFF
    MSG_UPDATE_ID = 0xFE

#---------------------------------------------------------------------
#                              VARIABLES
#--------------------------------------------------------------------- 
global_mailbox = [
# data, type,   flag,  dir,  src,                    dest
[ 0,   'ASYNC', False, 'RX', modules.RPI_MODULE,  modules.PICO_MODULE ],
[ 0.0, '1',     False, 'TX', modules.PICO_MODULE, modules.RPI_MODULE  ],
[ 0,   '5',     False, 'TX', modules.RPI_MODULE,  modules.PICO_MODULE ],
 ]

#---------------------------------------------------------------------
#                              CLASSES
#---------------------------------------------------------------------

class Mailbox():
    def __init__(self, msg_conn, gbl_mailbox, manage_lst = None ):
        self.msg_conn = msg_conn

        # By default we only manage ourself, however to support testing the option to
        # fake other units was added here
        # self.manage_list = [ msg_conn.currentModule ] if manage_lst is None else manage_lst
        if manage_lst != None:
            # we need to make changes to msgAPI to provide destination data before we can implement here
            raise( NotImplementedError )

        self.mailbox_map   = gbl_mailbox
        self.round_counter = 0 # round counter always starts at 0 
        self.ack_list     = []
        self.expecting_ack_map = {}
        self.current_round = 0

        self.tx_queue = []
        print( "Warning Mailbox is NOT currently thread safe!")

        #
    def mailbox_runtime( self ):
        self.rx_runtime()
        self.tx_runtime()


    def rx_runtime( self ):
        rtn_data= self.msg_conn.RX_Multi()
        if( rtn_data == None ):
            return

        num_rx, data_rx = rtn_data
        #if msg rx'ed parse through each one
        if num_rx != 0:
            for msg in data_rx:
                rx_src, rx_data, rx_validity = msg
                if rx_validity != True:
                    print("Invalid msg Rx'ed: src/{} data/{} valid/{}".format(rx_src, rx_data, rx_validity))
                    continue
                self.__parse_rx( rx_data )


    def tx_runtime( self ):
        if self.current_round != self.msg_conn.currentModule:
            return
        
        #verify acks
        for idx in self.expecting_ack_map:
            if self.expecting_ack_map[idx] == True:
                print("Missing ACK for idx {}".format( idx ) )
                self.expecting_ack_map[ idx ] = False #clear for next run

        #determine which entries need handling
        for idx, [data, rate, flag, dir, src, dest] in enumerate(self.mailbox_map):
            if src ==  self.msg_conn.currentModule:
                if ( rate == 'ASYNC' and flag == True ) or ( rate != 'ASYNC' and ( self.round_counter % int(rate) == 0) ):
                    self.tx_queue.append( ['data', idx] )
                    self.expecting_ack_map[ idx ] = True

        # lastly update round
        self.tx_queue.append( [ 'round', 0 ] ) 

        self.__msg_interface_pack_and_send()

        self.round_counter = (self.round_counter + 1) % 100




        #update round counter
        # self.round_counter = (self.round_counter + 1 )% 100 

    def __msg_interface_pack_and_send( self ):

        msg_data = []
        msg_dest = None
        
        for data_type, data_idx in self.tx_queue:

            #determine data size
            match data_type:
                case 'data':
                    data_var, rate, flag, dir, src, dest = self.mailbox_map[data_idx]
                    data_size = 1 if type(data_var) is bool else 4
                    data_dest = dest
                    data_formated = self.__data_type_handler( data_var, data_idx )
                    
                case 'ack':
                    data_var, rate, flag, dir, src, dest = self.mailbox_map[data_idx]
                    data_size = 1
                    data_dest = src
                    data_formated = [ACK_ID, data_idx]

                case 'round':
                    data_size = 1
                    data_dest = modules.MODULE_ALL
                    self.__round_update()
                    data_formated = [ MSG_UPDATE_ID, self.current_round ]

                case _:
                    raise( "Incorrect data type" )

            #determine destination
            if msg_dest == None:
                msg_dest = data_dest
            elif msg_dest != data_dest:
                msg_dest = modules.MODULE_ALL

            #determine if we can fit into current_msg, if not send current message
            if (len(msg_data) + len(data_formated) ) > 10:
                self.msg_conn.TXMessage( msg_data, msg_dest )
                msg_data = []
                msg_dest = data_dest
            
            #append data to end
            for data_bytes in data_formated:
                msg_data.append( data_bytes ) #<- check for ack and round format


        #need to run tx one more time incase its the last round
        if len(msg_data) != 0:
            self.msg_conn.TXMessage( msg_data, msg_dest )

        #empty tx queue
        self.tx_queue = []


    def __data_type_handler( self, data, idx ):
        match( data ):
            case int():
                return [ idx, (data >> 24 ), ((data >> 16) & 0x000000FF), ((data >> 8) & 0x000000FF), (data & 0x000000FF)]
            case bool():
                return [ idx, int(data) ]
            case float():
                temp_data = np.float32(data)
                return [ idx, (temp_data >> 24 ), ((temp_data >> 16) & 0x000000FF), ((temp_data >> 8) & 0x000000FF), (temp_data & 0x000000FF)]
            case _:
                print(" unsupported data type")

    def __round_update( self ):
        self.current_round = (self.current_round + 1 )% len( self.msg_conn.listOfModules )

    def __parse_rx(self, rx_data ):
        idx = 0

        while idx < len( rx_data):
            data_type = rx_data[idx]
            match( data_type ):
                case special_response.ACK_ID:
                    idx = idx + 1
                    self.expecting_ack_map[ rx_data[idx] ] = False
                    idx = idx+1 #place index for next data

                case special_response.MSG_UPDATE_ID:
                    idx = idx + 1
                    new_rnd = rx_data[idx]
                    self.__round_update()
                    if new_rnd != self.current_round:
                        print("Missing RX? New Round Requested out of order")
                        self.current_round = new_rnd

                    idx = idx+1 #place index for next data

                case _:
                    idx = idx + self.__data_rx_handler( rx_data[idx+1:], data_type )
                    self.tx_queue.append( [ 'ack', data_type ] ) 

    def __data_rx_handler( self, data, idx ):
        #note data can be larger than needed
        data_var, rate, flag, dir, src, dest = self.mailbox_map[ idx ]

        flag = True
        #add ack to queue
        
        match( data_var ):
            case int():
                data_var = int( (data[0] << 24 ) | (data[1] << 16) | (data[2] << 8) | data[3] )
                return 5 #msg size
            
            case bool():
                data_var = bool( data[0] )
                return 2 #msg size
            
            case float():
                raise( NotImplementedError )
                data_var = np.float32(data)
                return 5 #msg size
            case _:
                print(" unsupported data type")

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
        time.sleep(.5)    
        mailbox.mailbox_runtime()
        #force it to be an us round everytime
        # mailbox.current_round = 0

        ack_msg = [ int(special_response.ACK_ID), 0x02 ]
        msg_conn.rx_data_fill(src=int(modules.RPI_MODULE), data=ack_msg, validity=True)


        #send data to be acked
        #note bc we send 2x for every tx_runtime we need to ack 2-3 times
        msg_to_ack = [ 0, 0, 0, 0, 1] #data from index 1
        msg_conn.rx_data_fill(src=int(modules.RPI_MODULE), data=msg_to_ack, validity=True)

        #update rounds
        new_rnd = (mailbox.current_round + 1 )% modules.NUM_MODULES
        round_update_msg= [ int(special_response.MSG_UPDATE_ID), new_rnd ]
        msg_conn.rx_data_fill(src=int(modules.RPI_MODULE), data=round_update_msg, validity=True)


#---------------------------------------------------------------------
#                              RUN
#---------------------------------------------------------------------
if __name__ == "__main__":
    main()
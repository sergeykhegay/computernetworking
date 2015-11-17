import os
import signal
import sys
import socket as soc
import multiprocessing

from datetime import datetime

# Simple logger
def log(message):
	print datetime.now(), ":", message


# Handle Ctrl+C combination.
# Release the socket specifically. 
def ctrl_c_handler(signal, frame):
	log("CTRL+C pressed. Shutting down....")
	serverSocket.shutdown(soc.SHUT_RDWR)
	serverSocket.close()
	sys.exit(0)

# Registering action upon Ctrl+C combination os used
# This is done to close the socket, otherwise it may
# take some time, until the os finds out that the 
# process is dead and releases the socket.
signal.signal(signal.SIGINT, ctrl_c_handler)


# Server configurations
S_HOST_NAME = soc.getfqdn()
S_HOST_IP = soc.gethostbyname('localhost')
S_PORT = 50007
S_WWW_PATH = os.path.abspath(os.path.join(os.getcwd(), "www"))

# Create a STREAM socket, bind to given host and port.
# Returns created socket.
def setup_server():
	serverSocket = soc.socket(soc.AF_INET, soc.SOCK_STREAM) 
	serverSocket.bind((S_HOST_IP, S_PORT))	
	serverSocket.listen(5)
	return serverSocket


# Response functions
def response200OK(con_soc, addr, resource_abs_name):
	header = response_header = "HTTP/1.1 200 OK\r\n\r\n"
	try:
		f = open(resource_abs_name, "rb")

		con_soc.send(header)	
		
		# Send the content of the requested file to the client
	    # TODO: count sent bytes to resolve fails. Someday.
		body = f.read()
		f.close()
		
		for i in xrange(0, len(body)):
			con_soc.send(body[i])
	except IOError:
		# Cannot open file.
		response500InternalServerError(con_soc, addr)


def response404NotFound(con_soc, addr):
	header = "HTTP/1.1 404 Not Found\r\n\r\n"
	
	body = "404 Not Found\n"
	body += "You are requesting more than we give in here, man!\n"
	body += "Don't be a hog!"

	message = header + body
	con_soc.sendall(message)


def response405MethodNotAllowed(con_soc, addr):
	header = "HTTP/1.1 405 Method Not Allowed\r\n\r\n"

	body = "405 Method Not Allowed\n"
	body += "Do you want to break me? But why? I'm still young!\n"
	body += "Go play with adults, bully!"

	message = header + body
	con_soc.sendall(message)


def response500InternalServerError(con_soc, addr):
	header = "HTTP/1.1 500 Internal Server Error\r\n\r\n"

	body = "500 Internal Server Error\n"
	body += "Fred messed up our prevelegies system again!\n"
	body += "He is really bad with keyboards!"

	message = header + body
	con_soc.sendall(message)


# Method functions
def GET(con_soc, addr, resource_name):
	abs_resource_name = resolve_abs_path(resource_name)

	if os.path.isfile(abs_resource_name):
		response200OK(con_soc, addr, abs_resource_name)
	else:
		response404NotFound(con_soc, addr)


# Utility functions
def resolve_abs_path(resource_name):
	abs_name = ""
	if os.path.isabs(resource_name):
		abs_name = os.path.join(S_WWW_PATH, resource_name[1:])
	else:
		abs_name = os.path.join(S_WWW_PATH, resource_name)

	return abs_name


def handle_request(con_soc, addr):
	# print "Process", multiprocessing.current_process().pid, 
	#       "starts handle request", con_soc
	
	try:
		request_message = con_soc.recv(4096)
		request = request_message.split('\n')[0]
		
		log(request)

		request = request.split(" ")
		method = request[0]
		resource_name = request[1]

		if method.lower() == "get":
			GET(con_soc, addr, resource_name)
		else:
			# I serve only one thing, but do it well
			response405MethodNotAllowed(con_soc, addr)

	except Exception as e:
		log("ALERT! The process has failed!")
		log("REASON: " + str(e))

		response500InternalServerError(con_soc, addr)
	finally:
		con_soc.shutdown(soc.SHUT_RDWR)
		con_soc.close()

# Run server loop
def run_server():
	log("Server is listening on port {0}....".format(S_PORT))
	print "Main Process", multiprocessing.current_process().pid
	while True:
		# Accept an incoming connection socket
		con_soc, addr = serverSocket.accept()
		
		# Spawn a separate process to handle the request
		p = multiprocessing.Process(target=handle_request, 
									args=(con_soc, addr))
		p.start()
		# print "Active children", multiprocessing.active_children()	


serverSocket = setup_server()
try:
	run_server()
except Exception as e:
	log("ALERT! The server has failed!")
	log("REASON: " + str(e))
finally:
	serverSocket.close()
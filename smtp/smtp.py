import ssl
import socket as soc

sender = “<FILL IN>”
recipient = “<FILL IN>“

server_name = “<FILL IN>”
server_port = <FILL IN>


msg = "\
From: \"Santa Claus\" <{0}>\n\
To: \"Good Guy\" <{1}>\n\
Subject: Winter is coming...\n\
\
Mong mong mong!".format(sender, recipient)
endmsg = "\r\n.\r\n"


# SSL
context = ssl.create_default_context()
context.verify_mode = ssl.CERT_REQUIRED


mailserver = (server_name, server_port)

s = soc.socket(soc.AF_INET, soc.SOCK_STREAM)

# Wrap up the socket in SSL layer.
client_soc = context.wrap_socket(s, server_hostname=mailserver[0])

client_soc.connect(mailserver)

recv = client_soc.recv(1024)
print recv
if recv[:3] != '220':
	print '220 reply not received from server.'

# cmd_bigone = 'HELO Alice\r\n' + "MAIL FROM:<{0}>\r\n".format(sender) + "RCPT TO:<{0}>\r\n".format(recipient) + "DATA\r\n" + msg + endmsg + "QUIT\r\n"
# client_soc.send(cmd_bigone)
# recv1 = client_soc.recv(2048)
# print recv1

# Send HELO command and print server response.
cmd_HELO = 'HELO Alice\r\n'
client_soc.send(cmd_HELO)
recv1 = client_soc.recv(1024)
print recv1
if recv1[:3] != '250':
	print '250 reply not received from server.'


# Send MAIL FROM command and print server response.
cmd_MAIL = "MAIL FROM:<{0}>\r\n".format(sender)
client_soc.send(cmd_MAIL)
recv2 = client_soc.recv(1024)
print recv2
if recv2[:3] != '250':
	print '250 reply not received from server.'


# Send RCPT TO command and print server response.
cmd_RCPT = "RCPT TO:<{0}>\r\n".format(recipient)
client_soc.send(cmd_RCPT)
recv3 = client_soc.recv(1024)
print recv3
if recv3[:3] != '250':
	print '250 reply not received from server.'


# Send DATA command and print server response.
cmd_DATA = "DATA\r\n"
client_soc.send(cmd_DATA)
recv4 = client_soc.recv(1024)
print recv4
if recv4[:3] != '354':
	print '354 reply not received from server'


# Send message data.
client_soc.send(msg)
# Message ends with a single period.
client_soc.send(endmsg)
recv5 = client_soc.recv(1024)
print recv5
if recv5[:3] != '250':
	print '250 reply not received from server'


# Send QUIT command and get server response.
cmd_QUIT = "QUIT\r\n"
client_soc.send(cmd_QUIT)
recv6 = client_soc.recv(1024)
print recv6
if recv6[:3] != '221':
	print '221 reply not received from server'

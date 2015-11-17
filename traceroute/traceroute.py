#-*-coding:utf-8-*-
import os
import sys
import struct
import time
import select
import binascii
import socket as soc

ICMP_ECHO_REQUEST = 8
MAX_HOPS = 30
TIMEOUT = 2.0
TRIES = 3


# Displays line and returns number of bytes written
def disp(line):
	sys.stdout.write(line)
	sys.stdout.flush()
	return len(line)

# The packet that we shall send to each router along the path is the ICMP echo 
# request packet, which is exactly what we had used in the ICMP ping exercise. 
# We shall use the same packet that we built in the Ping exercise
def checksum(line):
	# In this function we make the checksum of our packet
	n = len(line)

	if n % 2 == 1:
		line += '\0'
		n += 1

	csum = 0
	for i in range(0, n, 2):
		frst_b = ord(line[i])
		scnd_b = ord(line[i + 1])
		csum += (frst_b << 8) + scnd_b

		if (csum >> 16) == 1: # Carry out condition
			csum &= 0xffff
			csum += 1

	return (~csum) & 0xffff


def build_ip_header(src_ip, dest_ip, ttl_val, data_len):
	version = 4
	IHL = 5
	DSCP = 0
	ECN = 0 
	total_lenght = soc.htons(20 + data_len)
	identification = 42
	flags = 0
	fragment_offset = 0
	ttl = ttl_val
	protocol = soc.IPPROTO_ICMP
	header_checksum = 0
	
	# BSD system bug. Remove function call if not on MacOS
	source_ip = soc.inet_aton(src_ip) 
	destination_ip = soc.inet_aton(dest_ip)
	#
	
	options = 0 # Not used


	version_IHL = (version << 4) + IHL
	DSCP_ECN = (DSCP << 2) + ECN
	flags_fragment_offset = (flags << 13) + fragment_offset

	hdr = struct.pack("!BBHHHBBH4s4s", # ! - signals network byte order
						version_IHL, DSCP_ECN, total_lenght,
						identification, flags_fragment_offset,
						ttl, protocol, header_checksum,
						source_ip,
						destination_ip
					 )

	# header_checksum = checksum(hdr)
	# We do not need to calculate the checksum and reassemble the datagram, 
	# since it will be done by the OS anyway

	return hdr


def build_icmp_packet():
	ID = 42 # Does not matter much here
	csum = 0

	header = struct.pack("!bbHHh", ICMP_ECHO_REQUEST, 0, csum, ID, 1)
	data = struct.pack("!d", time.time())

	csum = checksum(header + data)
	# # Get the right checksum, and put in the header
	# if sys.platform == 'darwin':
	# 	csum = soc.htons(csum) & 0xffff
	# #Convert 16-bit integers from host to network byte order.
	# else:
	# 	csum = soc.socket.htons(csum)

	header = struct.pack("!bbHHh", ICMP_ECHO_REQUEST, 0, csum, ID, 1)
	packet = header + data

	return packet

class Timeout():
	pass		



def aggregate_domains(doms):
	res = []
	
	doms = map(lambda l: l[0] if l else None, doms)

	if len(doms) == 0:
		return res

	res.append([doms[0], 1])

	for dom in doms[1:]:
		idx = len(res) - 1
		if res[idx][0] == dom:
			res[idx][1] += 1
		else:
			res.append([dom, 1])

	return res

def get_route(hostname):
	# timeLeft = TIMEOUT
	final_dest_reached = False

	src_ip = soc.gethostbyname(soc.gethostname()) # not always works

	try:
		dest_ip = soc.gethostbyname(hostname)
		print dest_ip
	except soc.herror:
		print "Wrong hostname given %s" % (hostname)
		return

	print "traceroute to %s (%s), %d hops max" % (hostname, dest_ip, MAX_HOPS)

	icmp_proto = socket.getprotobyname("icmp")

	for ttl in xrange(1, MAX_HOPS + 1):
		line_len = 0 # How many symbols are printed in the current line
		line_len += disp(" %d" % (ttl) if ttl/10 != 0 else "  %d" % (ttl))
		domains = []
		

		for tries in xrange(TRIES):
			main_soc = soc.socket(soc.AF_INET, soc.SOCK_RAW, soc.IPPROTO_RAW)
			main_soc.setsockopt(soc.IPPROTO_IP, soc.IP_HDRINCL, 1)
			main_soc.settimeout(TIMEOUT)

			# Auxillary ICMP socket is needed to catch ICMP packets.
			# We cannot use main_soc for this work, because a socket
			# can catch only those types of messages for which it is
			# preconfigured.
			# main_soc basically cannot catch anything (am I wrong?)
			# TODO: find relevant refference
			aux_soc = soc.socket(soc.AF_INET, soc.SOCK_RAW, soc.IPPROTO_ICMP)
			aux_soc.settimeout(TIMEOUT)

			try:
				icmp_packet = build_icmp_packet()
				ip_header = build_ip_header(src_ip, dest_ip, ttl, len(icmp_packet))
				ip_datagram = ip_header + icmp_packet

				main_soc.sendto(ip_datagram, (dest_ip, 0))

				t = time.time()

				whatReady = select.select([], [aux_soc], [], TIMEOUT)
				
				# This part seems fishy and unneccesary
				# TODO: Refactor later.
				if whatReady[1] == []: 
					raise Timeout()

				recv_pkt, addr = aux_soc.recvfrom(1024)
				time_recv = time.time()
				time_elapsed = time_recv - t

				domains.append(addr)

			except Timeout:
				line_len += disp("  *")
				domains.append(None)
				continue
			except soc.timeout:
				line_len += disp("  *")
				domains.append(None)
				continue
			else:
				ip_header_len = struct.unpack("!B", recv_pkt[0:1])[0]
				ip_header_len = (ip_header_len & 0xf) * 4

				# ICMP protocol starting index
				icmp_s = ip_header_len

				icmp_type = struct.unpack("!B", recv_pkt[icmp_s : (icmp_s+1)])[0]
				
				wrong_type = False
				bytes = struct.calcsize("d")
				if icmp_type == 11 or icmp_type == 3:
					# Time Exceeded OR Destination Unreachable
					time_sent = t
				elif icmp_type == 0: 
					# Echo Reply
					# In this case we cab retrieve payload (send timestamp)
					# from the packet itself. 
					time_sent = struct.unpack("!d", 
						recv_pkt[icmp_s + 8:icmp_s + 8 + bytes])[0]

					final_dest_reached = True
				else:
					wrong_type = True

				if wrong_type:
					print "error"
				else:
					line_len += disp("  %.3f ms" % ((time_recv - time_sent) * 1000))
						
			finally:
				main_soc.close()
				aux_soc.close()

		first_domain = True
		domains = aggregate_domains(domains)
		for [dom_ip, count] in domains:
			if not first_domain:
				disp(line_len * " ")
				
				first_domain = False

			if dom_ip != None:
				try:
					domain_tuple = soc.gethostbyaddr(dom_ip)
					domain_name = domain_tuple[0]
				except soc.herror:
					domain_name = dom_ip

				disp("    %s (%s)" % (domain_name, dom_ip))
				
			else:
				disp("    (unknown)")


			if count > 1:
				disp("    " + count * "@")
			disp("\n")

		if final_dest_reached:
			return

if __name__ == "__main__":
	if len(sys.argv) == 2:
		get_route(sys.argv[1])
	else:
		print "Wrong usege. Format: traceroute.py <domainname>"

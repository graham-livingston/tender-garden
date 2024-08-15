import socket

# Set up the UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Bind the socket to the network interface and port
udp_ip = "0.0.0.0"  # Listen on all available interfaces
udp_port = 12345    # Replace with the port you're receiving data on

sock.bind((udp_ip, udp_port))

print(f"Listening for UDP data on {udp_ip}:{udp_port}...")

while True:
    # Receive data from the socket (4096 is the buffer size)
    data, addr = sock.recvfrom(4096)  
    
    # Process the received data
    print(f"Received data from {addr}: {data}")

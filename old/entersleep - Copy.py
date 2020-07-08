import os

while True:
	intxt = int(input("Enter sleep info blind into this prompt or press Ctrl+C to get to the bash prompt: "))
	with open('/home/pi/temp.txt', 'w') as f:
		f.write(str(intxt))

# taskmanager
Supervisord like program manager

This project is composed of a main program, handling the processes how they have been configured in the config_file
and a client, communicating with it through UNIX Sockets, sending it commands to perform in relation with the configured tasks.
At each accepted connection, the main program creates a new thread wich handles the client.
This was an introduction to inter-process communication through the python socket module and to the threading module.

Usage:
  python taskmaster.py conf_file
  and, in another terminal:
  python cli.py

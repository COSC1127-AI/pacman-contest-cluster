#!/usr/bin/python

import paramiko
from scp import SCPClient


class RunCommand:
    def __init__(self):
        self.hosts = []

        self.connections = []

    def do_add_host(self, args):
        """
        Add the passed host to the hosts list.
        :param args a string containing (comma-separated) host, username and password
        """
        if args:
            self.hosts.append(args.split(','))
        else:
            print "usage: host "

    def do_connect(self):
        """
        Connects to all of the hosts in the hosts list.
        """
        self.do_close()
        self.connections = []

        for host in self.hosts:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(
                paramiko.AutoAddPolicy())
            client.connect(host[0],
                           username=host[1],
                           password=host[2])
            self.connections.append(client)

    def do_run(self, command):
        """
        Executes the given command on all hosts in the hosts list.
        """
        if command:
            for host, conn in zip(self.hosts, self.connections):
                print 'host: %s: %s' % (host[0], command)
                stdin, stdout, stderr = conn.exec_command(command)
                stdin.close()
                for line in stdout.read().split("\n"):
                    print 'host: %s: %s' % (host[0], line)
        else:
            print "usage: run "

    def do_close(self):
        """
        Closes all the connections opened when do_open() was called.
        :return: 
        """
        for conn in self.connections:
            conn.close()

    def do_get(self, filename):
        """
        Copies the given file-name from the remote host to this machine.
        :param filename: the path of the file to be copied
        """
        for host, conn in zip(self.hosts, self.connections):
            scp = SCPClient(conn.get_transport())
            scp.get(filename)
            print 'get %s file from host: %s:' % (filename, host[0])

    def do_put(self, filename, destination):
        """
        Copies the given file-name from this machine to the remote host.
        :param filename: the path of the file to be copied
        :param destination: the destination path
        """
        for host, conn in zip(self.hosts, self.connections):
            scp = SCPClient(conn.get_transport())
            scp.put(filename, destination)
            print 'put %s file from host: %s:' % (filename, host[0])
#!/usr/bin/env python

"""
Measure btrfs filesystem compression ratio by comparing 'du -sh' and 'df -h'
outputs.
"""

import optparse
import subprocess
import sys


def error(msg):
    """
    In case of error print message and exit with non-zero exit code.
    :param msg: message
    :return: None
    """
    print msg
    sys.exit(1)


def run(cmd):
    """
    Run command in shell.
    :param cmd: command to run
    :return: exit_code, output
    """
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    output, dummy = proc.communicate()
    return proc.returncode, output


def subvolume_list(mount_point):
    """
    Find all subvolumes that are part of btrfs filesystem with given mount
    point and return their mounts. It is used later for 'du -sh'.
    :param mount_point: given mount point
    :return: list of mounts
    """
    [exit_code, output] = run("btrfs subvolume list %s" % (mount_point, ))
    if exit_code != 0:
        error("'btrfs' returned error")
    mounts = set()
    if output:
        for output_line in output.splitlines():
            subvolume = output_line.split()[-1]
            with open('/etc/fstab', 'r') as fstab:
                for fstab_line in fstab:
                    if "subvol=%s" % (subvolume, ) in fstab_line:
                        mounts.add(fstab_line.split()[1])
                        break
    else:
        mounts.add("%s" % (mount_point, ))
    return mounts


def main():
    """
    Main function where everything happens.
    :return: None
    """
    usage = "usage: %prog [mount point]"
    parser = optparse.OptionParser(usage)
    args = parser.parse_args()[1]

    if len(args) != 1:
        parser.error("incorrect number of arguments")

    mounts = subvolume_list(args[0])
    # compressed size
    # df displays size of whole filesystem, not just one subvolume
    [exit_code, output] = run("df -h -BM --output=used %s" % (args[0], ))
    if exit_code != 0:
        error("'df' returned error")
    comp_size = int(output.splitlines()[-1][:-1])

    # compute real size from all subvolumes
    real_sizes = []
    for mount in mounts:
        [exit_code, output] = run("du -sx -BM %s" % (mount, ))
        if exit_code == 0:
            real_sizes.append(int(output.split()[0][:-1]))
        else:
            error("'du' returned error")
    real_size = sum(real_sizes)

    comp_ratio = real_size / float(comp_size)
    space_save = (1 - (comp_size / float(real_size))) * 100
    print "Btrfs compressed %sMB to %sMB." % (real_size, comp_size)
    print "Compression ratio %.2fx" % (comp_ratio, )
    print "Space savings %.2f%%" % (space_save, )


if __name__ == "__main__":
    main()

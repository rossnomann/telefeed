#!/usr/bin/env python3
import subprocess
import sys


def main():
    argc = len(sys.argv)
    if argc < 2:
        print('Usage: {} <command> [args...]'.format(sys.argv[0]))
        sys.exit(1)
    command = sys.argv[1]
    if command == 'test':
        if argc != 2:
            print('Too many arguments')
            sys.exit(1)
        result = subprocess.run(['docker-compose', 'run', '--rm', 'app', 'bin/tests'])
        sys.exit(result.returncode)
    elif command == 'build':
        if argc == 3:
            version = sys.argv[2]
        elif argc != 2:
            print('Too many arguments')
            sys.exit(1)
        else:
            version = None
        result = subprocess.run(['docker-compose', 'build', 'app'])
        exitcode = result.returncode
        if version:
            if exitcode != 0:
                sys.exit(exitcode)
            target_image = 'rossnomann/telefeed:{}'.format(version)
            result = subprocess.run(['docker', 'tag', 'telefeed:latest', target_image])
            exitcode = result.returncode
        sys.exit(exitcode)
    else:
        print('Unknown command: {}'.format(command))
        sys.exit(1)


if __name__ == '__main__':
    main()

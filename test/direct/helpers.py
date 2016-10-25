import subprocess
import os

version_tag = os.environ['ELASTIC_VERSION']
try:
    version_tag += '-%s' % os.environ['STAGING_BUILD_NUM']
except KeyError:
    pass

docker_image = 'docker.elastic.co/kibana/kibana:' + version_tag


def run(command):
    cli = ['docker', 'run', '--rm', '--interactive', docker_image]
    cli += command.split()
    print(' '.join(cli))
    result = subprocess.run(cli, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    result.stdout = result.stdout.rstrip()
    return result


def stdout_of(command):
    return(run(command).stdout.decode())


def stderr_of(command):
    return(run(command).stderr.decode())


def environment(varname):
    environ = {}
    for line in run('env').stdout.decode().split("\n"):
        var, value = line.split('=')
        environ[var] = value
    return environ[varname]

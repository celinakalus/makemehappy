import os
import subprocess

import makemehappy.utilities as mmh

def maybeToolchain(tc):
    if ('name' in tc):
        return tc['name']
    return 'gnu'

def maybeArch(tc):
    if ('architecture' in tc):
        return tc['architecture']
    return 'native'

def maybeInterface(tc):
    if ('interface' in tc):
        return tc['interface']
    return 'none'

def generateInstances(mod):
    chains = mod.toolchains()
    cfgs = mod.buildconfigs()
    tools = mod.buildtools()
    # Return a list of dicts, with dict keys: toolchain, architecture,
    # interface, buildcfg, buildtool; all of these must be set, if they are
    # missing, fill in defaults.
    if (len(cfgs) == 0):
        cfgs = [ 'debug' ]
    if (len(tools) == 0):
        tools = [ 'make' ]
    instances = []
    for tc in chains:
        for cfg in cfgs:
            for tool in tools:
                instances.append({ 'toolchain': maybeToolchain(tc),
                                   'architecture': maybeArch(tc),
                                   'interface': maybeInterface(tc),
                                   'buildcfg': cfg,
                                   'buildtool': tool })
    return instances

def instanceDirectory(instance):
    return "{}_{}_{}_{}_{}".format(instance['toolchain'],
                                   instance['architecture'],
                                   instance['interface'],
                                   instance['buildcfg'],
                                   instance['buildtool'])

def cmakeBuildtool(name):
    if (name == 'make'):
        return 'Unix Makefiles'
    if (name == 'ninja'):
        return 'Ninja'
    return 'Unknown Buildtool'

def findToolchain(ext, tc):
    tcp = ext.toolchainPath()
    ext = '.cmake'
    for d in tcp:
        candidate = os.path.join(d, tc + ext)
        if (os.path.exists(candidate)):
            return candidate
    raise(Exception())

def cmakeConfigure(log, ext, root, instance):
    return mmh.loggedProcess(
        log,
        ['cmake',
         '-G{}'.format(cmakeBuildtool(instance['buildtool'])),
         '-DCMAKE_TOOLCHAIN_FILE={}'.format(
             findToolchain(ext, instance['toolchain'])),
         '-DCMAKE_BUILD_TYPE={}'.format(instance['buildcfg']),
         '-DPROJECT_TARGET_CPU={}'.format(instance['architecture']),
         '-DINTERFACE_TARGET={}'.format(instance['interface']),
         root])

def cmakeBuild(log, instance):
    return mmh.loggedProcess(log, ['cmake', '--build', '.'])

def cmakeTest(log, instance):
    # The last line of this command reads  like this: "Total Tests: N" …where N
    # is the number of registered tests. Fetch this integer from stdout and on-
    # ly run ctest for real, if tests were registered using add_test().
    txt = subprocess.check_output(['ctest', '--show-only'])
    last = txt.splitlines()[-1]
    num = int(last.decode().split(' ')[-1])
    if (num > 0):
        return mmh.loggedProcess(log, ['ctest', '--extra-verbose'])
    return None

def build(log, ext, root, instance):
    dname = instanceDirectory(instance)
    dnamefull = os.path.join(root, 'build', dname)
    os.mkdir(dnamefull)
    os.chdir(dnamefull)
    cmakeConfigure(log, ext, root, instance)
    cmakeBuild(log, instance)
    cmakeTest(log, instance)
    os.chdir(root)

def allofthem(log, mod, ext):
    olddir = os.getcwd()
    instances = generateInstances(mod)
    for instance in instances:
        build(log, ext, olddir, instance)

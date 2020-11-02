import mako.template as mako
import re

defaultCMakeVersion = "3.1.0"
defaultProjectName = "MakeMeHappy"
defaultLanguages = "C CXX ASM"

def cmakeVariable(name):
    return '${' + name + '}'

def deprecatedTemplate(inc):
    return re.match('^[0-9a-z_]+$', inc) != None

def lookupVariant(table, name):
    for key in table:
        if (isinstance(table[key], str)):
            regex = table[key]
            if (re.match(regex, name) != None):
                return key
        if (isinstance(table[key], list)):
            if (name in table[key]):
                return key
    return name

class Toplevel:
    def __init__(self, log, var, defaults, thirdParty, cmakeVariants,
                 modulePath, trace, deporder):
        self.log = log
        self.thirdParty = thirdParty
        self.cmakeVariants = cmakeVariants
        self.trace = trace
        self.modulePath = modulePath
        self.deporder = deporder
        self.variables = var
        self.defaults = defaults
        self.filename = 'CMakeLists.txt'

    def generateHeader(self, fh):
        for s in ["cmake_minimum_required(VERSION {})".format(defaultCMakeVersion),
                "project({} {})".format(defaultProjectName, defaultLanguages)]:
            print(s, file = fh)

    def generateCMakeModulePath(self, fh, moddirs):
        for p in moddirs:
            print("list(APPEND CMAKE_MODULE_PATH \"{}\")".format(p), file = fh)

    def generateTestHeader(self, fh):
        print("include(CTest)", file = fh)
        print("enable_testing()", file = fh)

    def expandIncludeTemplate(self, inc, name):
        moduleroot = 'deps/{}'.format(name)
        if deprecatedTemplate(inc):
            new = inc + '(${moduleroot})'
            self.log.warn(
                'Deprecated inclusion clause: "{}", use "{}" instead!'
                .format(inc, new))
            inc = new
        exp = mako.Template(inc).render(
            moduleroot = moduleroot,
            cmake = cmakeVariable)
        return exp

    def insertInclude(self, fh, name, tp, variants):
        realname = name
        if (not name in tp):
            name = lookupVariant(variants, name)

        if (name in tp):
            inc = tp[name]['include']
            if (isinstance(inc, str)):
                if ('module' in tp[name]):
                    print("include({})".format(tp[name]['module']), file = fh)
                print(self.expandIncludeTemplate(inc, realname), file = fh)
        else:
            print("add_subdirectory(deps/{})".format(name), file = fh)

    def insertInit(self, fh, name, tp, variants):
        realname = name
        if (not name in tp):
            name = lookupVariant(variants, name)

        if (name in tp and 'init' in tp[name]):
            init = tp[name]['init']
            if (isinstance(init, str)):
                print(self.expandIncludeTemplate(init, realname), file = fh)

    def generateVariables(self, fh, variables):
        for key in variables.keys():
            print('set({} "{}")'.format(key, variables[key]), file = fh)

    def generateDefaults(self, fh, defaults):
        for key in defaults.keys():
            print('if (NOT DEFINED {})'.format(key), file = fh)
            print('  set({} "{}")'.format(key, defaults[key]), file = fh)
            print('endif()', file = fh)

    def generateDependencies(self, fh, deps, thirdParty, variants):
        for item in deps:
            self.insertInclude(fh, item, thirdParty, variants)
        for item in deps:
            self.insertInit(fh, item, thirdParty, variants)

    def generateFooter(self, fh):
        print("message(STATUS \"Configured interface: ${INTERFACE_TARGET}\")",
            file = fh)
        print("add_subdirectory(code-under-test)", file = fh)

    def generateToplevel(self):
        with open(self.filename, 'w') as fh:
            self.generateHeader(fh)
            self.generateCMakeModulePath(fh, self.modulePath)
            self.generateTestHeader(fh)
            tp = {}
            for entry in self.trace.data:
                if ('cmake-extensions' in entry):
                    tp = { **tp, **entry['cmake-extensions'] }
            tp = { **tp, **self.thirdParty }
            variants = {}
            for entry in self.trace.data:
                if ('cmake-extension-variants' in entry):
                    variants = { **variants, **entry['cmake-extension-variants'] }
            variants = { **variants, **self.cmakeVariants }
            var = {}
            for entry in self.trace.data:
                if ('variables' in entry):
                    var = { **var, **entry['variables'] }
            var = { **var, **self.variables }
            self.generateVariables(fh, var)
            var = {}
            for entry in self.trace.data:
                if ('defaults' in entry):
                    var = { **var, **entry['defaults'] }
            var = { **var, **self.defaults }
            self.generateDefaults(fh, var)
            self.generateDependencies(fh, self.deporder, tp, variants)
            self.generateFooter(fh)

from comment import *
from enum import *
from function import *
from include import *
from struct import *
from utils import *
from variable import *

from lxml import etree

import sys
import argparse
import re

X = []

parser = argparse.ArgumentParser(description='Generate stubs for V-REP plugin.')
parser.add_argument('xml_file', type=str, default='',
                   help='the XML file with the callback definitions')
parser.add_argument('--cpp', '-C', type=str, default='',
                   help='the C++ source file to generate')
parser.add_argument('--hpp', '-H', type=str, default='',
                   help='the C++ header file to generate')
args = parser.parse_args()

tree = etree.parse(args.xml_file)
root = tree.getroot()

if root.tag != 'plugin':
    print('malformed XML input')
    sys.exit(2)

pluginName = root.attrib['name']
author = root.attrib['author']

X.append(Comment('This file is generated automatically! Do NOT edit!', in_definition=True))
X.append(Include('luaFunctionData.h', local=True))
X.append(Include('v_repLib.h', local=True))
X.append(Include('boost/assign/list_of.hpp'))
X.append(Include('boost/lexical_cast.hpp', in_declaration=False, in_definition=True))
X.append(Include(args.hpp if args.hpp else re.sub(r'\.c(|xx|pp|c)$','.h',args.cpp), local=True, in_declaration=False, in_definition=True))

registerFunc = Function('registerLuaStuff')
registerFunc.body = ['std::vector<int> inArgs;']

commandPrefix = 'simExt%s_' % pluginName

def c_type(param, subtype=False):
    t = param.attrib['item-type'] if subtype else param.attrib['type'] 
    if t == 'table': return 'std::vector<%s>' % c_type(param, True)
    if t == 'int': return 'int'
    if t == 'float': return 'float'
    if t == 'string': return 'std::string'
    if t == 'bool': return 'bool'

def vrep_type(param, subtype=False):
    t = param.attrib['item-type'] if subtype else param.attrib['type'] 
    if t == 'table': return 'sim_lua_arg_table|%s' % vrep_type(param, True)
    if t == 'int': return 'sim_lua_arg_int'
    if t == 'float': return 'sim_lua_arg_float'
    if t == 'string': return 'sim_lua_arg_string'
    if t == 'bool': return 'sim_lua_arg_bool'

def vrep_help_type(param):
    t = param.attrib['type'] 
    if t == 'table': return 'table' + ('_%d' % param.attrib['minsize'] if 'minsize' in param.attrib else '')
    if t == 'int': return 'number'
    if t == 'float': return 'number'
    if t == 'string': return 'string'
    if t == 'bool': return 'bool'

def lfda(param, subtype=False):
    t = param.attrib['item-type'] if subtype else param.attrib['type'] 
    suffix = '' if subtype else '[0]'
    if t == 'table': return lfda(param, True)
    if t == 'int': return 'intData' + suffix
    if t == 'float': return 'floatData' + suffix
    if t == 'string': return 'stringData' + suffix
    if t == 'bool': return 'boolData' + suffix

def c_defval(param):
    if 'default' in param.attrib:
        d = param.attrib['default']
        if param.attrib['type'] == 'table':
            d = 'boost::assign::list_of' + ''.join(map(lambda x: '(%s)' % x.strip(), d.strip()[1:-1].split(',')))
        return d
    else:
        return None

for enum in root.findall('enum'):
    enumName = enum.attrib['name']
    base = int(enum.attrib['base']) if 'base' in enum.attrib else None
    prefix = enum.attrib['item-prefix'] if 'item-prefix' in enum.attrib else ''
    fields = []
    convCases = []
    for item in enum.findall('item'):
        itemName = prefix + item.attrib['name']
        fields.append(itemName)
        registerFunc.body.append('simRegisterCustomLuaVariable("{n}", (boost::lexical_cast<std::string>({n})).c_str());'.format(n=itemName))
        convCases.append('case {n}: return "{n}";'.format(n=itemName))
    convCases.append('default: return "???";')
    X.append(Enum(enumName, fields, base))
    X.append(Function('%s_string' % enumName.lower(), ret='const char*', args=[Variable('x', enumName)], body=['switch(x)','{',convCases,'}']))
        
for cmd in root.findall('command'):
    cmdName = cmd.attrib['name']

    params = cmd.findall('params/param')
    mandatory_params = [p for p in params if 'default' not in p.attrib]
    optional_params = [p for p in params if 'default' in p.attrib]
    params = mandatory_params + optional_params

    returns = cmd.findall('return/param')

    in_struct = Struct('%s_in' % cmdName, [Variable(p.attrib['name'], c_type(p), default=c_defval(p)) for p in params])
    out_struct = Struct('%s_out' % cmdName, [Variable(p.attrib['name'], c_type(p), default=c_defval(p)) for p in returns])
    X += [in_struct, out_struct]

    cb = Variable('p', 'SLuaCallBack *')
    cmd = Variable('cmd', 'const char *')
    struct_in = Variable('in', '%s_in *' % cmdName)
    struct_out = Variable('out', '%s_out *' % cmdName)

    f1 = Function(cmdName, args=[cb, struct_in, struct_out], body=['{}(p, "{}", in, out);'.format(cmdName, commandPrefix+cmdName)])
    f2 = Function(cmdName, args=[cb, cmd, struct_in, struct_out])
    X += [f1, f2]

    if len(out_struct.fields) == 1:
        f3 = Function(cmdName, ret=out_struct.fields[0].ctype, args=[cb]+in_struct.fields, body=[
            '{}_in in_args;'.format(cmdName)
        ] + [
            'in_args.{n} = {n};'.format(n=a.name) for a in in_struct.fields
        ] + [
            '{}_out out_args;'.format(cmdName),
            '{}(p, &in_args, &out_args);'.format(cmdName),
            'return out_args.{};'.format(out_struct.fields[0].name)
        ])
        X.append(f3)

    f4 = Function(cmdName, args=[cb, struct_out]+in_struct.fields, body=[
        '{}_in in_args;'.format(cmdName)
    ] + [
        'in_args.{n} = {n};'.format(n=a.name) for a in in_struct.fields
    ] + [
        '{}(p, &in_args, out);'.format(cmdName)
    ])
    X.append(f4)

    inArgs = Variable('inArgs_%s[]' % cmdName, 'int', const=True, default='{%s}' % ', '.join(['%d' % len(params)] + ['%s, %d' % (vrep_type(p), p.attrib.get('minsize', 0)) for p in params]))
    X.append(inArgs)

    f = Function('LUA_%s_CALLBACK' % cmdName, args=[cb], body=[
        'p->outputArgCount = 0;',
        'CLuaFunctionData D;',
        'if(D.readDataFromLua(p, inArgs_{}, {}, "{}"))'.format(cmdName, len(mandatory_params), commandPrefix+cmdName),
        '{',
        [
            'std::vector<CLuaFunctionDataItem>* inData = D.getInDataPtr();', '{}_in in_args;'.format(cmdName),
            '{}_out out_args;'.format(cmdName)
        ] + [
            'in_args.%s = inData->at(%d).%s;' % (p.attrib['name'], i, lfda(p)) for i, p in enumerate(mandatory_params)
        ] + [
            'if(inData->size() > {j}) in_args.{name} = inData->at({j}).{lfda};'.format(j=len(mandatory_params)+i, name=p.attrib['name'], lfda=lfda(p), default=c_defval(p)) for i, p in enumerate(optional_params)
        ] + [
            '{}(p, "{}", &in_args, &out_args);'.format(cmdName, commandPrefix+cmdName)
        ] + [
            'D.pushOutData(CLuaFunctionDataItem(out_args.%s));' % p.attrib['name'] for p in returns
        ],
        '}',
        'D.writeDataToLua(p);'
    ])
    X.append(f)

    help_out_args = ','.join('%s %s' % (vrep_help_type(p), p.attrib['name']) for p in returns)
    help_in_args = ','.join('%s %s' % (vrep_help_type(p), p.attrib['name']) + ('=%s' % p.attrib['default'] if 'default' in p.attrib else '') for p in params)
    registerFunc.body += [
        'CLuaFunctionData::getInputDataForFunctionRegistration(inArgs_{}, inArgs);'.format(cmdName),
        'simRegisterCustomLuaFunction("{}", "{}={}({})", &inArgs[0], LUA_{}_CALLBACK);'.format(commandPrefix+cmdName, help_out_args, commandPrefix+cmdName, help_in_args, cmdName)
    ]

for fn in root.findall('script-function'):
    fnName = fn.attrib['name']

    params = fn.findall('params/param')

    returns = fn.findall('return/param')

    in_struct = Struct('%s_in' % fnName, [Variable(p.attrib['name'], c_type(p), default=c_defval(p)) for p in params])
    out_struct = Struct('%s_out' % fnName, [Variable(p.attrib['name'], c_type(p), default=c_defval(p)) for p in returns])
    X += [in_struct, out_struct]

    outArgs = Variable('outArgs_%s[]' % fnName, 'int', const=True, default='{%s}' % ', '.join(['%d' % len(returns)] + ['%s, %d' % (vrep_type(p), p.attrib.get('minsize', 0)) for p in returns]))
    X.append(outArgs)

    scriptId = Variable('scriptId', 'simInt')
    func = Variable('func', 'const char *')
    struct_in = Variable('in', '{}_in *'.format(fnName))
    struct_out = Variable('out', '{}_out *'.format(fnName))
    f = Function(fnName, ret='bool', args=[scriptId, func, struct_in, struct_out], body=[
        'SLuaCallBack c;',
        'CLuaFunctionData D;',
        'bool ret = false;',
        ''
    ] + [
        'D.pushOutData_luaFunctionCall(CLuaFunctionDataItem(in->%s));' % p.attrib['name'] for p in params
    ] + [
        'D.writeDataToLua_luaFunctionCall(&c, outArgs_{});'.format(fnName),
        '',
        'if(simCallScriptFunction(scriptId, func, &c, NULL) != -1)',
        '{',
        [
            'if(D.readDataFromLua_luaFunctionCall(&c, outArgs_{n}, outArgs_{n}[0], func))'.format(n=fnName),
            '{',
            [
                'std::vector<CLuaFunctionDataItem> *outData = D.getOutDataPtr_luaFunctionCall();'
            ] + [
                'out->%s = outData->at(%d).%s;' % (p.attrib['name'], i, lfda(p)) for i, p in enumerate(returns)
            ] + [
                'ret = true;'
            ],
            '}',
            'else',
            '{',
            [
                'simSetLastError(func, "return value size and/or type is incorrect");'
            ],
            '}'
        ],
        '}',
        'else',
        '{',
        [
            'simSetLastError(func, "callback returned an error");'
        ],
        '}',
        '',
        'D.releaseBuffers_luaFunctionCall(&c);',
        'return ret;'
    ])
    X.append(f)

X.append(registerFunc)

if args.hpp:
    with open(args.hpp, 'w') as f:
        for x in X:
            f.write(x.declaration())

if args.cpp:
    with open(args.cpp, 'w') as f:
        for x in X:
            f.write(x.definition())

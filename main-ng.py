from codegen import *
from parse import parse

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

plugin = parse(args.xml_file)

X.append(Comment('This file is generated automatically! Do NOT edit!', in_definition=True))
X.append(Include('scriptFunctionData.h', local=True))
X.append(Include('v_repLib.h', local=True))
X.append(Include('boost/assign/list_of.hpp'))
X.append(Include('boost/lexical_cast.hpp', in_declaration=False, in_definition=True))
X.append(Include(args.hpp if args.hpp else re.sub(r'\.c(|xx|pp|c)$','.h',args.cpp), local=True, in_declaration=False, in_definition=True))

registerFunc = Function('registerScriptStuff')
registerFunc.body = ['std::vector<int> inArgs;']

commandPrefix = 'simExt%s_' % plugin.name

for enum in plugin.enums:
    fields = []
    convCases = []
    for item in enum.items:
        itemName = enum.item_prefix + item
        fields.append(itemName)
        registerFunc.body.append('simRegisterScriptVariable("{n}", (boost::lexical_cast<std::string>({n})).c_str());'.format(n=itemName))
        convCases.append('case {n}: return "{n}";'.format(n=itemName))
    convCases.append('default: return "???";')
    X.append(Enum(enum.name, fields, enum.base))
    X.append(Function('%s_string' % enum.name.lower(), ret='const char*', args=[Variable('x', enum.name)], body=['switch(x)','{',convCases,'}']))
        
for cmd in plugin.commands:
    in_struct = Struct('%s_in' % cmd.name, [Variable(p.name, p.ctype(), default=p.cdefault()) for p in cmd.params])
    out_struct = Struct('%s_out' % cmd.name, [Variable(p.name, p.ctype(), default=p.cdefault()) for p in cmd.returns])
    X += [in_struct, out_struct]

    cb = Variable('p', 'SScriptCallBack *')
    cmdstr = Variable('cmd', 'const char *')
    struct_in = Variable('in', '%s_in *' % cmd.name)
    struct_out = Variable('out', '%s_out *' % cmd.name)

    f1 = Function(cmd.name, args=[cb, struct_in, struct_out], body=['{}(p, "{}", in, out);'.format(cmd.name, commandPrefix+cmd.name)])
    f2 = Function(cmd.name, args=[cb, cmdstr, struct_in, struct_out])
    X += [f1, f2]

    if len(out_struct.fields) == 1:
        f3 = Function(cmd.name, ret=out_struct.fields[0].ctype, args=[cb]+in_struct.fields, body=[
            '{}_in in_args;'.format(cmd.name)
        ] + [
            'in_args.{n} = {n};'.format(n=a.name) for a in in_struct.fields
        ] + [
            '{}_out out_args;'.format(cmd.name),
            '{}(p, &in_args, &out_args);'.format(cmd.name),
            'return out_args.{};'.format(out_struct.fields[0].name)
        ])
        X.append(f3)

    f4 = Function(cmd.name, args=[cb, struct_out]+in_struct.fields, body=[
        '{}_in in_args;'.format(cmd.name)
    ] + [
        'in_args.{n} = {n};'.format(n=a.name) for a in in_struct.fields
    ] + [
        '{}(p, &in_args, out);'.format(cmd.name)
    ])
    X.append(f4)

    inArgs = Variable('inArgs_%s[]' % cmd.name, 'int', const=True, default='{%s}' % ', '.join(['%d' % len(cmd.params)] + ['%s, %d' % (p.vtype(), getattr(p, 'minsize', 0)) for p in cmd.params]))
    X.append(inArgs)

    f = Function('%s_callback' % cmd.name, args=[cb], body=[
        '//p->outputArgCount = 0;',
        'CScriptFunctionData D;',
        'if(D.readDataFromStack(p->stackID, inArgs_{}, {}, "{}"))'.format(cmd.name, len(cmd.mandatory_params), commandPrefix+cmd.name),
        '{',
        [
            'std::vector<CScriptFunctionDataItem>* inData = D.getInDataPtr();', '{}_in in_args;'.format(cmd.name),
            '{}_out out_args;'.format(cmd.name)
        ] + [
            'in_args.%s = inData->at(%d).%s;' % (p.name, i, p.lfda()) for i, p in enumerate(cmd.mandatory_params)
        ] + [
            'if(inData->size() > {j}) in_args.{name} = inData->at({j}).{lfda};'.format(j=len(cmd.mandatory_params)+i, name=p.name, lfda=p.lfda(), default=p.cdefault()) for i, p in enumerate(cmd.optional_params)
        ] + [
            '{}(p, "{}", &in_args, &out_args);'.format(cmd.name, commandPrefix+cmd.name)
        ] + [
            'D.pushOutData(CScriptFunctionDataItem(out_args.%s));' % p.name for p in cmd.returns
        ],
        '}',
        'D.writeDataToStack(p->stackID);'
    ])
    X.append(f)

    help_out_args = ','.join('%s %s' % (p.htype(), p.name) for p in cmd.returns)
    help_in_args = ','.join('%s %s' % (p.htype(), p.name) + ('=%s' % p.default if p.default is not None else '') for p in cmd.params)
    registerFunc.body += [
        'simRegisterScriptCallbackFunction("{}@{}", "{}={}({})", {}_callback);'.format(commandPrefix+cmd.name, plugin.name, help_out_args, commandPrefix+cmd.name, help_in_args, cmd.name)
    ]

for fn in plugin.script_functions:
    in_struct = Struct('%s_in' % fn.name, [Variable(p.name, p.ctype(), default=p.cdefault()) for p in fn.params])
    out_struct = Struct('%s_out' % fn.name, [Variable(p.name, p.ctype(), default=p.cdefault()) for p in fn.returns])
    X += [in_struct, out_struct]

    outArgs = Variable('outArgs_%s[]' % fn.name, 'int', const=True, default='{%s}' % ', '.join(['%d' % len(fn.returns)] + ['%s, %d' % (p.vtype(), getattr(p, 'minsize', 0)) for p in fn.returns]))
    X.append(outArgs)

    scriptId = Variable('scriptId', 'simInt')
    func = Variable('func', 'const char *')
    struct_in = Variable('in', '{}_in *'.format(fn.name))
    struct_out = Variable('out', '{}_out *'.format(fn.name))
    f = Function(fn.name, ret='bool', args=[scriptId, func, struct_in, struct_out], body=[
        '//SScriptCallBack c;',
        'int stackID = simCreateStack();',
        'CScriptFunctionData D;',
        'bool ret = false;',
        ''
    ] + [
        'D.pushOutData_scriptFunctionCall(CScriptFunctionDataItem(in->%s));' % p.name for p in fn.params
    ] + [
        'D.writeDataToStack_scriptFunctionCall(stackID);'.format(fn.name),
        '',
        'if(simCallScriptFunctionEx(scriptId, func, stackID) != -1)',
        '{',
        [
            'if(D.readDataFromStack_scriptFunctionCall(stackID, outArgs_{n}, outArgs_{n}[0], func))'.format(n=fn.name),
            '{',
            [
                'std::vector<CScriptFunctionDataItem> *outData = D.getOutDataPtr_scriptFunctionCall();'
            ] + [
                'out->%s = outData->at(%d).%s;' % (p.name, i, p.lfda()) for i, p in enumerate(fn.returns)
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
        'D.releaseBuffers_scriptFunctionCall(&c);',
        'simReleaseStack(stackID);',
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

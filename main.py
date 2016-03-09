from codegen import *
from parse import parse
import model

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
parser.add_argument('--include', '-I', type=str, default='',
                   help='extra header file to include')
args = parser.parse_args()

plugin = parse(args.xml_file)

X.append(Comment('This file is generated automatically! Do NOT edit!', in_definition=True))
X.append(Include('string'))
X.append(Include('vector'))
X.append(Include('v_repLib.h', local=True))
if args.include:
    X.append(Include(args.include, local=True))
X.append(Include('boost/assign/list_of.hpp'))
X.append(Include('boost/lexical_cast.hpp', in_declaration=False, in_definition=True))
X.append(Include(args.hpp if args.hpp else re.sub(r'\.c(|xx|pp|c)$','.h',args.cpp), local=True, in_declaration=False, in_definition=True))

registerFunc = Function('registerScriptStuff', ret='bool', body=[])

commandPrefix = 'simExt%s_' % plugin.name

for enum in plugin.enums:
    fields = []
    convCases = []
    for item in enum.items:
        itemName = enum.item_prefix + item
        fields.append(itemName)
        registerFunc.body += [
            '{',
            [
                'int ret = simRegisterScriptVariable("{n}", (boost::lexical_cast<std::string>({n})).c_str(), 0);'.format(n=itemName),
                'if(ret == 0)',
                '{',
                [
                    'std::cout << "Plugin \'{p}\': warning: replaced variable \'{n}\'" << std::endl;'.format(p=plugin.name, n=itemName)
                ],
                '}',
                'if(ret == -1)',
                '{',
                [
                    'std::cout << "Plugin \'{p}\': error: cannot register variable \'{n}\'" << std::endl;'.format(p=plugin.name, n=itemName),
                    'return false;'
                ],
                '}',
            ],
            '}'
        ]
        convCases.append('case {n}: return "{n}";'.format(n=itemName))
    convCases.append('default: return "???";')
    X.append(Enum(enum.name, fields, enum.base))
    X.append(Function('%s_string' % enum.name.lower(), ret='const char*', args=[Variable('x', enum.name)], body=['switch(x)','{',convCases,'}']))
        
for cmd in plugin.commands:
    in_struct = Struct('%s_in' % cmd.name, [Variable(p.name, p.ctype(), default=p.cdefault()) for p in cmd.params if p.write_in])
    out_struct = Struct('%s_out' % cmd.name, [Variable(p.name, p.ctype(), default=p.cdefault()) for p in cmd.returns if p.write_out])
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

    #inArgs = Variable('inArgs_%s[]' % cmd.name, 'int', const=True, default='{%s}' % ', '.join(['%d' % len(cmd.params)] + ['%s, %d' % (p.vtype(), getattr(p, 'minsize', 0)) for p in cmd.params]))
    #X.append(inArgs)

    f = Function('%s_callback' % cmd.name, args=[cb], body=[
        'const char *cmd = "{}";'.format(commandPrefix+cmd.name),
        '',
        '{}_in in_args;'.format(cmd.name),
        '{}_out out_args;'.format(cmd.name),
        '',
        '// check argument count',
        '',
        'int numArgs = simGetStackSize(p->stackID);',
        'if(numArgs < {} || numArgs > {})'.format(len(cmd.mandatory_params), len(cmd.params)),
        '{',
        [
            'simSetLastError(cmd, "wrong number of arguments");',
            'return;'
        ],
        '}',
        '',
        '// read input arguments from stack',
        ''
    ] + unindent([
        [
            'if(numArgs >= {})'.format(i + 1),
            '{',
            [
                'simMoveStackItemToTop(p->stackID, 0);',
                'int i = simGetStackTableInfo(p->stackID, 0);',
                'if(i == -1)',
                '{',
                [
                    'simSetLastError(cmd, "error reading input argument %d (simGetStackTableInfo error)");' % (i + 1),
                    'return;'
                ],
                '}',
                'if(i == sim_stack_table_not_table || i == sim_stack_table_map)',
                '{',
                [
                    'simSetLastError(cmd, "error reading input argument %d: expected array");' % (i + 1),
                    'return;'
                ],
                '}',
                'int sz = simGetStackSize(p->stackID);',
                'if(simUnfoldStackTable(p->stackID) == -1)',
                '{',
                [
                    'simSetLastError(cmd, "error: unfold table failed ");',
                    'return;'
                ],
                '}',
                'sz = (simGetStackSize(p->stackID) - sz + 1) / 2;',
                'for(int i = 0; i < sz; i++)',
                '{',
                [
                    'if(simMoveStackItemToTop(p->stackID, simGetStackSize(p->stackID) - 2) == -1)',
                    '{',
                    [
                        'simSetLastError(cmd, "error reading input argument %d move to stack top");' % (i + 1),
                        'return;'
                    ],
                    '}',
                    'int j;',
                    'if(!read__int(p->stackID, &j))',
                    '{',
                    [
                        'simSetLastError(cmd, "error reading input argument %d array item key");' % (i + 1),
                        'return;'
                    ],
                    '}',
                    '{ntype} v;'.format(ntype=p.ctype_normalized()),
                    'if(!read__{ntype}(p->stackID, &v))'.format(ntype=p.ctype_normalized()),
                    '{',
                    [
                        'simSetLastError(cmd, "error reading input argument %d array item value");' % (i + 1),
                        'return;'
                    ],
                    '}',
                    'in_args.{n}.push_back(v);'.format(n=p.name)
                ],
                '}'] + (
                [
                'if(in_args.{n}.size() < {ms})'.format(n=p.name, ms=p.minsize),
                '{',
                [
                    'simSetLastError(cmd, "argument %d array must have at least %d elements");' % (i + 1, p.minsize),
                    'return;'
                ],
                '}'
                ] if p.minsize > 0 else []) + (
                [
                'if(in_args.{n}.size() > {ms})'.format(n=p.name, ms=p.maxsize),
                '{',
                [
                    'simSetLastError(cmd, "argument %d array must have at most %d elements");' % (i + 1, p.maxsize),
                    'return;'
                ],
                '}'
                ] if p.maxsize is not None else []) + [
            ],
            '}',
            ''
        ]
        if isinstance(p, model.ParamTable) else
        [
            'if(numArgs >= {})'.format(i + 1),
            '{',
            [
                'simMoveStackItemToTop(p->stackID, 0);',
                'if(!read__{ntype}(p->stackID, &(in_args.{n})))'.format(ntype=p.ctype_normalized(), n=p.name),
                '{',
                [
                    'simSetLastError(cmd, "error reading input argument %d");' % (i + 1),
                    'return;'
                ],
                '}'
            ],
            '}',
            ''
        ]
        for i, p in enumerate(cmd.params) if p.write_in
    ]) + ([
        '// clear stack',
        'simPopStackItem(p->stackID, 0);',
        ''
    ] if not any(p.skip for p in cmd.params) else []) + [
        '{}(p, cmd, &in_args, &out_args);'.format(cmd.name),
        '',
        '// write output arguments to stack',
        ''
    ] + unindent([
        [
            'if(simPushTableOntoStack(p->stackID) == -1)',
            '{',
            [
                'simSetLastError(cmd, "failed to write output argument %d push empty table onto stack");' % (i + 1),
                'return;'
            ],
            '}',
            'for(int i = 0; i < out_args.{n}.size(); i++)'.format(n=p.name),
            '{',
            [
                'if(!write__int(i + 1, p->stackID))',
                '{',
                [
                    'simSetLastError(cmd, "failed to write output argument %d array key");' % (i + 1),
                    'return;'
                ],
                '}',
                'if(!write__{ntype}(out_args.{n}[i], p->stackID))'.format(ntype=p.ctype_normalized(), n=p.name),
                '{',
                [
                    'simSetLastError(cmd, "failed to write output argument %d array value");' % (i + 1),
                    'return;'
                ],
                '}',
                'if(simInsertDataIntoStackTable(p->stackID) == -1)',
                '{',
                [
                    'simSetLastError(cmd, "failed to write output argument %d array");' % (i + 1),
                    'return;'
                ],
                '}',
            ],
            '}'
        ]
        if isinstance(p, model.ParamTable) else
        [
            'if(!write__{ntype}(out_args.{n}, p->stackID))'.format(ntype=p.ctype_normalized(), n=p.name),
            '{',
            [
                'simSetLastError(cmd, "error writing output argument %d");' % (i + 1),
                'return;'
            ],
            '}',
            ''
        ]
        for i, p in enumerate(cmd.returns) if p.write_out
    ]))
    X.append(f)

    help_out_args = ','.join('%s %s' % (p.htype(), p.name) for p in cmd.returns)
    help_in_args = ','.join('%s %s' % (p.htype(), p.name) + ('=%s' % p.default if p.default is not None else '') for p in cmd.params)
    registerFunc.body += [
        '{',
        [
            'int ret = simRegisterScriptCallbackFunction("{}@{}", "{}={}({})", {}_callback);'.format(commandPrefix+cmd.name, plugin.name, help_out_args, commandPrefix+cmd.name, help_in_args, cmd.name),
            'if(ret == 0)',
            '{',
            [
                'std::cout << "Plugin \'{p}\': warning: replaced function \'{n}\'" << std::endl;'.format(p=plugin.name, n=commandPrefix+cmd.name)
            ],
            '}',
            'if(ret == -1)',
            '{',
            [
                'std::cout << "Plugin \'{p}\': error: cannot register function \'{n}\'" << std::endl;'.format(p=plugin.name, n=commandPrefix+cmd.name),
                'return false;'
            ],
            '}'
        ],
        '}'
    ]

for fn in plugin.script_functions:
    in_struct = Struct('%s_in' % fn.name, [Variable(p.name, p.ctype(), default=p.cdefault()) for p in fn.params if p.write_in])
    out_struct = Struct('%s_out' % fn.name, [Variable(p.name, p.ctype(), default=p.cdefault()) for p in fn.returns if p.write_out])
    X += [in_struct, out_struct]

    #outArgs = Variable('outArgs_%s[]' % fn.name, 'int', const=True, default='{%s}' % ', '.join(['%d' % len(fn.returns)] + ['%s, %d' % (p.vtype(), getattr(p, 'minsize', 0)) for p in fn.returns]))
    #X.append(outArgs)

    scriptId = Variable('scriptId', 'simInt')
    func = Variable('func', 'const char *')
    struct_in = Variable('in', '{}_in *'.format(fn.name))
    struct_out = Variable('out', '{}_out *'.format(fn.name))
    f = Function(fn.name, ret='bool', args=[scriptId, func, struct_in, struct_out], body=[
        'int stackID = simCreateStack();',
        '',
        '// write input arguments to stack',
        ''
    ] + unindent([
        [
            'if(simPushTableOntoStack(stackID) == -1)',
            '{',
            [
                'simSetLastError(func, "failed to write input argument %d push empty table onto stack");' % (i + 1),
                'simReleaseStack(stackID);',
                'return false;'
            ],
            '}',
            'for(int i = 0; i < in->{n}.size(); i++)'.format(n=p.name),
            '{',
            [
                'if(!write__int(i + 1, stackID))',
                '{',
                [
                    'simSetLastError(func, "failed to write input argument %d array key");' % (i + 1),
                    'simReleaseStack(stackID);',
                    'return false;'
                ],
                '}',
                'if(!write__{ntype}(in->{n}[i], stackID))'.format(n=p.name, ntype=p.ctype_normalized()),
                '{',
                [
                    'simSetLastError(func, "failed to write input argument %d array value");' % (i + 1),
                    'simReleaseStack(stackID);',
                    'return false;'
                ],
                '}',
                'if(simInsertDataIntoStackTable(stackID) == -1)',
                '{',
                [
                    'simSetLastError(func, "failed to write input argument %d array");' % (i + 1),
                    'simReleaseStack(stackID);',
                    'return false;'
                ],
                '}',
            ],
            '}'
        ]
        if isinstance(p, model.ParamTable) else
        [
            'if(!write__{ntype}(in->{n}, stackID))'.format(ntype=p.ctype_normalized(), n=p.name),
            '{',
            [
                'simSetLastError(func, "failed to write input argument {i} ({ntype})");'.format(i=i, ntype=p.ctype_normalized()),
                'simReleaseStack(stackID);',
                'return false;'
            ],
            '}'
        ]
        for i, p in enumerate(fn.params) if p.write_in
    ]) + [
        '',
        'if(simCallScriptFunctionEx(scriptId, func, stackID) != -1)',
        '{',
        [
            '// read output arguments from stack',
            '',
            unindent([
                [
                    'simMoveStackItemToTop(stackID, 0);',
                    'int i = simGetStackTableInfo(stackID, 0);',
                    'if(i < {})'.format(p.minsize),
                    '{',
                    [
                        'simSetLastError(func, "error reading output argument %d: expected array");' % (i + 1),
                        'simReleaseStack(stackID);',
                        'return false;'
                    ],
                    '}',
                    'int sz = simGetStackSize(stackID);',
                    'if(simUnfoldStackTable(stackID) == -1)',
                    '{',
                    [
                        'simSetLastError(func, "error: unfold table failed ");',
                        'simReleaseStack(stackID);',
                        'return false;'
                    ],
                    '}',
                    'sz = (simGetStackSize(stackID) - sz + 1) / 2;',
                    'for(int i = 0; i < sz; i++)',
                    '{',
                    [
                        'if(simMoveStackItemToTop(stackID, simGetStackSize(stackID) - 2) == -1)',
                        '{',
                        [
                            'simSetLastError(func, "error reading output argument %d move to stack top");' % (i + 1),
                            'simReleaseStack(stackID);',
                            'return false;'
                        ],
                        '}',
                        'int j;',
                        'if(!read__int(stackID, &j))',
                        '{',
                        [
                            'simSetLastError(func, "error reading output argument %d array item key");' % (i + 1),
                            'simReleaseStack(stackID);',
                            'return false;'
                        ],
                        '}',
                        '{ntype} v;'.format(ntype=p.ctype_normalized()),
                        'if(!read__{ntype}(stackID, &v))'.format(ntype=p.ctype_normalized()),
                        '{',
                        [
                            'simSetLastError(func, "error reading output argument %d array item value");' % (i + 1),
                            'simReleaseStack(stackID);',
                            'return false;'
                        ],
                        '}',
                        'out->{n}.push_back(v);'.format(n=p.name)
                    ],
                    '}'] + (
                    [
                    'if(out->{n}.size() < {ms})'.format(n=p.name, ms=p.minsize),
                    '{',
                    [
                        'simSetLastError(func, "argument %d array must have at least %d elements");' % (i + 1, p.minsize),
                        'simReleaseStack(stackID);',
                        'return false;'
                    ],
                    '}'
                    ] if p.minsize > 0 else []) + [
                    'if(out->{n}.size() > {ms})'.format(n=p.name, ms=p.maxsize),
                    '{',
                    [
                        'simSetLastError(func, "argument %d array must have at most %d elements");' % (i + 1, p.maxsize),
                        'simReleaseStack(stackID);',
                        'return false;'
                    ],
                    '}'
                ]
                if isinstance(p, model.ParamTable) else
                [
                    'if(!read__{ntype}(stackID, &(out->{n})))'.format(ntype=p.ctype_normalized(), n=p.name),
                    '{',
                    [
                        'simSetLastError(func, "error reading output argument %d");' % (i + 1),
                        'simReleaseStack(stackID);',
                        'return false;'
                    ],
                    '}',
                    ''
                ]
                for i, p in enumerate(fn.returns) if p.write_out
            ])
        ],
        '}',
        'else',
        '{',
        [
            'simSetLastError(func, "callback error");',
            'simReleaseStack(stackID);',
            'return false;'
        ],
        '}',
        '',
        'simReleaseStack(stackID);',
        'return true;'
    ])
    X.append(f)

registerFunc.body.append('return true;')
X.append(registerFunc)

def open_output(fn):
    if fn == '-': return sys.stdout
    else: return open(fn, 'w')

def close_output(fn, h):
    if fn != '-': h.close()

if args.hpp:
    guard_name = re.sub('[^a-zA-Z0-9]', '_', args.hpp.upper()) + '__INCLUDED'
    f = open_output(args.hpp)
    f.write('#ifndef %s\n' % guard_name)
    f.write('#define %s\n\n' % guard_name)
    f.write('''
#include <v_repLib.h>
#include <string>

bool read__bool(int stack, bool *value);
bool read__int(int stack, int *value);
bool read__float(int stack, float *value);
bool read__std__string(int stack, std::string *value);
bool write__bool(bool value, int stack);
bool write__int(int value, int stack);
bool write__float(float value, int stack);
bool write__std__string(std::string value, int stack);

''')
    for x in X:
        f.write(x.declaration())
    f.write('\n#endif // %s\n' % guard_name)
    close_output(args.hpp, f)

if args.cpp:
    f = open_output(args.cpp)
    f.write('''#include <iostream>

''')
    for x in X:
        f.write(x.definition())
    f.write('''

bool read__bool(int stack, bool *value)
{
    simBool v;
    if(simGetStackBoolValue(stack, &v) == 1)
    {
        *value = v;
        simPopStackItem(stack, 1);
        return true;
    }
    else
    {
        std::cerr << "read__bool: error: expected bool value." << std::endl;
        return false;
    }
}

bool read__int(int stack, int *value)
{
    int v;
    if(simGetStackInt32Value(stack, &v) == 1)
    {
        *value = v;
        simPopStackItem(stack, 1);
        return true;
    }
    else
    {
        std::cerr << "read__int: error: expected int value." << std::endl;
        return false;
    }
}

bool read__float(int stack, float *value)
{
    simFloat v;
    if(simGetStackFloatValue(stack, &v) == 1)
    {
        *value = v;
        simPopStackItem(stack, 1);
        return true;
    }
    else
    {
        std::cerr << "read__float: error: expected float value." << std::endl;
        return false;
    }
}

bool read__std__string(int stack, std::string *value)
{
    simChar *str;
    simInt strSize;
    if((str = simGetStackStringValue(stack, &strSize)) != NULL && strSize > 0)
    {
        *value = std::string(str);
        simPopStackItem(stack, 1);
        return true;
    }
    else
    {
        std::cerr << "read__std__string: error: expected string value." << std::endl;
        return false;
    }
}

bool write__bool(bool value, int stack)
{
    simBool v = value;
    if(simPushBoolOntoStack(stack, v) == -1)
    {
        std::cerr << "write__bool: error: push value failed." << std::endl;
        return false;
    }
    else
    {
        return true;
    }
}

bool write__int(int value, int stack)
{
    int v = value;
    if(simPushInt32OntoStack(stack, v) == -1)
    {
        std::cerr << "write__int: error: push value failed." << std::endl;
        return false;
    }
    else
    {
        return true;
    }
}

bool write__float(float value, int stack)
{
    simFloat v = value;
    if(simPushFloatOntoStack(stack, v) == -1)
    {
        std::cerr << "write__float: error: push value failed." << std::endl;
        return false;
    }
    else
    {
        return true;
    }
}

bool write__std__string(std::string value, int stack)
{
    const simChar *v = value.c_str();
    if(simPushStringOntoStack(stack, v, 0) == -1)
    {
        std::cerr << "write__std__string: error: push value failed." << std::endl;
        return false;
    }
    else
    {
        return true;
    }
}


''')
    close_output(args.cpp, f)

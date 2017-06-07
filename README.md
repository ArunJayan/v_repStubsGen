# V-REP Stubs generator

This utility is used to generate boilerplate code for V-REP Lua callbacks.
It reads an XML file containing a description of the callbacks, script
functions, and enums, and it produces a pair of C++ source/header files.

What you need:
- Python interpreter (2.7 or greater)
- xsltproc program in your PATH (an XSLT processor) if you want to generate documentation (windows binary available [here](https://github.com/fferri/xsltproc-win/raw/master/xsltproc-win.zip))

Usage:

```
$ python path/to/v_repStubsGen/main.py -H stubs.h -C stubs.cpp callbacks.xml
```

generates cpp/h in one shot.

See [v_repExtPluginSkeletonNG](https://github.com/fferri/v_repExtPluginSkeletonNG) for an example of a V-REP plugin using this framework.


import lldb
import os
import shlex
import optparse

from subprocess import call
from time import sleep


def __lldb_init_module(debugger, internal_dict):
    debugger.HandleCommand(
        'command script add -f android_remote.handle_command android_remote -h "Short documentation here"'
    )


def handle_command(debugger, command, exe_ctx, result, internal_dict):
    '''
    1) Check lldb-server existence at /data/local/tmp
    2) Start lldb-server and forward port by adb
    3) Connect to lldb-server
    4) Create target
    '''
    command_args = shlex.split(command, posix=False)
    parser = generate_option_parser()
    try:
        (options, args) = parser.parse_args(command_args)
    except:
        result.SetError(parser.usage)
        return
    if len(args) != 1:
        result.SetError("[-] Wrong args amount")
        return

    if os.getenv("ANDROID_SERIAL", options.serial) is None:
        result.SetError("[-] 'adb devices' and set serial as option")
        return

    try:
        call(["adb", "wait-for-device"])
    except FileNotFoundError:
        result.SetError("[-] Cannot find adb in PATH")
        return

    if call(["adb", "shell", "[[ -f /data/local/tmp/lldb-server ]]"]):
        result.SetError(
            "[-] There is no lldb-server. Execute 'adb push $ANDROID_NDK_HOME/toolchains/llvm.dir/lib64/clang/$CLANG_VERSION/lib/linux/$TARGET_ARCH/lldb-server /data/local/tmp'"
        )
        return

    is_sudo = 'su ' if options.root else ''
    print(
        f"Execute\n\tcd /data/local/tmp/; {is_sudo}./lldb-server platform --listen *:{options.port}"
    )
    while call(["adb", "shell", "pidof lldb-server"]) == 1:
        sleep(0.2)
    call(["adb", "forward", "--remove", f"tcp:{options.port}"])
    call(["adb", "forward", f"tcp:{options.port}", f"tcp:{options.port}"])
    debugger.HandleCommand("platform select remote-android")
    debugger.HandleCommand(
        f"platform connect connect://localhost:{options.port}")
    debugger.HandleCommand(f"target create {args[0]}")

    result.AppendMessage('[+] Connection to lldb-server is successful')


def generate_option_parser():
    usage = "usage: %prog [options] /local/path/to/binary"
    parser = optparse.OptionParser(usage=usage, prog="android_remote")
    parser.add_option(
        "-p",
        "--port",
        action="store",
        default=5343,
        help="choose port for lldb-server listening (default: 5343)")
    parser.add_option("-s",
                      "--serial",
                      action="store",
                      help="android's serial id")
    parser.add_option("-r",
                      "--root",
                      action="store_true",
                      default=False,
                      help="Start lldb-server with root rights")
    return parser

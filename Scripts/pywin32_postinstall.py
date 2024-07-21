import glob
import os
import shutil
import sys
import sysconfig
from typing import TextIO

try:
    import winreg
except ImportError:
    import winreg

import tempfile

tee_f = open(os.path.join(tempfile.gettempdir(), "pywin32_postinstall.log"), "w")

class Tee:
    def __init__(self, file: TextIO):
        self.f = file

    def write(self, what: str):
        if self.f is not None:
            try:
                self.f.write(what.replace("\n", "\r\n"))
            except IOError:
                pass
        tee_f.write(what)

    def flush(self):
        if self.f is not None:
            try:
                self.f.flush()
            except IOError:
                pass
        tee_f.flush()

if sys.stdout is None:
    sys.stdout = sys.stderr

sys.stderr = Tee(sys.stderr)
sys.stdout = Tee(sys.stdout)

com_modules = [
    ("win32com.servers.interp", "Interpreter"),
    ("win32com.servers.dictionary", "DictionaryPolicy"),
    ("win32com.axscript.client.pyscript", "PyScript"),
]

silent = 0
verbose = 1

root_key_name = "Software\\Python\\PythonCore\\" + sys.winver

def file_created(file: str):
    pass

def directory_created(directory: str):
    pass

def get_root_hkey():
    try:
        winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, root_key_name, 0, winreg.KEY_CREATE_SUB_KEY
        )
        return winreg.HKEY_LOCAL_MACHINE
    except OSError:
        return winreg.HKEY_CURRENT_USER

def create_shortcut(
    path: str, description: str, filename: str, arguments: str = "", workdir: str = "", iconpath: str = "", iconindex: int = 0
):
    import pythoncom
    from win32com.shell import shell

    ilink = pythoncom.CoCreateInstance(
        shell.CLSID_ShellLink,
        None,
        pythoncom.CLSCTX_INPROC_SERVER,
        shell.IID_IShellLink,
    )
    ilink.SetPath(path)
    ilink.SetDescription(description)
    if arguments:
        ilink.SetArguments(arguments)
    if workdir:
        ilink.SetWorkingDirectory(workdir)
    if iconpath or iconindex:
        ilink.SetIconLocation(iconpath, iconindex)
    ipf = ilink.QueryInterface(pythoncom.IID_IPersistFile)
    ipf.Save(filename, 0)

def get_special_folder_path(path_name: str) -> str:
    from win32com.shell import shell, shellcon

    for maybe in """
        CSIDL_COMMON_STARTMENU CSIDL_STARTMENU CSIDL_COMMON_APPDATA
        CSIDL_LOCAL_APPDATA CSIDL_APPDATA CSIDL_COMMON_DESKTOPDIRECTORY
        CSIDL_DESKTOPDIRECTORY CSIDL_COMMON_STARTUP CSIDL_STARTUP
        CSIDL_COMMON_PROGRAMS CSIDL_PROGRAMS CSIDL_PROGRAM_FILES_COMMON
        CSIDL_PROGRAM_FILES CSIDL_FONTS""".split():
        if maybe == path_name:
            csidl = getattr(shellcon, maybe)
            return shell.SHGetSpecialFolderPath(0, csidl, False)
    raise ValueError("%s is an unknown path ID" % (path_name,))

def CopyTo(desc: str, src: str, dest: str):
    import win32api
    import win32con

    while 1:
        try:
            win32api.CopyFile(src, dest, 0)
            return
        except win32api.error as details:
            if details.winerror == 5:  # access denied - user not admin.
                raise
            if silent:
                raise
            full_desc = (
                "Error %s\n\n"
                "If you have any Python applications running, "
                "please close them now\nand select 'Retry'\n\n%s"
                % (desc, details.strerror)
            )
            rc = win32api.MessageBox(
                0, full_desc, "Installation Error", win32con.MB_ABORTRETRYIGNORE
            )
            if rc == win32con.IDABORT:
                raise
            elif rc == win32con.IDIGNORE:
                return

def LoadSystemModule(lib_dir: str, modname: str):
    import importlib.machinery
    import importlib.util

    suffix = "_d" if "_d.pyd" in importlib.machinery.EXTENSION_SUFFIXES else ""
    filename = "%s%d%d%s.dll" % (
        modname,
        sys.version_info[0],
        sys.version_info[1],
        suffix,
    )
    filename = os.path.join(lib_dir, "pywin32_system32", filename)
    loader = importlib.machinery.ExtensionFileLoader(modname, filename)
    spec = importlib.machinery.ModuleSpec(name=modname, loader=loader, origin=filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

def SetPyKeyVal(key_name: str, value_name: str, value: str):
    root_hkey = get_root_hkey()
    root_key = winreg.OpenKey(root_hkey, root_key_name)
    try:
        my_key = winreg.CreateKey(root_key, key_name)
        try:
            winreg.SetValueEx(my_key, value_name, 0, winreg.REG_SZ, value)
            if verbose:
                print("-> %s\\%s[%s]=%r" % (root_key_name, key_name, value_name, value))
        finally:
            my_key.Close()
    finally:
        root_key.Close()

def UnsetPyKeyVal(key_name: str, value_name: str, delete_key: bool = False):
    root_hkey = get_root_hkey()
    root_key = winreg.OpenKey(root_hkey, root_key_name)
    try:
        my_key = winreg.OpenKey(root_key, key_name, 0, winreg.KEY_SET_VALUE)
        try:
            winreg.DeleteValue(my_key, value_name)
            if verbose:
                print("-> DELETE %s\\%s[%s]" % (root_key_name, key_name, value_name))
        finally:
            my_key.Close()
        if delete_key:
            winreg.DeleteKey(root_key, key_name)
            if verbose:
                print("-> DELETE %s\\%s" % (root_key_name, key_name))
    except OSError as why:
        winerror = getattr(why, "winerror", why.errno)
        if winerror != 2:  # file not found
            raise
    finally:
        root_key.Close()

def RegisterCOMObjects(register: bool = True):
    import win32com.server.register

    if register:
        func = win32com.server.register.RegisterClasses
    else:
        func = win32com.server.register.UnregisterClasses
    flags = {}
    if not verbose:
        flags["quiet"] = 1
    for module, klass_name in com_modules:
        __import__(module)
        mod = sys.modules[module]
        flags["finalize_register"] = getattr(mod, "DllRegisterServer", None)
        flags["finalize_unregister"] = getattr(mod, "DllUnregisterServer", None)
        klass = getattr(mod, klass_name)
        func(klass, **flags)

def RegisterHelpFile(register: bool = True, lib_dir: str = None):
    if lib_dir is None:
        lib_dir = sysconfig.get_paths()["platlib"]
    if register:
        chm_file = os.path.join(lib_dir, "PyWin32.chm")
        if os.path.isfile(chm_file):
            SetPyKeyVal("Help", None, None)
            SetPyKeyVal("Help\\Pythonwin Reference", None, chm_file)
            return chm_file
        else:
            print("NOTE: PyWin32.chm can not be located, so has not " "been registered")
    else:
        UnsetPyKeyVal("Help\\Pythonwin Reference", None, delete_key=True)
    return None

def RegisterPythonwin(register: bool = True, lib_dir: str = None):
    if lib_dir is None:
        lib_dir = sysconfig.get_paths()["platlib"]
    classes_root = get_root_hkey()
    pythonwin_exe = os.path.join(lib_dir, "Pythonwin", "Pythonwin.exe")
    pythonwin_edit_command = pythonwin_exe + ' -edit "%1"'

    keys_vals = [
        (
            "Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\Pythonwin.exe",
            "",
            pythonwin_exe,
        ),
        (
            "Software\\Classes\\Python.File\\shell\\Edit with Pythonwin",
            "command",
            pythonwin_edit_command,
        ),
        (
            "Software\\Classes\\Python.NoConFile\\shell\\Edit with Pythonwin",
            "command",
            pythonwin_edit_command,
        ),
    ]

    try:
        if register:
            for key, sub_key, val in keys_vals:
                hkey = winreg.CreateKey(classes_root, key)
                if sub_key:
                    hkey = winreg.CreateKey(hkey, sub_key)
                winreg.SetValueEx(hkey, None, 0, winreg.REG_SZ, val)
                hkey.Close()
        else:
            for key, sub_key, val in keys_vals:
                try:
                    if sub_key:
                        hkey = winreg.OpenKey(classes_root, key)
                        winreg.DeleteKey(hkey, sub_key)
                        hkey.Close()
                    winreg.DeleteKey(classes_root, key)
                except OSError as why:
                    winerror = getattr(why, "winerror", why.errno)
                    if winerror != 2:
                        raise
    finally:
        from win32com.shell import shell, shellcon

        shell.SHChangeNotify(
            shellcon.SHCNE_ASSOCCHANGED, shellcon.SHCNF_IDLIST, None, None
        )

def get_shortcuts_folder() -> str:
    if get_root_hkey() == winreg.HKEY_LOCAL_MACHINE:
        try:
            fldr = get_special_folder_path("CSIDL_COMMON_PROGRAMS")
        except OSError:
            fldr = get_special_folder_path("CSIDL_PROGRAMS")
    else:
        fldr = get_special_folder_path("CSIDL_PROGRAMS")

    try:
        install_group = winreg.QueryValue(
            get_root_hkey(), root_key_name + "\\InstallPath\\InstallGroup"
        )
    except OSError:
        vi = sys.version_info
        install_group = "Python %d.%d" % (vi[0], vi[1])
    return os.path.join(fldr, install_group)

def get_system_dir() -> str:
    import win32api

    try:
        import pythoncom
        import win32process
        from win32com.shell import shell, shellcon

        try:
            if win32process.IsWow64Process():
                return shell.SHGetSpecialFolderPath(0, shellcon.CSIDL_SYSTEMX86)
            return shell.SHGetSpecialFolderPath(0, shellcon.CSIDL_SYSTEM)
        except (pythoncom.com_error, win32process.error):
            return win32api.GetSystemDirectory()
    except ImportError:
        return win32api.GetSystemDirectory()

def fixup_dbi():
    import win32api
    import win32con

    pyd_name = os.path.join(os.path.dirname(win32api.__file__), "dbi.pyd")
    pyd_d_name = os.path.join(os.path.dirname(win32api.__file__), "dbi_d.pyd")
    py_name = os.path.join(os.path.dirname(win32con.__file__), "dbi.py")
    for this_pyd in (pyd_name, pyd_d_name):
        this_dest = this_pyd + ".old"
        if os.path.isfile(this_pyd) and os.path.isfile(py_name):
            try:
                if os.path.isfile(this_dest):
                    print(
                        "Old dbi '%s' already exists - deleting '%s'"
                        % (this_dest, this_pyd)
                    )
                    os.remove(this_pyd)
                else:
                    os.rename(this_pyd, this_dest)
                    print("renamed '%s'->'%s.old'" % (this_pyd, this_pyd))
                    file_created(this_pyd + ".old")
            except os.error as exc:
                print("FAILED to rename '%s': %s" % (this_pyd, exc))

def install(lib_dir: str):
    import traceback

    global is_bdist_wininst
    is_bdist_wininst = False

    if os.path.isfile(os.path.join(sys.prefix, "pywin32.pth")):
        os.unlink(os.path.join(sys.prefix, "pywin32.pth"))
    for name in "win32 win32\\lib Pythonwin".split():
        sys.path.append(os.path.join(lib_dir, name))
    for name in "pythoncom pywintypes".split():
        keyname = "Software\\Python\\PythonCore\\" + sys.winver + "\\Modules\\" + name
        for root in winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER:
            try:
                winreg.DeleteKey(root, keyname + "\\Debug")
            except WindowsError:
                pass
            try:
                winreg.DeleteKey(root, keyname)
            except WindowsError:
                pass
    LoadSystemModule(lib_dir, "pywintypes")
    LoadSystemModule(lib_dir, "pythoncom")
    import win32api

    files = glob.glob(os.path.join(lib_dir, "pywin32_system32\\*.*"))
    if not files:
        raise RuntimeError("No system files to copy!!")
    for dest_dir in [get_system_dir(), sys.prefix]:
        worked = 0
        try:
            for fname in files:
                base = os.path.basename(fname)
                dst = os.path.join(dest_dir, base)
                CopyTo("installing %s" % base, fname, dst)
                if verbose:
                    print("Copied %s to %s" % (base, dst))
                file_created(dst)
                worked = 1
                bad_dest_dirs = [
                    os.path.join(sys.prefix, "Library\\bin"),
                    os.path.join(sys.prefix, "Lib\\site-packages\\win32"),
                ]
                if dest_dir != sys.prefix:
                    bad_dest_dirs.append(sys.prefix)
                for bad_dest_dir in bad_dest_dirs:
                    bad_fname = os.path.join(bad_dest_dir, base)
                    if os.path.exists(bad_fname):
                        os.unlink(bad_fname)
            if worked:
                break
        except win32api.error as details:
            if details.winerror == 5:
                if os.path.exists(dst):
                    msg = (
                        "The file '%s' exists, but can not be replaced "
                        "due to insufficient permissions.  You must "
                        "reinstall this software as an Administrator" % dst
                    )
                    print(msg)
                    raise RuntimeError(msg)
                continue
            raise
    else:
        raise RuntimeError(
            "You don't have enough permissions to install the system files"
        )

    pywin_dir = os.path.join(lib_dir, "Pythonwin", "pywin")
    for fname in glob.glob(os.path.join(pywin_dir, "*.cfg")):
        file_created(fname[:-1] + "c")

    try:
        RegisterCOMObjects()
    except win32api.error as details:
        if details.winerror != 5:
            raise
        print("You do not have the permissions to install COM objects.")
        print("The sample COM objects were not registered.")
    except Exception:
        print("FAILED to register the Python COM objects")
        traceback.print_exc()

    winreg.CreateKey(get_root_hkey(), root_key_name)

    chm_file = None
    try:
        chm_file = RegisterHelpFile(True, lib_dir)
    except Exception:
        print("Failed to register help file")
        traceback.print_exc()
    else:
        if verbose:
            print("Registered help file")

    fixup_dbi()

    try:
        RegisterPythonwin(True, lib_dir)
    except Exception:
        print("Failed to register pythonwin as editor")
        traceback.print_exc()
    else:
        if verbose:
            print("Pythonwin has been registered in context menu")

    make_dir = os.path.join(lib_dir, "win32com", "gen_py")
    if not os.path.isdir(make_dir):
        if verbose:
            print("Creating directory %s" % (make_dir,))
        directory_created(make_dir)
        os.mkdir(make_dir)

    try:
        fldr = get_shortcuts_folder()
        if os.path.isdir(fldr):
            dst = os.path.join(fldr, "PythonWin.lnk")
            create_shortcut(
                os.path.join(lib_dir, "Pythonwin\\Pythonwin.exe"),
                "The Pythonwin IDE",
                dst,
                "",
                sys.prefix,
            )
            file_created(dst)
            if verbose:
                print("Shortcut for Pythonwin created")
            if chm_file:
                dst = os.path.join(fldr, "Python for Windows Documentation.lnk")
                doc = "Documentation for the PyWin32 extensions"
                create_shortcut(chm_file, doc, dst)
                file_created(dst)
                if verbose:
                    print("Shortcut to documentation created")
        else:
            if verbose:
                print("Can't install shortcuts - %r is not a folder" % (fldr,))
    except Exception as details:
        print(details)

    try:
        import win32com.client  # noqa
    except ImportError:
        pass
    print("The pywin32 extensions were successfully installed.")

def uninstall(lib_dir: str):
    LoadSystemModule(lib_dir, "pywintypes")
    LoadSystemModule(lib_dir, "pythoncom")

    try:
        RegisterCOMObjects(False)
    except Exception as why:
        print("Failed to unregister COM objects: %s" % (why,))

    try:
        RegisterHelpFile(False, lib_dir)
    except Exception as why:
        print("Failed to unregister help file: %s" % (why,))
    else:
        if verbose:
            print("Unregistered help file")

    try:
        RegisterPythonwin(False, lib_dir)
    except Exception as why:
        print("Failed to unregister Pythonwin: %s" % (why,))
    else:
        if verbose:
            print("Unregistered Pythonwin")

    try:
        gen_dir = os.path.join(lib_dir, "win32com", "gen_py")
        if os.path.isdir(gen_dir):
            shutil.rmtree(gen_dir)
            if verbose:
                print("Removed directory %s" % (gen_dir,))

        pywin_dir = os.path.join(lib_dir, "Pythonwin", "pywin")
        for fname in glob.glob(os.path.join(pywin_dir, "*.cfc")):
            os.remove(fname)

        try:
            os.remove(os.path.join(lib_dir, "win32", "dbi.pyd.old"))
        except os.error:
            pass
        try:
            os.remove(os.path.join(lib_dir, "win32", "dbi_d.pyd.old"))
        except os.error:
            pass

    except Exception as why:
        print("Failed to remove misc files: %s" % (why,))

    try:
        fldr = get_shortcuts_folder()
        for link in ("PythonWin.lnk", "Python for Windows Documentation.lnk"):
            fqlink = os.path.join(fldr, link)
            if os.path.isfile(fqlink):
                os.remove(fqlink)
                if verbose:
                    print("Removed %s" % (link,))
    except Exception as why:
        print("Failed to remove shortcuts: %s" % (why,))

    files = glob.glob(os.path.join(lib_dir, "pywin32_system32\\*.*"))
    try:
        for dest_dir in [get_system_dir(), sys.prefix]:
            worked = 0
            for fname in files:
                base = os.path.basename(fname)
                dst = os.path.join(dest_dir, base)
                if os.path.isfile(dst):
                    try:
                        os.remove(dst)
                        worked = 1
                        if verbose:
                            print("Removed file %s" % (dst))
                    except Exception:
                        print("FAILED to remove %s" % (dst,))
            if worked:
                break
    except Exception as why:
        print("FAILED to remove system files: %s" % (why,))

def verify_destination(location: str):
    if not os.path.isdir(location):
        raise argparse.ArgumentTypeError('Path "{}" does not exist!'.format(location))
    return location

def main():
    import argparse

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""A post-install script for the pywin32 extensions.

    * Typical usage:

    > python pywin32_postinstall.py -install

    If you installed pywin32 via a .exe installer, this should be run
    automatically after installation, but if it fails you can run it again.

    If you installed pywin32 via PIP, you almost certainly need to run this to
    setup the environment correctly.

    Execute with script with a '-install' parameter, to ensure the environment
    is setup correctly.
    """,
    )
    parser.add_argument(
        "-install",
        default=False,
        action="store_true",
        help="Configure the Python environment correctly for pywin32.",
    )
    parser.add_argument(
        "-remove",
        default=False,
        action="store_true",
        help="Try and remove everything that was installed or copied.",
    )
    parser.add_argument(
        "-wait",
        type=int,
        help="Wait for the specified process to terminate before starting.",
    )
    parser.add_argument(
        "-silent",
        default=False,
        action="store_true",
        help='Don\'t display the "Abort/Retry/Ignore" dialog for files in use.',
    )
    parser.add_argument(
        "-quiet",
        default=False,
        action="store_true",
        help="Don't display progress messages.",
    )
    parser.add_argument(
        "-destination",
        default=sysconfig.get_paths()["platlib"],
        type=verify_destination,
        help="Location of the PyWin32 installation",
    )

    args = parser.parse_args()

    if not args.quiet:
        print("Parsed arguments are: {}".format(args))

    if not args.install ^ args.remove:
        parser.error("You need to either choose to -install or -remove!")

    if args.wait is not None:
        try:
            os.waitpid(args.wait, 0)
        except os.error:
            pass

    silent = args.silent
    verbose = not args.quiet

    if args.install:
        install(args.destination)

    if args.remove:
        uninstall(args.destination)

if __name__ == "__main__":
    main()

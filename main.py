#!/usr/bin/env python3
import argparse
import json
import os
import random
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path
from shutil import which
from subprocess import CalledProcessError
from urllib.error import HTTPError, URLError

MANIFEST_LOCATION = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
CLIENT = "client"
SERVER = "server"


def getMinecraftPath():
    if sys.platform.startswith('linux'):
        return Path("~/.minecraft")
    elif sys.platform.startswith('win'):
        return Path("~/AppData/Roaming/.minecraft")
    elif sys.platform.startswith('darwin'):
        return Path("~/Library/Application Support/minecraft")
    else:
        print("Cannot detect of version : %s. Please report to your closest sysadmin" % sys.platform)
        sys.exit()


mc_path = getMinecraftPath()


def checkjava():
    """Check for java and setup the proper directory if needed"""
    results = []
    if sys.platform.startswith('win'):
        if not results:
            import winreg

            for flag in [winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY]:
                try:
                    k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'Software\JavaSoft\Java Development Kit', 0, winreg.KEY_READ | flag)
                    version, _ = winreg.QueryValueEx(k, 'CurrentVersion')
                    k.Close()
                    k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'Software\JavaSoft\Java Development Kit\%s' % version, 0, winreg.KEY_READ | flag)
                    path, _ = winreg.QueryValueEx(k, 'JavaHome')
                    k.Close()
                    path = os.path.join(str(path), 'bin')
                    subprocess.run(['"%s"' % os.path.join(path, 'java'), ' -version'], stdout=open(os.devnull, 'w'), stderr=subprocess.STDOUT, check=True)
                    results.append(path)
                except (CalledProcessError, OSError):
                    pass
        if not results:
            try:
                subprocess.run(['java', '-version'], stdout=open(os.devnull, 'w'), stderr=subprocess.STDOUT, check=True)
                results.append('')
            except (CalledProcessError, OSError):
                pass
        if not results and 'ProgramW6432' in os.environ:
            results.extend(which('java.exe', os.environ['ProgramW6432']))
        if not results and 'ProgramFiles' in os.environ:
            results.extend(which('java.exe', os.environ['ProgramFiles']))
        if not results and 'ProgramFiles(x86)' in os.environ:
            results.extend(which('java.exe', os.environ['ProgramFiles(x86)']))
    elif sys.platform.startswith('linux') or sys.platform.startswith('darwin'):
        if not results:
            try:
                subprocess.run(['java', '-version'], stdout=open(os.devnull, 'w'), stderr=subprocess.STDOUT, check=True)
                results.append('')
            except (CalledProcessError, OSError):
                pass
        if not results:
            results.extend(which('java', path='/usr/bin'))
        if not results:
            results.extend(which('java', path='/usr/local/bin'))
        if not results:
            results.extend(which('java', path='/opt'))
    if not results:
        print('Java JDK is not installed ! Please install java JDK from http://java.oracle.com or OpenJDK')
        input("Aborting, press anything to exit")
        sys.exit(1)


def getManifest():
    if Path(f"versions/version_manifest.json").exists() and Path(f"versions/version_manifest.json").is_file():
        print("Manifest already existing, not downloading again, if you want to please accept safe removal at beginning")
        return
    downloadFile(MANIFEST_LOCATION, f"versions/version_manifest.json")


def downloadFile(url, filename):
    try:
        print(f'Downloading {filename}...')
        f = urllib.request.urlopen(url)
        with open(filename, 'wb+') as local_file:
            local_file.write(f.read())
    except HTTPError as e:
        print('HTTP Error')
        print(e)
    except URLError as e:
        print('URL Error')
        print(e)

def getLatestVersion():
    downloadFile(MANIFEST_LOCATION, f"manifest.json")
    path_to_json = Path(f'manifest.json')
    snapshot=None
    version=None
    if path_to_json.exists() and path_to_json.is_file():
        path_to_json = path_to_json.resolve()
        with open(path_to_json) as f:
            versions = json.load(f)["latest"]
            if versions and versions.get("release") and versions.get("release"):
                version = versions.get("release")
                snapshot = versions.get("snapshot")
    path_to_json.unlink()
    return snapshot,version           

def getVersionManifest(target_version):
    if Path(f"versions/{target_version}/version.json").exists() and Path(f"versions/{target_version}/version.json").is_file():
        print("Version manifest already existing, not downloading again, if you want to please accept safe removal at beginning")
        return
    path_to_json = Path(f'versions/version_manifest.json')
    if path_to_json.exists() and path_to_json.is_file():
        path_to_json = path_to_json.resolve()
        with open(path_to_json) as f:
            versions = json.load(f)["versions"]
            for version in versions:
                if version.get("id") and version.get("id") == target_version and version.get("url"):
                    downloadFile(version.get("url"), f"versions/{target_version}/version.json")
                    break
    else:
        print('ERROR: Missing manifest file: version.json')
        input("Aborting, press anything to exit")
        sys.exit()


def getVersionJar(target_version, side):
    path_to_json = Path(f"versions/{target_version}/version.json")
    if Path(f"versions/{target_version}/{side}.jar").exists() and Path(f"versions/{target_version}/{side}.jar").is_file():
        print(f"versions/{target_version}/{side}.jar already existing, not downloading again")
        return
    if path_to_json.exists() and path_to_json.is_file():
        path_to_json = path_to_json.resolve()
        with open(path_to_json) as f:
            jsn = json.load(f)
            if jsn.get("downloads") and jsn.get("downloads").get(side) and jsn.get("downloads").get(side).get("url"):
                downloadFile(jsn.get("downloads").get(side).get("url"), f"versions/{target_version}/{side}.jar")
            else:
                print("Could not download jar, missing fields")
                input("Aborting, press anything to exit")
                sys.exit()
    else:
        print('ERROR: Missing manifest file: version.json')
        input("Aborting, press anything to exit")
        sys.exit()
    print("Done !")


def getMappings(version, side):
    if Path(f'mappings/{version}/{side}.txt').exists() and Path(f'mappings/{version}/{side}.txt').is_file():
        print("Mappings already existing, not downloading again, if you want to please accept safe removal at beginning")
        return
    path_to_json = Path(f'versions/{version}/version.json')
    if path_to_json.exists() and path_to_json.is_file():
        print(f'Found {version}.json')
        path_to_json = path_to_json.resolve()
        with open(path_to_json) as f:
            jfile = json.load(f)
            url = jfile['downloads']
            if side == CLIENT:  # client:
                if url['client_mappings']:
                    url = url['client_mappings']['url']
                else:
                    print(f'Error: Missing client mappings for {version}')
            elif side == SERVER:  # server
                if url['server_mappings']:
                    url = url['server_mappings']['url']
                else:
                    print(f'Error: Missing server mappings for {version}')
            else:
                print('ERROR, type not recognized')
                sys.exit()

            print(f'Downloading the mappings for {version}...')
            downloadFile(url, f'mappings/{version}/{"client" if side == CLIENT else "server"}.txt')
    else:
        print('ERROR: Missing manifest file: version.json')
        input("Aborting, press anything to exit")
        sys.exit()


def remap(version, side):
    print('=== Remapping jar using SpecialSource ====')
    t = time.time()
    path = Path(f'versions/{version}/{side}.jar')
    if not path.exists() or not path.is_file():
        path_temp = (mc_path / f'versions/{version}/{version}.jar').expanduser()
        if path_temp.exists() and path_temp.is_file():
            r = input("Error, defaulting to client.jar from your local Minecraft folder, continue? (y/n)") or "y"
            if r != "y":
                sys.exit()
            path = path_temp
    mapp = Path(f'mappings/{version}/{side}.tsrg')
    specialsource = Path('./lib/SpecialSource-1.8.6.jar')
    if path.exists() and mapp.exists() and specialsource.exists() and path.is_file() and mapp.is_file() and specialsource.is_file():
        path = path.resolve()
        mapp = mapp.resolve()
        specialsource = specialsource.resolve()
        subprocess.run(['java',
                        '-jar', specialsource.__str__(),
                        '--in-jar', path.__str__(),
                        '--out-jar', f'./src/{version}-{side}-temp.jar',
                        '--srg-in', mapp.__str__(),
                        "--kill-lvt"  # kill snowmen
                        ], check=True)
        print(f'- New -> {version}-{side}-temp.jar')
        t = time.time() - t
        print('Done in %.1fs' % t)
    else:
        print(f'ERROR: Missing files: ./lib/SpecialSource-1.8.6.jar or mappings/{version}/{side}.tsrg or versions/{version}/{side}.jar')
        input("Aborting, press anything to exit")
        sys.exit()


def decompileFernFlower(decompiled_version, version, side):
    print('=== Decompiling using FernFlower (silent) ===')
    t = time.time()
    path = Path(f'./src/{version}-{side}-temp.jar')
    fernflower = Path('./lib/fernflower.jar')
    if path.exists() and fernflower.exists():
        path = path.resolve()
        fernflower = fernflower.resolve()
        subprocess.run(['java',
                        '-Xmx2G',
                        '-Xms1G',
                        '-jar', fernflower.__str__(),
                        '-hes=0',  # hide empty super invocation deactivated (might clutter but allow following)
                        '-hdc=0',  # hide empty default constructor deactivated (allow to track)
                        '-dgs=1',  # decompile generic signatures activated (make sure we can follow types)
                        '-ren=1',  # rename ambiguous activated
                        '-lit=1',  # output numeric literals
                        '-asc=1',  # encode non-ASCII characters in string and character
                        '-log=WARN',
                        path.__str__(), f'./src/{decompiled_version}/{side}'
                        ], check=True)
        print(f'- Removing -> {version}-{side}-temp.jar')
        os.remove(f'./src/{version}-{side}-temp.jar')
        print("Decompressing remapped jar to directory")
        with zipfile.ZipFile(f'./src/{decompiled_version}/{side}/{version}-{side}-temp.jar') as z:
            z.extractall(path=f'./src/{decompiled_version}/{side}')
        t = time.time() - t
        print('Done in %.1fs' % t)
        print(f'Remove Extra Jar file (file was decompressed in {decompiled_version}/{side})? (y/n): ')
        response = input() or "y"
        if response == 'y':
            print(f'- Removing -> {decompiled_version}/{side}/{version}-{side}-temp.jar')
            os.remove(f'./src/{decompiled_version}/{side}/{version}-{side}-temp.jar')
    else:
        print(f'ERROR: Missing files: ./lib/fernflower.jar or ./src/{version}-{side}-temp.jar')
        input("Aborting, press anything to exit")
        sys.exit()


def decompileCFR(decompiled_version, version, side):
    print('=== Decompiling using CFR (silent) ===')
    t = time.time()
    path = Path(f'./src/{version}-{side}-temp.jar')
    cfr = Path('./lib/cfr-0.146.jar')
    if path.exists() and cfr.exists():
        path = path.resolve()
        cfr = cfr.resolve()
        subprocess.run(['java',
                        '-Xmx2G',
                        '-Xms1G',
                        '-jar', cfr.__str__(),
                        path.__str__(),
                        '--outputdir', f'./src/{decompiled_version}/{side}',
                        '--caseinsensitivefs', 'true',
                        "--silent", "true"
                        ], check=True)
        print(f'- Removing -> {version}-{side}-temp.jar')
        print(f'- Removing -> summary.txt')
        os.remove(f'./src/{version}-{side}-temp.jar')
        os.remove(f'./src/{decompiled_version}/{side}/summary.txt')

        t = time.time() - t
        print('Done in %.1fs' % t)
    else:
        print(f'ERROR: Missing files: ./lib/cfr-0.146.jar or ./src/{version}-{side}-temp.jar')
        input("Aborting, press anything to exit")
        sys.exit()


def removeBrackets(line, counter):
    while '[]' in line:  # get rid of the array brackets while counting them
        counter += 1
        line = line[:-2]
    return line, counter


def convertMappings(version, side):
    remap_primitives = {"int": "I", "double": "D", "boolean": "Z", "float": "F", "long": "J", "byte": "B", "short": "S", "char": "C", "void": "V"}
    remap_file_path = lambda path: "L" + "/".join(path.split(".")) + ";" if path not in remap_primitives else remap_primitives[path]
    with open(f'mappings/{version}/{side}.txt', 'r') as inputFile:
        file_name = {}
        for line in inputFile.readlines():
            if line.startswith('#'):  # comment at the top, could be stripped
                continue
            deobf_name, obf_name = line.split(' -> ')
            if not line.startswith('    '):
                obf_name = obf_name.split(":")[0]
                file_name[remap_file_path(deobf_name)] = obf_name  # save it to compare to put the Lb

    with open(f'mappings/{version}/{side}.txt', 'r') as inputFile, open(f'mappings/{version}/{side}.tsrg', 'w+') as outputFile:
        for line in inputFile.readlines():
            if line.startswith('#'):  # comment at the top, could be stripped
                continue
            deobf_name, obf_name = line.split(' -> ')
            if line.startswith('    '):
                obf_name = obf_name.rstrip()  # remove leftover right spaces
                deobf_name = deobf_name.lstrip()  # remove leftover left spaces
                method_type, method_name = deobf_name.split(" ")  # split the `<methodType> <methodName>`
                method_type = method_type.split(":")[-1]  # get rid of the line numbers at the beginning for functions eg: `14:32:void`-> `void`
                if "(" in method_name and ")" in method_name:  # detect a function function
                    variables = method_name.split('(')[-1].split(')')[0]  # get rid of the function name and parenthesis
                    function_name = method_name.split('(')[0]  # get the function name only
                    array_length_type = 0

                    method_type, array_length_type = removeBrackets(method_type, array_length_type)
                    method_type = remap_file_path(method_type)  # remap the dots to / and add the L ; or remap to a primitives character
                    method_type = "L" + file_name[method_type] + ";" if method_type in file_name else method_type  # get the obfuscated name of the class
                    if "." in method_type:  # if the class is already packaged then change the name that the obfuscated gave
                        method_type = "/".join(method_type.split("."))
                    for i in range(array_length_type):  # restore the array brackets upfront
                        if method_type[-1] == ";":
                            method_type = "[" + method_type[:-1] + ";"
                        else:
                            method_type = "[" + method_type

                    if variables != "":  # if there is variables
                        array_length_variables = [0] * len(variables)
                        variables = list(variables.split(","))  # split the variables
                        for i in range(len(variables)):  # remove the array brackets for each variable
                            variables[i], array_length_variables[i] = removeBrackets(variables[i], array_length_variables[i])
                        variables = [remap_file_path(variable) for variable in variables]  # remap the dots to / and add the L ; or remap to a primitives character
                        variables = ["L" + file_name[variable] + ";" if variable in file_name else variable for variable in variables]  # get the obfuscated name of the class
                        variables = ["/".join(variable.split(".")) if "." in variable else variable for variable in variables]  # if the class is already packaged then change the obfuscated name
                        for i in range(len(variables)):  # restore the array brackets upfront for each variable
                            for j in range(array_length_variables[i]):
                                if variables[i][-1] == ";":
                                    variables[i] = "[" + variables[i][:-1] + ";"
                                else:
                                    variables[i] = "[" + variables[i]
                        variables = "".join(variables)

                    outputFile.write(f'\t{obf_name} ({variables}){method_type} {function_name}\n')
                else:
                    outputFile.write(f'\t{obf_name} {method_name}\n')

            else:
                obf_name = obf_name.split(":")[0]
                outputFile.write(remap_file_path(obf_name)[1:-1] + " " + remap_file_path(deobf_name)[1:-1] + "\n")

    print("Done !")


def makePaths(version, side, removal_bool):
    path = Path(f'mappings/{version}')
    if not path.exists():
        path.mkdir(parents=True)
    else:
        if removal_bool:
            shutil.rmtree(path)
            path.mkdir(parents=True)
    path = Path(f'versions/{version}')
    if not path.exists():
        path.mkdir(parents=True)
    else:
        path = Path(f'versions/{version}/version.json')
        if path.is_file() and removal_bool:
            path.unlink()
    if Path("versions").exists():
        path = Path(f'versions/version_manifest.json')
        if path.is_file() and removal_bool:
            path.unlink()

    path = Path(f'versions/{version}/{side}.jar')
    if path.exists() and path.is_file() and removal_bool:
        aw = input(f"versions/{version}/{side}.jar already exists, wipe it (w) or ignore (i) ? ") or "i"
        path = Path(f'versions/{version}')
        if aw == "w":
            shutil.rmtree(path)
            path.mkdir(parents=True)

    path = Path(f'src/{version}/{side}')
    if not path.exists():
        path.mkdir(parents=True)
    else:
        aw = input(f"/src/{version}/{side} already exists, wipe it (w), create a new folder (n) or kill the process (k) ? ")
        if aw == "w":
            shutil.rmtree(Path(f"./src/{version}/{side}"))
        elif aw == "n":
            version = version + side + "_" + str(random.getrandbits(128))
        else:
            sys.exit()
        path = Path(f'src/{version}/{side}')
        path.mkdir(parents=True)
    return version


def main():
    checkjava()
    snapshot, latest = getLatestVersion()
    if snapshot == None or latest == None:
        print("Error getting latest versions, please refresh cache")
        exit()

    parser = argparse.ArgumentParser(description="Decompile MC using mojang mappings")
    parser.add_argument("-r", "--removeold", help="Clean up old runs", action="store_true")
    parser.add_argument("-d", "--decompiler", choices=["cfr", "f"], help="Decompiler to use (CFR or Fernflower, defaults to Fernflower)", default="f")
    parser.add_argument("-m", "--manual", help="Manual mode, defaults to auto", action="store_true")
    parser.add_argument("side", choices=["client", "server"], help="Side to decompile (Client or Server)")
    parser.add_argument("version", help="Version to decompile (or latest/snapshot)")

    args = parser.parse_args()
    print(args)

    print("Decompiling using official mojang mappings (Default option are in uppercase, you can just enter)")
    removal_bool = 1 if args.removeold else 0
    decompiler = args.decompiler
    version = args.version
    if version in ["snapshot","snap","s"]:
        version=snapshot
    if version in ["latest","l"]:
        version=latest
    side = args.side
    side = CLIENT if side == "client" else SERVER
    decompiled_version = makePaths(version, side, removal_bool)
    getManifest()
    getVersionManifest(version)
    manual = args.manual
    if not manual:
        getMappings(version, side)
        convertMappings(version, side)
        getVersionJar(version, side)
        remap(version, side)
        if decompiler.lower() == "cfr":
            decompileCFR(decompiled_version, version, side)
        else:
            decompileFernFlower(decompiled_version, version, side)
        print("===FINISHED===")
        print(f"output is in /src/{version}")
        input("Press Enter key to exit")
        sys.exit()

    r = input('Download mappings? (y/n): ') or "y"
    if r == 'y':
        getMappings(version, side)

    r = input('Remap mappings to tsrg? (y/n): ') or "y"
    if r == 'y':
        convertMappings(version, side)

    r = input(f'Get {version}-{side}.jar ? (y/n): ') or "y"
    if r == "y":
        getVersionJar(version, side)

    r = input('Remap? (y/n): ') or "y"
    if r == 'y':
        remap(version, side)

    r = input('Decompile? (y/n): ') or "y"
    if r == 'y':
        if decompiler.lower() == "cfr":
            decompileCFR(decompiled_version, version, side)
        else:
            decompileFernFlower(decompiled_version, version, side)

    print("===FINISHED===")
    print(f"output is in /src/{version}")
    input("Press Enter key to exit")


if __name__ == "__main__":
    main()
